# Certificate Trust Installation Guide

**Purpose**: Automate installation and configuration of VectorWeight Root CA certificate for proper TLS validation across all services.

**Security Context**: This guide addresses **CWE-295: Improper Certificate Validation** vulnerabilities found in the security audit (see [`SECURITY_TLS_VALIDATION_AUDIT.md`](SECURITY_TLS_VALIDATION_AUDIT.md)).

---

## Quick Start

### ⭐ Recommended: One-Command Fix

**For administrators who need to fix everything**:

```bash
cd self-hosted-ai/
./scripts/fix-all-tls-issues.sh
```

This **master script** orchestrates the entire workflow:
1. Audits current TLS validation status
2. Fixes oauth2-proxy and Grafana configurations
3. Commits changes to git
4. Deploys to Kubernetes cluster
5. Verifies deployment
6. Installs CA certificate on your workstation
7. Tests SSO endpoints

**Time**: ~5 minutes | **Details**: [`scripts/README-TLS-REMEDIATION.md`](../scripts/README-TLS-REMEDIATION.md)

---

### Manual Workflow (Alternative)

If you prefer step-by-step control or need to run individual phases:

#### For End Users (Workstation/Browser)

Install the CA certificate on your local machine to trust the self-signed certificates:

```bash
# Extract and install CA certificate
cd self-hosted-ai/
./scripts/install-ca-certificate.sh all
```

This will:
1. Extract the CA certificate from Kubernetes
2. Install it to your system trust store (Linux/macOS)
3. Export it for service configuration
4. Show Firefox configuration instructions
5. Verify the installation

#### For Administrators (Service Configuration)

Fix TLS validation in oauth2-proxy and Grafana:

```bash
# Check current status
uv run scripts/fix-tls-validation.py check

# Apply fixes
uv run scripts/fix-tls-validation.py fix

# Commit changes
git add helm/oauth2-proxy/values.yaml helm/prometheus/values.yaml
git commit -m "fix(security): enable TLS validation for oauth2-proxy and Grafana"

# Sync ArgoCD
argocd app sync oauth2-proxy
argocd app sync prometheus

# Verify deployment
uv run scripts/fix-tls-validation.py verify
```

---

## Overview

This platform uses **self-signed TLS certificates** issued by a private Certificate Authority (VectorWeight Root CA). To prevent MITM attacks, all services **must validate TLS certificates** properly.

### The Problem

Several services were configured with insecure TLS validation bypass:

| Service | Insecure Setting | Risk Level |
|---------|------------------|------------|
| ArgoCD | `insecureSkipVerify: true` | CRITICAL (✅ FIXED) |
| oauth2-proxy | `sslInsecureSkipVerify: true` | CRITICAL (⚠️ NEEDS FIX) |
| Grafana | `tls_skip_verify_insecure: true` | HIGH (⚠️ NEEDS FIX) |

**Impact**: These settings disable TLS certificate validation, allowing Man-in-the-Middle (MITM) attacks.

### The Solution

Install the VectorWeight Root CA certificate:
1. **System-wide** (for curl, wget, system tools)
2. **Browser-specific** (Firefox, Chrome)
3. **Service-specific** (oauth2-proxy, Grafana, etc.)

---

## Installation Methods

### Method 1: Automated Installation (Recommended)

The `install-ca-certificate.sh` script automates the entire process:

```bash
# Show all available commands
./scripts/install-ca-certificate.sh help

# Complete installation (recommended)
./scripts/install-ca-certificate.sh all

# Step-by-step installation
./scripts/install-ca-certificate.sh extract    # Extract from K8s
./scripts/install-ca-certificate.sh install    # Install to system
./scripts/install-ca-certificate.sh verify     # Verify trust
./scripts/install-ca-certificate.sh export     # Export for services
./scripts/install-ca-certificate.sh firefox    # Firefox instructions
```

**Supported Platforms**:
- Debian/Ubuntu (uses `update-ca-certificates`)
- RHEL/Fedora/CentOS (uses `update-ca-trust`)
- Arch Linux (uses `trust extract-compat`)
- macOS (uses Security.framework)

### Method 2: Manual Installation

If the automated script doesn't work on your platform:

#### Extract Certificate

```bash
# Extract from Kubernetes
kubectl get secret vectorweight-root-ca -n cert-manager \
  -o jsonpath='{.data.tls\.crt}' | base64 -d > vectorweight-ca.crt

# Verify certificate
openssl x509 -in vectorweight-ca.crt -noout -subject -issuer -dates
```

#### Install on Debian/Ubuntu

```bash
sudo cp vectorweight-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

#### Install on RHEL/Fedora/CentOS

```bash
sudo cp vectorweight-ca.crt /etc/pki/ca-trust/source/anchors/
sudo update-ca-trust
```

#### Install on Arch Linux

```bash
sudo cp vectorweight-ca.crt /etc/ca-certificates/trust-source/anchors/
sudo trust extract-compat
```

#### Install on macOS

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  vectorweight-ca.crt
```

### Method 3: Browser-Specific Installation

#### Firefox

Firefox uses its own certificate store (doesn't use system certificates):

1. Open Firefox → **Settings** → **Privacy & Security**
2. Scroll to **Certificates** → Click **View Certificates**
3. Go to **Authorities** tab → Click **Import**
4. Select `vectorweight-ca.crt`
5. Check **"Trust this CA to identify websites"**
6. Click **OK**

#### Chrome/Chromium (Linux)

Chrome uses the system certificate store, so the automated installation should work. If not:

1. Open Chrome → **Settings** → **Privacy and security**
2. Click **Security** → **Manage certificates**
3. Go to **Authorities** tab → Click **Import**
4. Select `vectorweight-ca.crt`
5. Check **"Trust this certificate for identifying websites"**
6. Click **OK**

#### Chrome (macOS)

Chrome uses the macOS Keychain, so the automated installation should work.

#### Safari (macOS)

Safari uses the macOS Keychain, so the automated installation should work.

---

## Service Configuration Fixes

The `fix-tls-validation.py` script automatically updates service configurations.

### What It Does

#### oauth2-proxy Fix

**Before** (INSECURE):
```yaml
config:
  sslInsecureSkipVerify: true  # ← SECURITY VULNERABILITY
```

**After** (SECURE):
```yaml
config:
  sslInsecureSkipVerify: false  # Enable validation

# Mount CA certificate
extraVolumes:
  - name: ca-bundle
    secret:
      secretName: vectorweight-root-ca

extraVolumeMounts:
  - name: ca-bundle
    mountPath: /etc/ssl/certs/vectorweight-ca.crt
    subPath: tls.crt
    readOnly: true

# Configure environment
extraEnv:
  - name: SSL_CERT_FILE
    value: /etc/ssl/certs/vectorweight-ca.crt
```

#### Grafana Fix

**Before** (INSECURE):
```yaml
auth.generic_oauth:
  tls_skip_verify_insecure: true  # ← SECURITY VULNERABILITY
```

**After** (SECURE):
```yaml
auth.generic_oauth:
  tls_skip_verify_insecure: false  # Enable validation
  tls_client_ca: /etc/grafana/ca/tls.crt

# Mount CA certificate
extraSecretMounts:
  - name: ca-cert
    secretName: vectorweight-root-ca
    defaultMode: 0444
    mountPath: /etc/grafana/ca
    readOnly: true
```

### Applying Fixes

```bash
# 1. Check current status
uv run scripts/fix-tls-validation.py check

# Output:
# [FAIL] oauth2-proxy: Using sslInsecureSkipVerify: true (INSECURE)
# [FAIL] Grafana: Using tls_skip_verify_insecure: true (INSECURE)
# [OK] ArgoCD: Proper rootCA configured

# 2. Apply fixes
uv run scripts/fix-tls-validation.py fix

# Output:
# [OK] Disabled sslInsecureSkipVerify
# [OK] Added CA certificate volume
# [OK] Added CA certificate mount
# [OK] Added SSL_CERT_FILE environment variable
# [OK] Updated helm/oauth2-proxy/values.yaml
# ...

# 3. Review changes
git diff helm/oauth2-proxy/values.yaml
git diff helm/prometheus/values.yaml

# 4. Commit
git add helm/oauth2-proxy/values.yaml helm/prometheus/values.yaml
git commit -m "fix(security): enable TLS validation for oauth2-proxy and Grafana

Fixes CWE-295: Improper Certificate Validation

- oauth2-proxy: Mount vectorweight-root-ca, set SSL_CERT_FILE
- Grafana: Mount CA certificate, configure tls_client_ca

Replaces insecure sslInsecureSkipVerify and tls_skip_verify_insecure
with proper certificate trust validation.

Refs: docs/SECURITY_TLS_VALIDATION_AUDIT.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 5. Deploy
git push origin dev

# 6. Sync ArgoCD
argocd app sync oauth2-proxy
argocd app sync prometheus

# 7. Restart pods to load new configuration
kubectl rollout restart deployment/oauth2-proxy -n automation
kubectl rollout restart deployment/prometheus-grafana -n monitoring

# 8. Verify
uv run scripts/fix-tls-validation.py verify
```

---

## Verification

### Verify System Trust

```bash
# Test HTTPS connections
curl -v https://auth.vectorweight.com 2>&1 | grep "SSL certificate verify"
# Should show: SSL certificate verify ok

curl -v https://argocd.vectorweight.com 2>&1 | grep "SSL certificate verify"
# Should show: SSL certificate verify ok

# Test with openssl
openssl s_client -connect auth.vectorweight.com:443 -CAfile /tmp/vectorweight-ca/vectorweight-ca.crt
# Should show: Verify return code: 0 (ok)
```

### Verify Service Configuration

```bash
# Check oauth2-proxy pod environment
kubectl get pod -n automation -l app.kubernetes.io/name=oauth2-proxy -o yaml | grep SSL_CERT_FILE
# Should show: - name: SSL_CERT_FILE

# Check Grafana pod mounts
kubectl get pod -n monitoring -l app.kubernetes.io/name=grafana -o yaml | grep vectorweight-root-ca
# Should show: secretName: vectorweight-root-ca

# Check service logs for TLS errors
kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=100 | grep -i "certificate\|tls"
# Should NOT show certificate verification errors
```

### Verify SSO Login

1. **ArgoCD**: https://argocd.vectorweight.com
   - Click **"LOG IN VIA KEYCLOAK"**
   - Should redirect to Keycloak without certificate warnings
   - Login as `kang` / `banana12`
   - Should redirect back to ArgoCD

2. **Grafana**: https://grafana.vectorweight.com
   - Click **"Sign in with Keycloak"**
   - Should redirect to Keycloak without certificate warnings
   - Login as `kang` / `banana12`
   - Should redirect back to Grafana

3. **Protected Services** (via oauth2-proxy):
   - n8n: https://n8n.vectorweight.com
   - SearXNG: https://search.vectorweight.com
   - LiteLLM: https://llm.vectorweight.com
   - Traefik: https://traefik.vectorweight.com
   - Should all redirect to oauth2-proxy → Keycloak
   - No certificate warnings

---

## Troubleshooting

### Certificate Not Trusted

**Symptom**: `curl: (60) SSL certificate problem: unable to get local issuer certificate`

**Solution**:
```bash
# Re-run installation
./scripts/install-ca-certificate.sh install

# Verify certificate is in trust store
ls -la /usr/local/share/ca-certificates/ | grep vectorweight
# or
ls -la /etc/pki/ca-trust/source/anchors/ | grep vectorweight

# Update trust store manually
sudo update-ca-certificates  # Debian/Ubuntu
sudo update-ca-trust         # RHEL/Fedora
```

### Firefox Still Shows Certificate Warning

**Symptom**: Firefox shows "Your connection is not secure" for vectorweight.com domains

**Solution**:
Firefox uses its own certificate store. Follow the Firefox-specific installation steps above.

### Service Logs Show Certificate Errors

**Symptom**: `kubectl logs` shows `x509: certificate signed by unknown authority`

**Solution**:
```bash
# Check if vectorweight-root-ca secret exists
kubectl get secret vectorweight-root-ca -n cert-manager

# Re-apply service fixes
uv run scripts/fix-tls-validation.py fix

# Restart the affected service
kubectl rollout restart deployment/<service-name> -n <namespace>
```

### Kubernetes Secret Not Found

**Symptom**: `Error from server (NotFound): secrets "vectorweight-root-ca" not found`

**Solution**:
```bash
# Check if cert-manager is deployed
kubectl get pods -n cert-manager

# Check if ClusterIssuer exists
kubectl get clusterissuer

# Manually create the secret (if needed)
# See docs/DEPLOYMENT.md for cert-manager setup instructions
```

---

## Certificate Rotation

The VectorWeight Root CA certificate has an expiration date. To rotate:

### Check Expiration

```bash
kubectl get secret vectorweight-root-ca -n cert-manager \
  -o jsonpath='{.data.tls\.crt}' | base64 -d | \
  openssl x509 -noout -enddate
```

### Rotate Certificate

```bash
# 1. Generate new CA (via cert-manager)
kubectl delete certificate vectorweight-root-ca -n cert-manager
# cert-manager will regenerate automatically

# 2. Wait for new secret
kubectl get secret vectorweight-root-ca -n cert-manager -o yaml

# 3. Re-install on all workstations
./scripts/install-ca-certificate.sh all

# 4. Restart all services
argocd app sync argocd-config
argocd app sync oauth2-proxy
argocd app sync prometheus
```

### Automation (Future)

Add to cron or CI/CD:
```bash
# Monthly certificate check
0 0 1 * * /path/to/install-ca-certificate.sh verify || /path/to/install-ca-certificate.sh all
```

---

## Security Best Practices

### DO ✅

- **Always validate certificates** in production
- **Use `rootCA` or CA bundles** to trust self-signed certificates
- **Monitor certificate expiration** (set up alerts)
- **Rotate certificates regularly** (90 days recommended)
- **Use Let's Encrypt** for public-facing services (free, automated)

### DON'T ❌

- **Never use `insecureSkipVerify: true`** in production
- **Never use `verify: false`** or equivalent
- **Never disable TLS entirely** for authentication
- **Never trust certificates without verifying fingerprint**

### For Production Environments

Consider:
1. **Let's Encrypt**: Free, automated, publicly trusted certificates
2. **Private CA with OCSP**: Certificate revocation checking
3. **mTLS**: Mutual TLS for service-to-service communication
4. **Certificate Monitoring**: Alert on expiry, revocation, invalid certs
5. **Automated Rotation**: Use cert-manager with automated renewal

---

## References

- [OWASP: Transport Layer Protection](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [CWE-295: Improper Certificate Validation](https://cwe.mitre.org/data/definitions/295.html)
- [Security Audit Report](SECURITY_TLS_VALIDATION_AUDIT.md)
- [ArgoCD TLS Fix Documentation](SECURITY_ARGOCD_TLS_FIX.md)

---

## Support

For issues or questions:
1. Check the [Security Audit Report](SECURITY_TLS_VALIDATION_AUDIT.md)
2. Review [OPERATIONS.md](../OPERATIONS.md) troubleshooting section
3. Check service logs: `kubectl logs -f deployment/<name> -n <namespace>`
4. Verify ArgoCD sync status: `argocd app get <app-name>`

---

**Last Updated**: 2026-02-21
**Script Version**: 1.0
**Security Review**: Complete (see SECURITY_TLS_VALIDATION_AUDIT.md)
