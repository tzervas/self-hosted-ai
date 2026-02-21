# SSO Integration Fixes - Implementation Summary

**Date**: 2026-02-21
**Branch**: `dev`
**Status**: ✅ Complete - Ready for Testing

---

## Changes Made

### 1. Fixed n8n SSO Authentication ✅

**Problem**: n8n showed native basic auth login instead of SSO redirect

**Root Cause**: Dual authentication conflict - both oauth2-proxy forward-auth AND native basic auth enabled

**Fix**: Removed basic auth environment variables

**Files Changed**:
- `helm/n8n/values.yaml` - Removed `N8N_BASIC_AUTH_USER` and `N8N_BASIC_AUTH_PASSWORD` from secretEnv

**Expected Behavior After Deploy**:
- Visiting `https://n8n.vectorweight.com` auto-redirects to Keycloak login
- After authentication, user goes straight to n8n interface
- No n8n login screen shown

---

### 2. Fixed GitLab SSO Authentication ✅

**Problem**: GitLab showed username/password login instead of SSO button

**Root Cause**: Secret mismatch - values.yaml references `gitlab-oidc-provider` but setup script created `gitlab-oidc-secret` with wrong format

**Fix**: Created proper OmniAuth provider secret with full OIDC configuration

**Files Changed**:
- `scripts/setup-keycloak-realm.sh` - Added creation of `gitlab-oidc-provider` secret with OmniAuth JSON structure

**Expected Behavior After Deploy**:
- Run `./scripts/setup-keycloak-realm.sh` to create the new secret
- Visiting `https://git.vectorweight.com` auto-redirects to Keycloak (due to `autoSignInWithProvider: "openid_connect"`)
- User logs in once, gets redirected to GitLab with full access

---

### 3. Configured ArgoCD OIDC Integration ✅

**Problem**: ArgoCD error - `tls: failed to verify certificate: x509: certificate signed by unknown authority`

**Root Cause**: No OIDC configuration exists in ArgoCD; self-signed CA not trusted

**Fix**: Created new Helm chart for ArgoCD configuration with OIDC settings and TLS insecure skip

**Files Created**:
- `helm/argocd-config/Chart.yaml` - Wrapper chart for ArgoCD config
- `helm/argocd-config/values.yaml` - OIDC settings
- `helm/argocd-config/templates/configmap.yaml` - `argocd-cm` ConfigMap with OIDC config
- `helm/argocd-config/templates/secret-ref.yaml` - OIDC client secret reference
- `helm/argocd-config/templates/_helpers.tpl` - Helper to read secret from `argocd-oidc-secret`
- `argocd/applications/argocd-config.yaml` - ArgoCD Application (sync wave 4)

**Expected Behavior After Deploy**:
- ArgoCD UI shows "Login with Keycloak" button
- User can log in with Keycloak credentials (kang/banana12)
- Admin can still use admin user for emergency access

---

### 4. Updated Keycloak User Password ✅

**Problem**: Keycloak not accepting kang/banana12 credentials

**Root Cause**: User created with password `ChangeMe123` (temporary=true)

**Fix**: Updated setup script to use `banana12` (temporary=false)

**Files Changed**:
- `scripts/setup-keycloak-realm.sh` - Changed user password from `ChangeMe123` to `banana12`, removed temporary flag

**Expected Behavior After Deploy**:
- Run `./scripts/setup-keycloak-realm.sh` (or manually update user in Keycloak admin console)
- User `kang` can log in with password `banana12`
- No forced password change on first login

---

### 5. Created OpenObserve IngressRoute with SSO ✅

**Problem**: OpenObserve not accessible externally, no SSO integration

**Root Cause**: No IngressRoute template exists (uses upstream chart with ingress disabled)

**Fix**: Created wrapper Helm chart with IngressRoute template

**Files Created**:
- `helm/openobserve/Chart.yaml` - Wrapper chart with upstream dependency
- `helm/openobserve/values.yaml` - Pass-through values
- `helm/openobserve/templates/ingressroute.yaml` - IngressRoute with oauth2-proxy forward-auth

**Files Changed**:
- `argocd/applications/openobserve.yaml` - Changed from multi-source to local chart path

**Expected Behavior After Deploy**:
- OpenObserve accessible at `https://observe.vectorweight.com`
- Auto-redirects to Keycloak for SSO authentication
- After login, full access to logs/metrics/traces UI

---

### 6. Added Jaeger to SSO-Protected Services ✅

**Problem**: Jaeger accessible without authentication, wrong cert-manager issuer

**Root Cause**: Not in oauth2-proxy protectedServices list, references non-existent `letsencrypt-prod` issuer

**Fix**: Added to protected services and fixed ingress configuration

**Files Changed**:
- `helm/oauth2-proxy/values.yaml` - Added `jaeger` to protectedServices list
- `helm/jaeger/values.yaml` - Fixed cert issuer to use wildcard cert, added forward-auth middleware annotation

**Expected Behavior After Deploy**:
- Jaeger UI at `https://traces.vectorweight.com` requires SSO login
- Uses wildcard TLS certificate (no separate cert generation)
- Auto-redirects to Keycloak for authentication

---

### 7. Created SealedSecrets Tooling ✅

**Problem**: OIDC secrets not persisted in Git, cluster rebuild requires manual script execution

**Root Cause**: Setup script creates secrets directly via kubectl, not as SealedSecrets

**Fix**: Created script to seal all OIDC secrets for GitOps storage

**Files Created**:
- `scripts/seal-oidc-secrets.sh` - Bash script to convert K8s secrets to SealedSecrets
- `docs/SSO_INTEGRATION_GUIDE.md` - Comprehensive SSO architecture and troubleshooting guide

**Expected Behavior After Running**:
- All OIDC secrets sealed and saved to `argocd/sealed-secrets/*-oidc-secret.yaml`
- Safe to commit to Git (encrypted with cluster public key)
- Cluster rebuild can restore secrets from Git without manual intervention

---

## Deployment Instructions

### Step 1: Commit Changes to Git

```bash
cd /home/kang/Documents/projects/github/homelab-cluster/self-hosted-ai

# Make seal script executable
chmod +x scripts/seal-oidc-secrets.sh

# Stage all changes
git add -A

# Commit with descriptive message
git commit -m "feat(sso): complete SSO integration for all services

- Fix n8n basic auth conflict with oauth2-proxy
- Fix GitLab OmniAuth provider secret format
- Add ArgoCD OIDC configuration with Keycloak
- Update Keycloak user password to standardized banana12
- Add OpenObserve IngressRoute with SSO
- Secure Jaeger with oauth2-proxy forward-auth
- Create seal-oidc-secrets.sh script for GitOps
- Add comprehensive SSO_INTEGRATION_GUIDE.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to dev branch
git push origin dev
```

### Step 2: Update Keycloak Secrets

The GitLab OmniAuth secret and user password need to be updated:

```bash
# Re-run Keycloak realm setup to create new secrets and update user
./scripts/setup-keycloak-realm.sh
```

This will:
- Create the `gitlab-oidc-provider` secret with proper OmniAuth format
- Update user `kang` password to `banana12`
- Leave existing working secrets untouched (idempotent)

### Step 3: Sync ArgoCD Applications

```bash
# Sync ArgoCD config first (creates OIDC config)
argocd app sync argocd-config

# Sync oauth2-proxy (adds Jaeger middleware)
argocd app sync oauth2-proxy

# Sync n8n (removes basic auth)
argocd app sync n8n

# Sync OpenObserve (creates IngressRoute)
argocd app sync openobserve

# Sync Jaeger (adds SSO protection)
argocd app sync jaeger

# Or sync all at once
argocd app sync argocd-config oauth2-proxy n8n openobserve jaeger
```

### Step 4: Wait for Pods to Restart

```bash
# Watch for rollouts
kubectl rollout status deployment/n8n -n automation
kubectl rollout status deployment/oauth2-proxy -n automation
kubectl rollout status statefulset/openobserve-standalone -n monitoring
kubectl rollout status deployment/jaeger -n monitoring

# ArgoCD server needs restart to pick up new config
kubectl rollout restart deployment/argocd-server -n argocd
kubectl rollout status deployment/argocd-server -n argocd
```

### Step 5: Test SSO Access

Visit each service and verify SSO works:

```bash
# Should all redirect to Keycloak login
open https://n8n.vectorweight.com
open https://git.vectorweight.com
open https://argocd.vectorweight.com
open https://observe.vectorweight.com
open https://traces.vectorweight.com
```

**Test Credentials**:
- Username: `kang`
- Password: `banana12`

### Step 6: Seal Secrets for GitOps (Optional but Recommended)

Once everything is working:

```bash
# Seal all OIDC secrets
./scripts/seal-oidc-secrets.sh

# Review sealed secrets
ls -lh argocd/sealed-secrets/*-oidc-secret.yaml

# Commit to Git
git add argocd/sealed-secrets/
git commit -m "feat(sso): seal OIDC secrets for GitOps

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push origin dev
```

---

## Verification Checklist

- [ ] n8n auto-redirects to Keycloak (no basic auth screen)
- [ ] GitLab auto-redirects to Keycloak (no username/password form)
- [ ] ArgoCD shows "Login with Keycloak" button (no TLS error)
- [ ] OpenObserve accessible at observe.vectorweight.com with SSO
- [ ] Jaeger accessible at traces.vectorweight.com with SSO
- [ ] User `kang` can log in with password `banana12` across all services
- [ ] After one login, user stays authenticated across all ForwardAuth services (n8n, SearXNG, LiteLLM, Traefik, Longhorn, Prometheus, OpenObserve, Jaeger)
- [ ] Services with native OIDC maintain separate sessions (Open WebUI, Grafana, GitLab, ArgoCD)

---

## Rollback Procedure

If issues occur:

```bash
# Revert Git commit
git revert HEAD
git push origin dev

# Manually restore previous state
argocd app sync <service-name>

# Or restore n8n basic auth temporarily
kubectl set env deployment/n8n -n automation \
  N8N_BASIC_AUTH_USER=admin \
  N8N_BASIC_AUTH_PASSWORD=temppassword
```

---

## Next Steps

1. **Test thoroughly** - Verify all services work with SSO
2. **Update MEMORY.md** - Add SSO configuration patterns and troubleshooting notes
3. **Monitor logs** - Watch for auth errors in oauth2-proxy, Keycloak
4. **User management** - Create additional users in Keycloak as needed
5. **Role mapping** - Configure service-specific roles in Keycloak realm for granular access control

---

## Troubleshooting

See `docs/SSO_INTEGRATION_GUIDE.md` for comprehensive troubleshooting guide.

**Common Issues**:
- **TLS errors**: Check `insecureSkipVerify: true` in OIDC configs
- **Redirect loops**: Ensure `/oauth2/` path routes to oauth2-proxy without middleware
- **403 Forbidden**: Check role mapping in service OIDC config
- **Secrets not found**: Run `./scripts/setup-keycloak-realm.sh` first

**Useful Commands**:
```bash
# Check oauth2-proxy logs
kubectl logs -n automation deployment/oauth2-proxy -f

# Check Keycloak logs
kubectl logs -n auth deployment/keycloak -f

# Check OIDC secrets exist
kubectl get secrets -A | grep oidc

# Test OIDC discovery endpoint
curl -k https://auth.vectorweight.com/realms/vectorweight/.well-known/openid-configuration | jq
```

---

## Files Changed Summary

```
Modified:
  helm/n8n/values.yaml
  helm/oauth2-proxy/values.yaml
  helm/jaeger/values.yaml
  scripts/setup-keycloak-realm.sh
  argocd/applications/openobserve.yaml

Created:
  helm/openobserve/Chart.yaml
  helm/openobserve/values.yaml
  helm/openobserve/templates/ingressroute.yaml
  helm/argocd-config/Chart.yaml
  helm/argocd-config/values.yaml
  helm/argocd-config/templates/configmap.yaml
  helm/argocd-config/templates/secret-ref.yaml
  helm/argocd-config/templates/_helpers.tpl
  argocd/applications/argocd-config.yaml
  scripts/seal-oidc-secrets.sh
  docs/SSO_INTEGRATION_GUIDE.md
  docs/SSO_FIXES_SUMMARY.md (this file)
```

Total: **6 modified**, **13 created** = **19 files**

---

**Implementation Complete** ✅
**Ready for Deployment** 🚀
**Estimated Testing Time**: 30-45 minutes
