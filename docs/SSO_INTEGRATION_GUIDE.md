# SSO Integration Guide

This document explains the SSO (Single Sign-On) architecture and integration process for the self-hosted AI platform.

**Last Updated**: 2026-02-21

---

## Overview

The platform uses **Keycloak** as the central identity provider with two integration patterns:

1. **oauth2-proxy ForwardAuth** - For services without native OIDC support
2. **Native OIDC Integration** - For services with built-in OIDC capabilities

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User Browser                                                │
└────────────┬────────────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────────────┐
│  Traefik Ingress (homelab:192.168.1.170)                    │
│  - Routes by hostname                                        │
│  - Applies ForwardAuth middleware OR passes to app          │
└────────┬─────────────────────────┬──────────────────────────┘
         │                         │
         │ (ForwardAuth)           │ (Native OIDC)
         ↓                         ↓
┌────────────────────┐    ┌────────────────────────┐
│  oauth2-proxy       │    │  App (Open WebUI,      │
│  (automation ns)    │    │  Grafana, GitLab)      │
│                     │    │                        │
│  Checks auth with → │────┤  Redirects to →        │
│  Keycloak           │    │  Keycloak directly     │
└────────────────────┘    └────────────────────────┘
         │                         │
         └──────────┬──────────────┘
                    ↓
         ┌────────────────────┐
         │  Keycloak           │
         │  (auth.vectorweight │
         │   .com)             │
         │                     │
         │  Realm: vectorweight│
         │  Users: kang, admin │
         └────────────────────┘
```

---

## Integration Patterns

### Pattern A: oauth2-proxy ForwardAuth

**Used by**: n8n, SearXNG, LiteLLM, Traefik Dashboard, Longhorn, Prometheus, OpenObserve, Jaeger

**How it works**:
1. User requests `https://n8n.vectorweight.com`
2. Traefik applies `n8n-forward-auth` middleware
3. Middleware calls `oauth2-proxy` at `/oauth2/auth`
4. If not authenticated, oauth2-proxy redirects to Keycloak
5. User logs in at Keycloak
6. Keycloak redirects back to `https://n8n.vectorweight.com/oauth2/callback`
7. oauth2-proxy sets cookie and passes request to n8n with auth headers
8. Subsequent requests use cookie, no re-authentication needed

**Configuration files**:
- `helm/oauth2-proxy/values.yaml` - Main config, `protectedServices` list
- `helm/oauth2-proxy/templates/middleware.yaml` - Generates ForwardAuth middleware per service
- `helm/<service>/templates/ingressroute.yaml` - References middleware

**Auth headers passed to application**:
- `X-Auth-Request-User`: username
- `X-Auth-Request-Email`: email
- `X-Auth-Request-Access-Token`: JWT token
- `Authorization: Bearer <token>`

### Pattern B: Native OIDC

**Used by**: Open WebUI, Grafana, GitLab

**How it works**:
1. User requests `https://ai.vectorweight.com`
2. Application checks for session cookie
3. If not authenticated, app redirects directly to Keycloak
4. User logs in at Keycloak
5. Keycloak redirects to `https://ai.vectorweight.com/auth/callback` (app-specific)
6. Application validates token and creates session
7. Subsequent requests use app's session management

**Configuration files**:
- **Open WebUI**: `helm/open-webui/values.yaml` - `OPENID_PROVIDER_URL` env var
- **Grafana**: `argocd/helm/prometheus/values.yaml` - `auth.generic_oauth` section
- **GitLab**: `argocd/helm/gitlab/values.yaml` - `omniauth.providers` with `gitlab-oidc-provider` secret

---

## Services SSO Status

| Service | URL | Pattern | Status | Notes |
|---------|-----|---------|--------|-------|
| **Open WebUI** | ai.vectorweight.com | Native OIDC | ✅ Active | Shows "Login with Keycloak" button |
| **Grafana** | grafana.vectorweight.com | Native OIDC | ✅ Active | Auto-redirects to SSO |
| **GitLab** | git.vectorweight.com | Native OIDC | ✅ Fixed | Requires `gitlab-oidc-provider` secret |
| **n8n** | n8n.vectorweight.com | ForwardAuth | ✅ Fixed | Removed basic auth conflict |
| **SearXNG** | search.vectorweight.com | ForwardAuth | ✅ Active | Auto-redirect |
| **LiteLLM** | llm.vectorweight.com | ForwardAuth | ✅ Active | Auto-redirect |
| **Traefik** | traefik.vectorweight.com | ForwardAuth | ✅ Active | Dashboard protected |
| **Longhorn** | longhorn.vectorweight.com | ForwardAuth | ✅ Active | Storage UI |
| **Prometheus** | prometheus.vectorweight.com | ForwardAuth | ✅ Active | Metrics UI |
| **ArgoCD** | argocd.vectorweight.com | Native OIDC | ✅ Fixed | Configured via argocd-cm |
| **OpenObserve** | observe.vectorweight.com | ForwardAuth | ✅ Fixed | IngressRoute created |
| **Jaeger** | traces.vectorweight.com | ForwardAuth | ✅ Fixed | Added to protected services |
| **Keycloak** | auth.vectorweight.com | N/A | ✅ Active | Identity provider itself |

---

## OIDC Client Inventory

**Keycloak Realm**: `vectorweight`
**Issuer URL**: `https://auth.vectorweight.com/realms/vectorweight`

| Client ID | Namespace | Secret Name | Used By | Redirect URIs |
|-----------|-----------|-------------|---------|---------------|
| `open-webui` | ai-services | `keycloak-oidc-secret` | Open WebUI | `https://ai.vectorweight.com/auth/callback` |
| `grafana` | monitoring | `grafana-oidc-secret` | Grafana | `https://grafana.vectorweight.com/login/generic_oauth` |
| `gitlab` | gitlab | `gitlab-oidc-provider` | GitLab | `https://git.vectorweight.com/users/auth/openid_connect/callback` |
| `n8n` | automation | `n8n-oidc-secret` | **oauth2-proxy (shared)** | `https://*.vectorweight.com/oauth2/callback` |
| `argocd` | argocd | `argocd-oidc-secret` | ArgoCD | `https://argocd.vectorweight.com/auth/callback` |
| `searxng` | ai-services | `searxng-oidc-secret` | *Unused* | Created but not consumed |
| `litellm` | ai-services | `litellm-oidc-secret` | *Unused* | Created but not consumed |
| `traefik` | traefik | `traefik-oidc-secret` | *Unused* | Created but not consumed |
| `prometheus` | monitoring | `prometheus-oidc-secret` | *Unused* | Created but not consumed |
| `longhorn` | longhorn-system | `longhorn-oidc-secret` | *Unused* | Created but not consumed |
| `dify` | dify | `dify-oidc-secret` | *Unused* | Service not deployed |
| `ana-agent` | ana | `ana-oidc-secret` | *Planned* | aNa agent (external repo) |

**Note**: oauth2-proxy uses a **single shared client** (`n8n`) for all ForwardAuth-protected services. The per-service secrets exist but are not consumed. This is intentional to simplify redirect URI management.

---

## Users

**Created by**: `scripts/setup-keycloak-realm.sh`

| Username | Email | Password | Roles | First Login |
|----------|-------|----------|-------|-------------|
| `kang` | tz-dev@vectorweight.com | `banana12` | `admin` (realm role) | No password change required |
| `admin` | admin@vectorweight.com | *(random, see `keycloak-admin-secret`)* | Keycloak admin | N/A (admin console only) |

**Retrieve admin password**:
```bash
kubectl get secret keycloak-admin-secret -n auth -o jsonpath='{.data.admin-password}' | base64 -d
```

---

## Setup Process

### Initial Deployment

1. **Deploy Keycloak** (sync wave 3):
   ```bash
   kubectl apply -f argocd/applications/keycloak.yaml
   argocd app sync keycloak
   ```

2. **Create Realm and Clients**:
   ```bash
   ./scripts/setup-keycloak-realm.sh
   ```

   This script:
   - Creates `vectorweight` realm
   - Creates 12 OIDC clients with secrets
   - Creates user `kang` with password `banana12`
   - Assigns realm `admin` role to `kang`
   - Creates K8s secrets in respective namespaces

3. **Deploy oauth2-proxy** (sync wave 5):
   ```bash
   kubectl apply -f argocd/applications/oauth2-proxy.yaml
   argocd app sync oauth2-proxy
   ```

4. **Deploy ArgoCD SSO config** (sync wave 4):
   ```bash
   kubectl apply -f argocd/applications/argocd-config.yaml
   argocd app sync argocd-config
   ```

5. **Deploy services** (sync waves 5-7):
   - Services with native OIDC will auto-configure
   - Services with ForwardAuth will be protected automatically

### Sealing Secrets for GitOps

After initial setup, seal the OIDC secrets for Git storage:

```bash
./scripts/seal-oidc-secrets.sh
git add argocd/sealed-secrets/*-oidc-secret.yaml
git commit -m "feat(sso): seal OIDC secrets for GitOps"
git push origin dev
```

**Why seal secrets?**
- Enables cluster rebuild from Git alone (no manual `setup-keycloak-realm.sh` needed)
- Follows ADR-006 (SealedSecrets for GitOps)
- Safe to commit to public repos (encrypted with cluster public key)

---

## Troubleshooting

### "TLS certificate verification failed" (ArgoCD)

**Symptom**: `x509: certificate signed by unknown authority`

**Cause**: ArgoCD doesn't trust the self-signed `vectorweight-ca-issuer` certificate.

**Fix**: The `helm/argocd-config` chart sets `insecureSkipVerify: true` in the OIDC config. If you prefer to trust the CA:

```yaml
# helm/argocd-config/templates/configmap.yaml
oidc.config: |
  name: Keycloak
  issuer: https://auth.vectorweight.com/realms/vectorweight
  rootCA: |
    -----BEGIN CERTIFICATE-----
    <contents of vectorweight-root-ca certificate>
    -----END CERTIFICATE-----
```

Get the CA cert:
```bash
kubectl get secret vectorweight-root-ca -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d
```

### Service shows native login instead of SSO

**Possible causes**:

1. **oauth2-proxy conflict** (n8n): Service has both ForwardAuth AND native auth enabled
   - **Fix**: Remove native auth env vars (e.g., `N8N_BASIC_AUTH_USER`)

2. **Missing OIDC secret** (GitLab): Secret name mismatch or wrong format
   - **Fix**: Ensure `gitlab-oidc-provider` secret exists with `provider` key containing OmniAuth JSON

3. **OIDC not enabled** (Grafana): Config missing in values.yaml
   - **Fix**: Check `auth.generic_oauth.enabled: true` in Grafana values

### SSO works but user has no permissions

**Symptom**: User can log in but sees "403 Forbidden" or "Access Denied"

**Cause**: Role mapping not configured.

**Fix (Grafana example)**:
```yaml
# argocd/helm/prometheus/values.yaml
grafana:
  grafana.ini:
    auth.generic_oauth:
      role_attribute_path: "contains(realm_access.roles, 'admin') && 'Admin' || 'Viewer'"
```

For other services, check their OIDC role/group mapping documentation.

### oauth2-proxy returns 500 error

**Check logs**:
```bash
kubectl logs -n automation deployment/oauth2-proxy -f
```

**Common issues**:
- `n8n-oidc-secret` missing in `automation` namespace
- Cookie secret wrong length (must be 16, 24, or 32 bytes)
- Keycloak unreachable from oauth2-proxy pod

### Redirect loop

**Symptom**: Browser keeps redirecting between service and Keycloak

**Cause**: `/oauth2/` path not routed to oauth2-proxy (circular forward-auth)

**Fix**: Ensure IngressRoute has two routes:
```yaml
routes:
  # oauth2 callback (no middleware)
  - match: Host(`service.vectorweight.com`) && PathPrefix(`/oauth2/`)
    kind: Rule
    services:
      - name: oauth2-proxy
        namespace: automation
        port: 4180
  # Application (with forward-auth middleware)
  - match: Host(`service.vectorweight.com`)
    kind: Rule
    middlewares:
      - name: service-forward-auth
        namespace: automation
    services:
      - name: service
        port: 8080
```

---

## Adding a New Service with SSO

### Option 1: ForwardAuth (for services without native OIDC)

1. **Add to oauth2-proxy protectedServices**:
   ```yaml
   # helm/oauth2-proxy/values.yaml
   protectedServices:
     - name: new-service
   ```

2. **Create IngressRoute with middleware**:
   ```yaml
   # helm/new-service/templates/ingressroute.yaml
   apiVersion: traefik.io/v1alpha1
   kind: IngressRoute
   metadata:
     name: new-service
   spec:
     entryPoints:
       - websecure
     routes:
       - match: Host(`new-service.vectorweight.com`) && PathPrefix(`/oauth2/`)
         kind: Rule
         services:
           - name: oauth2-proxy
             namespace: automation
             port: 4180
       - match: Host(`new-service.vectorweight.com`)
         kind: Rule
         middlewares:
           - name: new-service-forward-auth
             namespace: automation
         services:
           - name: new-service
             port: 8080
     tls:
       secretName: vectorweight-wildcard-tls
   ```

3. **Deploy**:
   ```bash
   git add helm/oauth2-proxy/values.yaml helm/new-service/
   git commit -m "feat(sso): add new-service to SSO-protected services"
   git push origin dev
   ```

### Option 2: Native OIDC (for services with built-in support)

1. **Add OIDC client to Keycloak script**:
   ```bash
   # scripts/setup-keycloak-realm.sh
   # Add to client creation section
   NEW_SERVICE_SECRET=$(openssl rand -hex 32)
   create_oidc_client "new-service" "$NEW_SERVICE_SECRET" "https://new-service.vectorweight.com/auth/callback"

   # Add to secret creation section
   kubectl create secret generic new-service-oidc-secret -n new-service-namespace \
     --from-literal=client-id=new-service \
     --from-literal=client-secret="$NEW_SERVICE_SECRET" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **Configure service OIDC settings**:
   ```yaml
   # helm/new-service/values.yaml
   env:
     OIDC_ISSUER_URL: "https://auth.vectorweight.com/realms/vectorweight"
     OIDC_CLIENT_ID: "new-service"
     OIDC_CLIENT_SECRET:
       secretName: new-service-oidc-secret
       key: client-secret
     OIDC_REDIRECT_URI: "https://new-service.vectorweight.com/auth/callback"
   ```

3. **Run setup and deploy**:
   ```bash
   ./scripts/setup-keycloak-realm.sh  # Creates new client
   ./scripts/seal-oidc-secrets.sh      # Seal the secret
   git add argocd/sealed-secrets/new-service-oidc-secret.yaml
   git add helm/new-service/ scripts/setup-keycloak-realm.sh
   git commit -m "feat(sso): add native OIDC for new-service"
   git push origin dev
   ```

---

## References

- [Keycloak Documentation](https://www.keycloak.org/docs/latest/)
- [oauth2-proxy Documentation](https://oauth2-proxy.github.io/oauth2-proxy/)
- [Traefik ForwardAuth Middleware](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)
- [SealedSecrets](https://github.com/bitnami-labs/sealed-secrets)
- [ARCHITECTURE.md ADR-006](../ARCHITECTURE.md) - SealedSecrets decision
- [OPERATIONS.md](../OPERATIONS.md) - Service endpoints

---

**Document Version**: 1.0
**Last Updated**: 2026-02-21
**Maintained By**: Platform Team
