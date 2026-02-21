# Certificate Management Quick Reference

**Quick access to certificate installation and TLS validation commands.**

---

## 🚀 Quick Start

### ⭐ One-Command Fix (Recommended)

```bash
cd self-hosted-ai/
./scripts/fix-all-tls-issues.sh
```

**Does everything**: Audit → Fix → Commit → Deploy → Verify → Install CA cert
**Time**: ~5 minutes
**Details**: [`scripts/README-TLS-REMEDIATION.md`](../scripts/README-TLS-REMEDIATION.md)

---

### Manual Workflow (If Needed)

#### Install CA Certificate (End Users)

```bash
cd self-hosted-ai/
./scripts/install-ca-certificate.sh all
```

#### Fix Service TLS Validation (Administrators)

```bash
uv run scripts/fix-tls-validation.py fix
git add helm/oauth2-proxy/values.yaml helm/prometheus/values.yaml
git commit -m "fix(security): enable TLS validation"
argocd app sync oauth2-proxy prometheus
```

---

## 📋 Common Commands

### Certificate Installation

| Task | Command |
|------|---------|
| Complete installation | `./scripts/install-ca-certificate.sh all` |
| Extract from K8s only | `./scripts/install-ca-certificate.sh extract` |
| Install to system | `./scripts/install-ca-certificate.sh install` |
| Verify trust | `./scripts/install-ca-certificate.sh verify` |
| Firefox instructions | `./scripts/install-ca-certificate.sh firefox` |
| Export for services | `./scripts/install-ca-certificate.sh export` |

### Service Configuration

| Task | Command |
|------|---------|
| Check TLS status | `uv run scripts/fix-tls-validation.py check` |
| Apply fixes | `uv run scripts/fix-tls-validation.py fix` |
| Verify deployment | `uv run scripts/fix-tls-validation.py verify` |

### Manual Certificate Operations

| Task | Command |
|------|---------|
| Extract CA cert | `kubectl get secret vectorweight-root-ca -n cert-manager -o jsonpath='{.data.tls\.crt}' \| base64 -d > ca.crt` |
| View cert info | `openssl x509 -in ca.crt -noout -subject -issuer -dates` |
| Check expiry | `openssl x509 -in ca.crt -noout -enddate` |
| Verify fingerprint | `openssl x509 -in ca.crt -noout -fingerprint -sha256` |

### Verification

| Task | Command |
|------|---------|
| Test HTTPS | `curl -v https://auth.vectorweight.com 2>&1 \| grep "SSL certificate verify"` |
| Test with openssl | `openssl s_client -connect auth.vectorweight.com:443 -CAfile ca.crt` |
| Check service logs | `kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=50 \| grep -i tls` |

---

## 🔧 ArgoCD Operations

### Sync Applications

```bash
# Sync all auth-related apps
argocd app sync argocd-config oauth2-proxy prometheus

# Restart pods
kubectl rollout restart deployment/argocd-server -n argocd
kubectl rollout restart deployment/oauth2-proxy -n automation
kubectl rollout restart deployment/prometheus-grafana -n monitoring
```

### Check App Status

```bash
# Check sync status
argocd app list | grep -E "argocd-config|oauth2-proxy|prometheus"

# Get detailed app status
argocd app get oauth2-proxy
```

---

## 🩺 Troubleshooting

### Certificate Not Trusted

```bash
# Debian/Ubuntu
sudo update-ca-certificates

# RHEL/Fedora
sudo update-ca-trust

# macOS
security find-certificate -a -c "VectorWeight Root CA"
```

### Service Certificate Errors

```bash
# Check if secret exists
kubectl get secret vectorweight-root-ca -n cert-manager

# Verify secret is mounted in pod
kubectl get pod -n automation -l app.kubernetes.io/name=oauth2-proxy -o yaml | grep vectorweight

# Check pod environment
kubectl exec -n automation deployment/oauth2-proxy -- env | grep SSL_CERT_FILE
```

### Browser Shows Warning

**Firefox**: Uses own cert store, import manually
```
Settings → Privacy & Security → Certificates → View Certificates
→ Authorities → Import → Select ca.crt
```

**Chrome (Linux)**: Uses system store, run:
```bash
sudo update-ca-certificates
```

**Chrome (macOS)**: Uses Keychain, run:
```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ca.crt
```

---

## 📊 Status Dashboard

### Check All Services

```bash
# Quick status check
uv run scripts/fix-tls-validation.py check

# Output:
# [OK]   ArgoCD: Proper rootCA configured
# [FAIL] oauth2-proxy: Using sslInsecureSkipVerify: true (INSECURE)
# [FAIL] Grafana: Using tls_skip_verify_insecure: true (INSECURE)
```

### Test SSO Logins

| Service | URL | Method |
|---------|-----|--------|
| ArgoCD | https://argocd.vectorweight.com | Native OIDC |
| Grafana | https://grafana.vectorweight.com | Native OAuth |
| n8n | https://n8n.vectorweight.com | oauth2-proxy |
| SearXNG | https://search.vectorweight.com | oauth2-proxy |
| LiteLLM | https://llm.vectorweight.com | oauth2-proxy |

---

## 🔐 Security Checklist

### Before Deployment

- [ ] Run `uv run scripts/fix-tls-validation.py check`
- [ ] Verify no `insecureSkipVerify` in configs
- [ ] Test local certificate trust: `curl -v https://auth.vectorweight.com`
- [ ] Review git diff for security implications

### After Deployment

- [ ] Run `uv run scripts/fix-tls-validation.py verify`
- [ ] Check service logs for TLS errors
- [ ] Test SSO login flows
- [ ] Verify certificate expiry dates

### Regular Maintenance

- [ ] Monthly: Check certificate expiry
- [ ] Quarterly: Rotate certificates
- [ ] After cert rotation: Re-install on workstations

---

## 📚 Full Documentation

- **Complete Guide**: [`CERTIFICATE_TRUST_GUIDE.md`](CERTIFICATE_TRUST_GUIDE.md)
- **Security Audit**: [`SECURITY_TLS_VALIDATION_AUDIT.md`](SECURITY_TLS_VALIDATION_AUDIT.md)
- **ArgoCD Fix**: [`SECURITY_ARGOCD_TLS_FIX.md`](SECURITY_ARGOCD_TLS_FIX.md)
- **Operations**: [`../OPERATIONS.md`](../OPERATIONS.md)

---

## 🆘 Emergency Procedures

### Certificate Expired

```bash
# 1. Generate new CA
kubectl delete certificate vectorweight-root-ca -n cert-manager
# Wait 30 seconds for cert-manager to regenerate

# 2. Verify new certificate
kubectl get secret vectorweight-root-ca -n cert-manager

# 3. Sync all services
argocd app sync --force argocd-config oauth2-proxy prometheus

# 4. Re-install on workstations
./scripts/install-ca-certificate.sh all
```

### MITM Attack Detected

```bash
# 1. Check certificate fingerprint
kubectl get secret vectorweight-root-ca -n cert-manager \
  -o jsonpath='{.data.tls\.crt}' | base64 -d | \
  openssl x509 -noout -fingerprint -sha256

# 2. Compare with known good fingerprint
# (Store fingerprint in password manager)

# 3. If mismatch, investigate:
kubectl get events -n cert-manager --sort-by='.lastTimestamp'
kubectl logs -n cert-manager -l app=cert-manager
```

### Service Down After Fix

```bash
# 1. Check pod status
kubectl get pods -n automation -l app.kubernetes.io/name=oauth2-proxy

# 2. Check logs
kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=100

# 3. Rollback if needed
git revert HEAD
argocd app sync oauth2-proxy --force

# 4. File issue with logs
```

---

**Last Updated**: 2026-02-21
**Maintained By**: Security Team
**Report Issues**: See [`SECURITY_TLS_VALIDATION_AUDIT.md`](SECURITY_TLS_VALIDATION_AUDIT.md)
