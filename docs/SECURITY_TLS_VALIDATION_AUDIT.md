# Security Audit: TLS Certificate Validation

**Date**: 2026-02-21
**Auditor**: Claude Sonnet 4.5
**Severity**: HIGH
**Scope**: All services connecting to Keycloak SSO

---

## Executive Summary

**Finding**: Multiple services disable TLS certificate validation when connecting to Keycloak, creating MITM attack vectors.

**Impact**: CRITICAL - Compromised authentication can lead to cluster-wide breach.

**Status**:
- ✅ ArgoCD: FIXED
- ⚠️ oauth2-proxy: NEEDS FIX
- ⚠️ Grafana: NEEDS FIX

---

## Affected Services

### 1. ArgoCD (FIXED ✅)

**File**: `helm/argocd-config/templates/configmap.yaml`

**Insecure Configuration** (removed):
```yaml
oidc.config: |
  insecureSkipVerify: true  # ← REMOVED
```

**Secure Configuration** (implemented):
```yaml
oidc.config: |
  rootCA: |
    -----BEGIN CERTIFICATE-----
    <vectorweight-root-ca certificate>
    -----END CERTIFICATE-----
```

**Fix Date**: 2026-02-21
**Verification**: Certificate validation enabled, TLS verified

---

### 2. oauth2-proxy (⚠️ NEEDS FIX)

**File**: `helm/oauth2-proxy/values.yaml:28`

**Current Insecure Configuration**:
```yaml
# Skip TLS verification for OIDC provider (needed when using self-signed certs)
sslInsecureSkipVerify: true  # ← SECURITY VULNERABILITY
```

**Impact**:
- **CRITICAL**: oauth2-proxy is the authentication gateway for 9 services
- Compromised oauth2-proxy = compromised access to:
  - n8n (workflow automation with credentials)
  - SearXNG (search queries)
  - LiteLLM (AI API gateway)
  - Traefik Dashboard (ingress control)
  - Prometheus (cluster metrics)
  - Longhorn (storage management)
  - OpenObserve (logs/traces)
  - Jaeger (distributed tracing)
  - Landing page

**Attack Scenario**:
1. Attacker performs MITM between oauth2-proxy and Keycloak
2. Intercepts authentication tokens for ALL protected services
3. Gains access to automation, AI, monitoring, and storage systems
4. Can deploy malicious workloads via n8n
5. Exfiltrate data via LiteLLM or observability tools

**Recommended Fix**:

**Option A: Use Kubernetes CA Bundle** (recommended):
```yaml
# helm/oauth2-proxy/values.yaml
config:
  # ... existing config ...
  sslInsecureSkipVerify: false  # Enable verification

# Add to deployment template
volumes:
  - name: ca-certs
    secret:
      secretName: vectorweight-root-ca
volumeMounts:
  - name: ca-certs
    mountPath: /etc/ssl/certs/vectorweight-ca.crt
    subPath: tls.crt
    readOnly: true

env:
  - name: SSL_CERT_FILE
    value: /etc/ssl/certs/vectorweight-ca.crt
```

**Option B: Use oauth2-proxy's CA file option**:
```yaml
config:
  sslInsecureSkipVerify: false
  oidcIssuerUrl: "https://auth.vectorweight.com/realms/vectorweight"

# Add CA bundle via extraVolumes
extraVolumes:
  - name: ca-bundle
    secret:
      secretName: vectorweight-root-ca

extraVolumeMounts:
  - name: ca-bundle
    mountPath: /etc/ssl/certs/custom-ca.crt
    subPath: tls.crt

# oauth2-proxy will use system CA store + custom CA
```

---

### 3. Grafana (⚠️ NEEDS FIX)

**File**: `argocd/helm/prometheus/values.yaml:156`

**Current Insecure Configuration**:
```yaml
auth:
  generic_oauth:
    tls_skip_verify_insecure: true  # ← SECURITY VULNERABILITY
    # Comment admits it: "proper fix: mount CA bundle"
```

**Impact**:
- **HIGH**: Grafana has access to all cluster metrics and logs
- Compromised Grafana admin can:
  - View sensitive metrics (API keys in labels, etc.)
  - Modify dashboards to hide attacks
  - Access trace data showing internal architecture
  - Query logs for credential leaks

**Attack Scenario**:
1. MITM Grafana ↔ Keycloak connection
2. Issue fake admin token
3. Log into Grafana as admin
4. Enumerate cluster infrastructure via metrics
5. Find vulnerable services via Prometheus alerts
6. Use dashboards to map attack surface

**Recommended Fix**:
```yaml
# argocd/helm/prometheus/values.yaml
grafana:
  grafana.ini:
    auth.generic_oauth:
      tls_skip_verify_insecure: false  # Enable verification
      tls_client_ca: /etc/grafana/ca/tls.crt

  # Mount CA certificate
  extraSecretMounts:
    - name: ca-cert
      secretName: vectorweight-root-ca
      defaultMode: 0444
      mountPath: /etc/grafana/ca
      readOnly: true
```

---

## Other Services Audited

### ✅ Open WebUI
**File**: `helm/open-webui/values.yaml`

**Status**: Uses native OIDC with proper certificate validation
```yaml
env:
  OPENID_PROVIDER_URL: https://auth.vectorweight.com/realms/vectorweight
  # No skip verify flags - uses system CA store
```

**Finding**: SECURE (no issues found)

---

### ✅ GitLab
**File**: `argocd/helm/gitlab/values.yaml`

**Status**: Uses OmniAuth with proper HTTPS
```yaml
omniauth:
  providers:
    - secret: gitlab-oidc-provider
      # Uses HTTPS with default verification
```

**Finding**: SECURE (no issues found)

---

## Vulnerability Summary Table

| Service | File | Line | Setting | Severity | Status |
|---------|------|------|---------|----------|--------|
| ArgoCD | helm/argocd-config/templates/configmap.yaml | 21 | `insecureSkipVerify: true` | CRITICAL | ✅ FIXED |
| oauth2-proxy | helm/oauth2-proxy/values.yaml | 28 | `sslInsecureSkipVerify: true` | CRITICAL | ⚠️ OPEN |
| Grafana | argocd/helm/prometheus/values.yaml | 156 | `tls_skip_verify_insecure: true` | HIGH | ⚠️ OPEN |

**Total Vulnerabilities**: 3
**Fixed**: 1
**Remaining**: 2

---

## Remediation Plan

### Phase 1: Immediate (Critical)
- [x] Fix ArgoCD OIDC configuration
- [x] Create automation tooling for certificate installation
- [ ] Fix oauth2-proxy SSL verification (automated via `fix-tls-validation.py`)
- [ ] Fix Grafana OAuth TLS verification (automated via `fix-tls-validation.py`)

### Phase 2: Verification (Post-Fix)
- [ ] Test all SSO logins with TLS validation enabled
- [ ] Verify no certificate errors in logs
- [ ] Confirm MITM attacks are detected
- [ ] Security scan all services for similar issues

### Phase 3: Documentation
- [x] Create security advisory (SECURITY_ARGOCD_TLS_FIX.md)
- [x] Update SSO_INTEGRATION_GUIDE.md with security warnings
- [x] Create Certificate Trust Guide (CERTIFICATE_TRUST_GUIDE.md)
- [x] Create automation scripts (install-ca-certificate.sh, fix-tls-validation.py)
- [ ] Add security checklist to deployment docs

### Automation Tools

**For End Users** (install CA certificate on workstations):
```bash
# Complete installation (extract, install, verify)
./scripts/install-ca-certificate.sh all
```

**For Administrators** (fix service configurations):
```bash
# Check current TLS validation status
uv run scripts/fix-tls-validation.py check

# Apply fixes to oauth2-proxy and Grafana
uv run scripts/fix-tls-validation.py fix

# Verify deployment
uv run scripts/fix-tls-validation.py verify
```

**Documentation**:
- [`docs/CERTIFICATE_TRUST_GUIDE.md`](CERTIFICATE_TRUST_GUIDE.md) - Complete installation guide
- [`scripts/install-ca-certificate.sh`](../scripts/install-ca-certificate.sh) - CA installation automation
- [`scripts/fix-tls-validation.py`](../scripts/fix-tls-validation.py) - Service configuration fixes

---

## Testing Recommendations

### Manual MITM Test

**Setup**:
```bash
# Create self-signed cert for fake Keycloak
openssl req -x509 -newkey rsa:4096 -keyout fake.key -out fake.crt -days 1 \
  -subj "/CN=auth.vectorweight.com" -nodes

# Run fake server
python3 -m http.server 8443 --bind 127.0.0.1

# Modify /etc/hosts on client
echo "127.0.0.1 auth.vectorweight.com" >> /etc/hosts
```

**Expected Behavior**:

With `insecureSkipVerify: true`:
- ❌ Connection succeeds
- ❌ No warnings
- ❌ MITM attack succeeds

With `rootCA` configured:
- ✅ Connection fails
- ✅ Certificate error logged
- ✅ MITM attack blocked

---

## Certificate Management

### Current CA Certificate

**Issuer**: VectorWeight Root CA
**Location**: `vectorweight-root-ca` secret in `cert-manager` namespace
**Expiry**: 2026-04-16 (check with: `kubectl get secret vectorweight-root-ca -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -enddate`)
**Used By**:
- Wildcard certificate (`*.vectorweight.com`)
- All internal service TLS
- Now: ArgoCD OIDC validation

### Rotation Procedure

When CA certificate expires or needs rotation:

1. **Generate New CA**:
   ```bash
   # Via cert-manager (automated)
   kubectl delete certificate vectorweight-root-ca -n cert-manager
   # cert-manager will regenerate
   ```

2. **Update All Services**:
   ```bash
   # ArgoCD (automatic via Helm template)
   argocd app sync argocd-config

   # oauth2-proxy (after fix implemented)
   argocd app sync oauth2-proxy

   # Grafana (after fix implemented)
   argocd app sync prometheus
   ```

3. **Verify**:
   ```bash
   # Check all services trust new CA
   for service in argocd oauth2-proxy grafana; do
     echo "Testing $service..."
     # Test OIDC connection
   done
   ```

---

## Compliance Implications

### Standards Affected

- **CIS Kubernetes Benchmark**: 5.7.1 - Do not disable certificate validation
- **NIST SP 800-190**: Container security - Secure communication channels
- **PCI-DSS**: Requirement 4 - Encrypt transmission of cardholder data
- **SOC 2**: CC6.1 - Logical and physical access controls

### Audit Trail

- Initial finding: 2026-02-21
- ArgoCD fix applied: 2026-02-21
- Remaining fixes: Pending approval
- Next security review: After all fixes applied

---

## Lessons Learned

1. **Code Review Gap**: Insecure TLS bypass was documented as "needed" without security review
2. **Default Insecure**: Template chose convenience over security
3. **Lack of Testing**: No MITM testing in validation procedures
4. **Documentation Debt**: Security implications not clearly stated

### Process Improvements

- [ ] Add security review step for all authentication changes
- [ ] Include MITM testing in deployment validation
- [ ] Create security checklist for new services
- [ ] Mandatory security documentation for all bypasses
- [ ] Automated scanning for insecure TLS configurations

---

## References

- [OWASP: Transport Layer Protection](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [CWE-295: Improper Certificate Validation](https://cwe.mitre.org/data/definitions/295.html)
- [oauth2-proxy SSL Configuration](https://oauth2-proxy.github.io/oauth2-proxy/docs/configuration/overview#ssl-configuration)
- [Grafana OAuth TLS](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/generic-oauth/#tls-skip-verify)

---

**Next Actions**:
1. ~~Create fixes for oauth2-proxy and Grafana~~ ✅ **Automated** (use `fix-tls-validation.py`)
2. Apply fixes: `uv run scripts/fix-tls-validation.py fix`
3. Commit and deploy to dev branch
4. Test all SSO flows with TLS validation enabled
5. Install CA certificate on user workstations: `./scripts/install-ca-certificate.sh all`
6. Conduct security review of other services
7. Update deployment procedures with security checks

**Automation Tools Available**:
- [`scripts/install-ca-certificate.sh`](../scripts/install-ca-certificate.sh) - CA installation for end users
- [`scripts/fix-tls-validation.py`](../scripts/fix-tls-validation.py) - Service configuration fixes
- [`docs/CERTIFICATE_TRUST_GUIDE.md`](CERTIFICATE_TRUST_GUIDE.md) - Complete guide

**Security Contact**: See SECURITY.md (to be created)
