# TLS Remediation Automation

**One-command solution to fix all TLS certificate validation issues across the platform.**

---

## 🚀 Quick Start (The Easy Way)

```bash
cd self-hosted-ai/
./scripts/fix-all-tls-issues.sh
```

That's it! The script will:
1. ✅ Check prerequisites (kubectl, argocd, git, uv)
2. ✅ Audit current TLS validation status
3. ✅ Fix oauth2-proxy and Grafana configurations
4. ✅ Commit changes to git
5. ✅ Deploy to Kubernetes
6. ✅ Verify deployment
7. ✅ Install CA certificate on your workstation
8. ✅ Test SSO endpoints

**Total time**: ~5 minutes (mostly waiting for pod restarts)

---

## 📋 What Gets Fixed

### Security Vulnerabilities (CWE-295)

**Before** (INSECURE):
- oauth2-proxy: `sslInsecureSkipVerify: true` ← MITM attack vector
- Grafana: `tls_skip_verify_insecure: true` ← MITM attack vector

**After** (SECURE):
- oauth2-proxy: Mounts CA certificate, validates TLS properly
- Grafana: Configures CA trust, validates TLS properly

### Services Protected

| Service | Status | Protected By |
|---------|--------|--------------|
| ArgoCD | ✅ Already Fixed | Native OIDC with rootCA |
| oauth2-proxy | ⚠️ **This Script Fixes** | Mounts vectorweight-root-ca |
| Grafana | ⚠️ **This Script Fixes** | Configures tls_client_ca |
| n8n | ✅ Protected | Via oauth2-proxy (after fix) |
| SearXNG | ✅ Protected | Via oauth2-proxy (after fix) |
| LiteLLM | ✅ Protected | Via oauth2-proxy (after fix) |
| Traefik | ✅ Protected | Via oauth2-proxy (after fix) |
| Prometheus | ✅ Protected | Via oauth2-proxy (after fix) |
| Longhorn | ✅ Protected | Via oauth2-proxy (after fix) |
| OpenObserve | ✅ Protected | Via oauth2-proxy (after fix) |
| Jaeger | ✅ Protected | Via oauth2-proxy (after fix) |

**Impact**: Fixes protect **11 services** from MITM attacks.

---

## 🎯 Prerequisites

The script automatically checks these, but you need:

- **kubectl** - Configured with cluster access
- **argocd** - Logged in (script can prompt SSO login)
- **git** - Repository on `dev` branch
- **uv** - Python package manager for scripts
- **sudo** - For system CA certificate installation

**Check prerequisites**:
```bash
./scripts/fix-all-tls-issues.sh
# Will fail fast if anything is missing
```

---

## 📖 Detailed Workflow

### Phase 1: Security Audit

```
════════════════════════════════════════════════════════
  Phase 1: Security Audit
════════════════════════════════════════════════════════

▶ Checking Current TLS Validation Status

[OK]   ArgoCD: Proper rootCA configured
[FAIL] oauth2-proxy: Using sslInsecureSkipVerify: true (INSECURE)
[FAIL] Grafana: Using tls_skip_verify_insecure: true (INSECURE)

Proceed with automated fixes? [Y/n]:
```

### Phase 2: Service Configuration Fixes

```
════════════════════════════════════════════════════════
  Phase 2: Service Configuration Fixes
════════════════════════════════════════════════════════

▶ Applying TLS Validation Fixes

ℹ Creating backups...
✓ Backups created
✓ Service configuration fixes applied

▶ Review Changes

ℹ oauth2-proxy changes:
+  extraVolumes:
+    - name: ca-bundle
+      secret:
+        secretName: vectorweight-root-ca
+  extraVolumeMounts:
+    - name: ca-bundle
+      mountPath: /etc/ssl/certs/vectorweight-ca.crt
+      subPath: tls.crt

ℹ Grafana changes:
+  extraSecretMounts:
+    - name: ca-cert
+      secretName: vectorweight-root-ca
+      mountPath: /etc/grafana/ca

Commit these changes? [Y/n]:
```

### Phase 3: Git Commit

```
════════════════════════════════════════════════════════
  Phase 3: Git Commit
════════════════════════════════════════════════════════

▶ Committing Service Configuration Changes

[dev abc1234] fix(security): enable TLS validation for oauth2-proxy and Grafana
 2 files changed, 45 insertions(+), 2 deletions(-)

✓ Changes committed to dev
```

### Phase 4: Cluster Deployment

```
════════════════════════════════════════════════════════
  Phase 4: Cluster Deployment
════════════════════════════════════════════════════════

▶ Pushing Changes to Remote
✓ Pushed to origin/dev

▶ Syncing ArgoCD Applications
ℹ Syncing oauth2-proxy...
✓ oauth2-proxy synced
ℹ Syncing prometheus...
✓ prometheus synced

▶ Restarting Pods
ℹ Restarting oauth2-proxy...
deployment.apps/oauth2-proxy restarted
Waiting for deployment "oauth2-proxy" rollout to finish...
deployment "oauth2-proxy" successfully rolled out
✓ oauth2-proxy restarted

✓ Deployment complete
```

### Phase 5: Deployment Verification

```
════════════════════════════════════════════════════════
  Phase 5: Deployment Verification
════════════════════════════════════════════════════════

▶ Running Verification Tests
[OK] No TLS errors in oauth2-proxy logs
[OK] No TLS errors in Grafana logs
✓ All verification tests passed

▶ Checking Service Health
ℹ oauth2-proxy pods:
NAME                            READY   STATUS    RESTARTS   AGE
oauth2-proxy-7d8f9c5b4d-xyz12   1/1     Running   0          2m

ℹ Grafana pods:
NAME                                   READY   STATUS    RESTARTS   AGE
prometheus-grafana-5f7c9d8b6d-abc34    1/1     Running   0          2m
```

### Phase 6: Workstation Certificate Installation

```
════════════════════════════════════════════════════════
  Phase 6: Workstation Certificate Installation
════════════════════════════════════════════════════════

▶ Installing CA Certificate on This Workstation

Install CA certificate on this workstation? [Y/n]: y

✓ Certificate extracted to: /tmp/vectorweight-ca/vectorweight-ca.crt
✓ Certificate installed to system trust store

Testing https://auth.vectorweight.com ... ✓ OK
Testing https://argocd.vectorweight.com ... ✓ OK

✓ CA certificate installed on workstation
```

### Phase 7: SSO Login Testing

```
════════════════════════════════════════════════════════
  Phase 7: SSO Login Testing
════════════════════════════════════════════════════════

▶ Testing SSO Endpoints
  https://argocd.vectorweight.com ... ✓ OK
  https://grafana.vectorweight.com ... ✓ OK
  https://n8n.vectorweight.com ... ✓ OK

ℹ Manual SSO Testing:
  1. ArgoCD: https://argocd.vectorweight.com
     - Click 'LOG IN VIA KEYCLOAK'
  2. Grafana: https://grafana.vectorweight.com
     - Click 'Sign in with Keycloak'

ℹ Login credentials: kang / banana12
```

### Success Summary

```
════════════════════════════════════════════════════════
  Remediation Complete ✓
════════════════════════════════════════════════════════

✓ All phases completed successfully!

ℹ Summary:
  ✓ Service configurations updated (oauth2-proxy, Grafana)
  ✓ Changes committed to dev branch
  ✓ Deployed to Kubernetes cluster
  ✓ Services restarted with new configuration
  ✓ Verification tests passed
  ✓ CA certificate installed on workstation

ℹ Next steps:
  1. Test SSO logins (see URLs above)
  2. Monitor service logs for any issues
  3. Create PR from dev to main when stable
```

---

## 🛡️ Safety Features

### Automatic Backups

Before modifying files, the script creates backups:
```
helm/oauth2-proxy/values.yaml → values.yaml.backup
helm/prometheus/values.yaml → values.yaml.backup
```

If anything fails, restore with:
```bash
mv helm/oauth2-proxy/values.yaml.backup helm/oauth2-proxy/values.yaml
mv helm/prometheus/values.yaml.backup helm/prometheus/values.yaml
```

### User Confirmations

The script prompts before:
- ✅ Applying fixes (shows diff first)
- ✅ Committing to git
- ✅ Installing workstation certificate
- ✅ Switching git branches (if needed)

### Rollback Capability

If deployment fails:
```bash
# Revert the commit
git revert HEAD

# Sync ArgoCD
argocd app sync oauth2-proxy --force
argocd app sync prometheus --force
```

### Error Handling

The script uses `set -euo pipefail` to:
- Exit on any command failure
- Treat unset variables as errors
- Catch errors in pipes

---

## 🔧 Advanced Usage

### Skip Workstation Installation

Edit the script and set:
```bash
INSTALL_WORKSTATION_CERT=false
```

Or run individual phases manually (see below).

### Change Target Branch

Edit the script and set:
```bash
BRANCH="main"  # Default is "dev"
```

### Run Individual Phases

The script is modular - you can source it and run phases separately:

```bash
source scripts/fix-all-tls-issues.sh

# Run only specific phases
check_prerequisites
audit_current_state
apply_service_fixes
# ... etc
```

### Customize Services to Sync

Edit the script and modify:
```bash
SERVICES_TO_SYNC=("oauth2-proxy" "prometheus" "custom-service")
```

---

## 🐛 Troubleshooting

### "kubectl not connected to cluster"

**Fix**:
```bash
kubectl config use-context <context-name>
kubectl cluster-info
```

### "ArgoCD not logged in"

**Fix**:
```bash
argocd login argocd.vectorweight.com --sso
```

The script will also prompt for login automatically.

### "Git commit failed"

**Possible causes**:
- Commit signing enabled but GPG not configured
- No changes to commit (already applied)

**Fix**:
```bash
# Check git status
git status

# Configure GPG (if needed)
git config --global commit.gpgsign false
```

### "Pod restart failed"

**Check pod status**:
```bash
kubectl get pods -n automation -l app.kubernetes.io/name=oauth2-proxy
kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=50
```

**Manual restart**:
```bash
kubectl rollout restart deployment/oauth2-proxy -n automation
kubectl rollout status deployment/oauth2-proxy -n automation
```

### "Certificate installation failed"

**For macOS**: May need to manually approve certificate in Keychain
**For Linux**: Check sudo permissions

**Manual installation**:
```bash
./scripts/install-ca-certificate.sh all
```

---

## 📚 Related Documentation

- **Security Audit**: [`docs/SECURITY_TLS_VALIDATION_AUDIT.md`](../docs/SECURITY_TLS_VALIDATION_AUDIT.md)
- **Certificate Guide**: [`docs/CERTIFICATE_TRUST_GUIDE.md`](../docs/CERTIFICATE_TRUST_GUIDE.md)
- **Quick Reference**: [`docs/CERTIFICATE_QUICK_REFERENCE.md`](../docs/CERTIFICATE_QUICK_REFERENCE.md)
- **ArgoCD Fix**: [`docs/SECURITY_ARGOCD_TLS_FIX.md`](../docs/SECURITY_ARGOCD_TLS_FIX.md)

---

## 🔐 Security Considerations

### What This Fixes

**CWE-295: Improper Certificate Validation**
- Prevents Man-in-the-Middle (MITM) attacks
- Ensures TLS certificates are properly validated
- Replaces `insecureSkipVerify` with proper CA trust

### Attack Scenarios Mitigated

1. **Network MITM**: Attacker intercepts traffic between service and Keycloak
2. **DNS Poisoning**: Redirects to fake Keycloak instance
3. **ARP Spoofing**: Intercepts LAN traffic
4. **Compromised Router**: Routes traffic through malicious proxy

**Without this fix**: All scenarios succeed silently
**With this fix**: All scenarios detected and blocked

### Compliance

Addresses requirements for:
- **CIS Kubernetes Benchmark**: 5.7.1 - Do not disable certificate validation
- **NIST SP 800-190**: Container security - Secure communication channels
- **PCI-DSS**: Requirement 4 - Encrypt transmission of cardholder data
- **SOC 2**: CC6.1 - Logical and physical access controls

---

## ❓ FAQ

### Q: Is this safe to run in production?

**A**: Yes, with caveats:
- Creates backups before modifying files
- Prompts for confirmation before each phase
- Tests deployment before declaring success
- Can be rolled back with `git revert HEAD`

However, **test in dev/staging first** if possible.

### Q: What if I don't want to install the certificate on my workstation?

**A**: You can skip phase 6 when prompted, or set `INSTALL_WORKSTATION_CERT=false` in the script.

### Q: Can I run this multiple times?

**A**: Yes, it's idempotent. If fixes are already applied, it will detect that and skip unnecessary changes.

### Q: What if ArgoCD sync fails?

**A**: The script will show the error and ask if you want to continue. You can manually sync later:
```bash
argocd app sync oauth2-proxy
```

### Q: How do I verify it worked?

**A**: The script runs verification automatically, but you can also:
```bash
# Check TLS validation status
uv run scripts/fix-tls-validation.py check

# Test SSO login
open https://argocd.vectorweight.com

# Check service logs
kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=50
```

---

## 🎓 Learning Resources

### Understanding the Vulnerability

Read the security audit for detailed attack scenarios:
```bash
cat docs/SECURITY_TLS_VALIDATION_AUDIT.md
```

### How the Fix Works

The fix replaces certificate validation bypass with proper CA trust:

**oauth2-proxy**:
- Mounts `vectorweight-root-ca` secret as file
- Sets `SSL_CERT_FILE` environment variable
- Go's TLS library reads custom CA automatically

**Grafana**:
- Mounts CA certificate to `/etc/grafana/ca/`
- Configures `tls_client_ca` in grafana.ini
- Grafana validates Keycloak certificate against CA

### Why Not Let's Encrypt?

For internal services, self-signed certificates are:
- ✅ Free (like Let's Encrypt)
- ✅ Automated (via cert-manager)
- ✅ No external dependencies
- ✅ Works offline
- ✅ Full control over lifecycle

For public-facing services, use Let's Encrypt. For internal services with proper CA trust, self-signed is fine.

---

**Last Updated**: 2026-02-21
**Script Version**: 1.0
**Maintained By**: Security Team
