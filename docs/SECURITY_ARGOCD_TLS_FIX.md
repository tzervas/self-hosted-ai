# Security Fix: ArgoCD TLS Certificate Validation

**Date**: 2026-02-21
**Severity**: HIGH
**Status**: ✅ FIXED

---

## Vulnerability Description

### Original Insecure Configuration

The initial ArgoCD OIDC configuration used `insecureSkipVerify: true` to bypass TLS certificate validation when connecting to Keycloak:

```yaml
# INSECURE - Original configuration
oidc.config: |
  name: Keycloak
  issuer: https://auth.vectorweight.com/realms/vectorweight
  insecureSkipVerify: true  # ← CRITICAL VULNERABILITY
```

### Security Impact

**Attack Vector**: Man-in-the-Middle (MITM)

An attacker positioned between ArgoCD and Keycloak (e.g., on the network, compromised router, ARP spoofing) can:

1. **Impersonate Keycloak**: Present a fake TLS certificate
2. **Intercept Authentication**: Capture OAuth tokens and user credentials
3. **Issue Fake Identities**: Create malicious authentication responses
4. **Gain Cluster Access**: Compromise ArgoCD and entire Kubernetes cluster

**Risk Level**: **CRITICAL**
- ArgoCD has admin access to entire cluster
- Compromised auth = full cluster takeover
- Silent attack (no TLS warnings when verification disabled)

### CWE Classification

- **CWE-295**: Improper Certificate Validation
- **CWE-297**: Improper Validation of Certificate with Host Mismatch
- **CWE-319**: Cleartext Transmission of Sensitive Information (effective outcome)

---

## Secure Fix Implementation

### New Configuration

```yaml
# SECURE - Fixed configuration
oidc.config: |
  name: Keycloak
  issuer: https://auth.vectorweight.com/realms/vectorweight
  clientID: argocd
  clientSecret: $oidc.keycloak.clientSecret
  requestedScopes: ["openid", "profile", "email", "groups"]
  # Trust self-signed CA certificate (maintains TLS security)
  rootCA: |
    -----BEGIN CERTIFICATE-----
    MIIDLzCCAhegAwIBAgIUAJl2xR1OaKfgTNTC4KhjdhTa2ugwDQYJKoZIhvcNAQEL
    BQAwHzEdMBsGA1UEAxMUVmVjdG9yV2VpZ2h0IFJvb3QgQ0EwHhcNMjYwMTE2MDIw
    ...
    -----END CERTIFICATE-----
```

### How It Works

1. **Helm Template Helper**: `argocd-config.rootCA` template function
2. **Dynamic CA Loading**: Reads from `vectorweight-root-ca` secret in `cert-manager` namespace
3. **Fallback CA**: Embedded certificate if secret not available (bootstrap)
4. **TLS Validation**: ArgoCD validates Keycloak's certificate chain against trusted CA

**Files Changed**:
- `helm/argocd-config/templates/configmap.yaml` - Updated OIDC config to use `rootCA`
- `helm/argocd-config/templates/_helpers.tpl` - Added `argocd-config.rootCA` helper
- `docs/SSO_INTEGRATION_GUIDE.md` - Updated troubleshooting section with security warning

---

## Verification

### Test TLS Validation

```bash
# Verify ArgoCD OIDC config uses rootCA (not insecureSkipVerify)
kubectl get cm argocd-cm -n argocd -o yaml | grep -A 30 "oidc.config"
# Should show: rootCA: | with certificate, NOT insecureSkipVerify: true

# Test OIDC connection from ArgoCD pod
kubectl exec -n argocd deployment/argocd-server -- \
  curl -v https://auth.vectorweight.com/realms/vectorweight/.well-known/openid-configuration
# Should complete successfully without certificate errors

# Check ArgoCD logs for TLS errors
kubectl logs -n argocd deployment/argocd-server | grep -i "certificate\|tls\|x509"
# Should NOT show "certificate signed by unknown authority"
```

### Expected Behavior

✅ **Secure**:
- ArgoCD validates Keycloak TLS certificate
- Connection uses encrypted channel
- MITM attacks detected and blocked

❌ **Insecure** (old behavior):
- No certificate validation
- Silent MITM attacks possible
- No security warnings

---

## Why This Matters

### Production Security Requirements

1. **Zero Trust Architecture**: All connections must be authenticated and encrypted
2. **Defense in Depth**: TLS is critical security layer
3. **Compliance**: Many standards (PCI-DSS, SOC 2, HIPAA) require proper TLS validation
4. **Supply Chain Security**: ArgoCD deploys all infrastructure - must be secured

### Real-World Attack Scenarios

**Scenario 1: Compromised Home Router**
- Attacker gains access to router (weak password, firmware vuln)
- Routes ArgoCD traffic through malicious proxy
- Captures OAuth tokens for Keycloak
- Logs into ArgoCD with admin privileges
- Deploys backdoor containers to all pods

**Scenario 2: ARP Spoofing on LAN**
- Attacker on same network (e.g., compromised IoT device)
- Performs ARP spoofing to intercept traffic
- Presents fake Keycloak instance
- Issues tokens granting admin access
- Compromises entire cluster

**Scenario 3: DNS Poisoning**
- Attacker compromises local DNS or uses DNS rebinding
- Redirects `auth.vectorweight.com` to malicious server
- Without cert validation, ArgoCD connects to fake Keycloak
- Attacker gains persistent cluster access

---

## Best Practices

### For Self-Signed Certificates

**DO:**
- ✅ Use `rootCA` to explicitly trust your CA
- ✅ Distribute CA certificate to all services
- ✅ Implement certificate rotation
- ✅ Monitor certificate expiry

**DON'T:**
- ❌ Use `insecureSkipVerify` (ever!)
- ❌ Use `verify: false` or equivalent
- ❌ Disable TLS entirely
- ❌ Trust "just this once" for production

### For Production Environments

**Strongly Recommended**:
1. **Use Let's Encrypt**: Free, automated, publicly trusted certificates
2. **Private CA with Distribution**: If using internal CA, distribute to all systems
3. **Certificate Monitoring**: Alert on expiry, revocation, invalid certs
4. **mTLS**: Mutual TLS for ArgoCD ↔ Keycloak communication

---

## Migration Guide

### If You Have `insecureSkipVerify` in Production

**Immediate Steps**:

1. **Identify All Instances**:
   ```bash
   # Search entire cluster for insecure TLS configs
   kubectl get cm -A -o yaml | grep -B5 -A5 "insecureSkipVerify\|verify.*false"
   ```

2. **Get Root CA Certificate**:
   ```bash
   kubectl get secret vectorweight-root-ca -n cert-manager \
     -o jsonpath='{.data.tls\.crt}' | base64 -d > vectorweight-ca.crt
   ```

3. **Update ArgoCD Config**:
   ```bash
   # Sync the fixed argocd-config Helm chart
   argocd app sync argocd-config

   # Restart ArgoCD server to reload config
   kubectl rollout restart deployment/argocd-server -n argocd
   ```

4. **Verify Fix**:
   ```bash
   # Test OIDC login
   argocd login argocd.vectorweight.com --sso
   # Should work without certificate errors
   ```

5. **Update Documentation**:
   - Remove any `insecureSkipVerify` examples
   - Add security warnings
   - Document proper CA trust configuration

---

## Additional Reading

- [OWASP: Transport Layer Protection Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [CWE-295: Improper Certificate Validation](https://cwe.mitre.org/data/definitions/295.html)
- [ArgoCD SSO Configuration](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/#sso)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)

---

## Related Fixes

Check these services for similar issues:

```bash
# Grafana
kubectl get cm -n monitoring grafana -o yaml | grep -i "skip.*verify"

# oauth2-proxy
kubectl get deployment -n automation oauth2-proxy -o yaml | grep -i "skip.*verify"

# Other services with OIDC
kubectl get cm,deployment -A -o yaml | grep -B3 -A3 "oidc\|oauth" | grep -i "skip.*verify"
```

---

**Status**: ✅ Fixed in argocd-config v0.1.0
**Verified By**: Security review 2026-02-21
**Next Review**: Certificate rotation (90 days from CA issue date)
