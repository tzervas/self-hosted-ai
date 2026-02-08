# Automation Guide

This document describes the automated deployment and sync mechanisms for the self-hosted AI platform.

## Overview

The platform uses a multi-layered automation approach:

1. **ArgoCD Auto-Sync**: Automatically syncs Git changes to cluster
2. **GitHub Actions**: Triggers ArgoCD refreshes on push to main
3. **ArgoCD Hooks**: Handles StatefulSet restarts automatically
4. **Self-Healing**: Automatically corrects drift from desired state

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Developer pushes to main branch                            │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │  GitHub Actions  │
        │  (.github/       │
        │   workflows/)    │
        └────────┬─────────┘
                 │
     ┌───────────┴────────────┐
     │                        │
┌────▼─────────┐  ┌──────────▼─────┐
│ Detect       │  │ Trigger ArgoCD │
│ Changed      │  │ App Refresh    │
│ Helm Charts  │  │ + Sync         │
└────┬─────────┘  └──────┬─────────┘
     │                   │
     └──────────┬────────┘
                │
        ┌───────▼────────┐
        │  ArgoCD Syncs  │
        │  Applications  │
        └───────┬────────┘
                │
        ┌───────▼──────────┐
        │  PreSync Hook    │
        │  (Scale down     │
        │   StatefulSets)  │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐
        │  Apply Manifests │
        │  (New config)    │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐
        │  PostSync Hook   │
        │  (Verify health  │
        │   & rootless)    │
        └──────────────────┘
```

## Components

### 1. ArgoCD Auto-Sync

**Location**: `argocd/applications/*.yaml`

All ArgoCD applications are configured with:
```yaml
syncPolicy:
  automated:
    prune: true       # Remove resources not in Git
    selfHeal: true    # Automatically fix drift
  syncOptions:
    - CreateNamespace=true
```

**Behavior**:
- **prune**: Deletes resources removed from Git
- **selfHeal**: Reverts manual changes back to Git state
- Checks Git every 3 minutes (ArgoCD default)

**Affected Applications**:
- postgresql
- redis
- open-webui
- searxng
- litellm
- n8n
- ollama
- All other ArgoCD apps

### 2. GitHub Actions Workflow

**Location**: `.github/workflows/argocd-sync.yml`

**Triggers**:
- Push to `main` branch
- Changes to:
  - `helm/**` (Helm charts)
  - `argocd/applications/**` (ArgoCD apps)
  - `policies/**` (Kyverno policies)

**Workflow Steps**:

1. **Detect Changed Files**
   ```bash
   git diff --name-only HEAD^ HEAD
   ```

2. **Refresh Affected Apps**
   - Maps changed Helm charts to ArgoCD apps
   - Runs `argocd app get <app> --refresh`
   - Triggers sync with `--prune --retry-limit 3`

3. **Wait for Sync Completion**
   - Monitors sync status (Synced/OutOfSync)
   - Monitors health status (Healthy/Degraded)
   - Timeout: 5 minutes per app
   - Fails if any app becomes Degraded

**Example**:
```bash
# Push changes
git push origin main

# GitHub Actions automatically:
# 1. Detects helm/postgresql/ changed
# 2. Refreshes postgresql app
# 3. Syncs with --prune
# 4. Monitors until Healthy
```

**Required Secret**: `ARGOCD_TOKEN`
- Create in GitHub repo: Settings → Secrets → Actions
- Value: ArgoCD API token (see below)

### 3. ArgoCD Hooks

#### PreSync Hook: Restart StatefulSet

**Location**: `argocd/hooks/restart-statefulset.yaml`

**Purpose**: Ensures StatefulSets recreate pods when Helm chart changes

**Behavior**:
1. Runs before ArgoCD applies manifests
2. Finds StatefulSets managed by the app
3. Scales each StatefulSet to 0
4. Waits for pods to terminate (120s timeout)
5. ArgoCD then applies new manifests (pods recreate with new spec)

**Why Needed**:
- StatefulSets don't auto-recreate pods on spec change
- Manual `kubectl rollout restart` doesn't work reliably
- Scale to 0 + scale to desired forces pod recreation

**Example**:
```bash
# When postgresql Helm chart changes:
# 1. PreSync hook scales postgresql-0 to 0
# 2. Pod terminates
# 3. ArgoCD applies new StatefulSet spec
# 4. StatefulSet controller creates new postgresql-0 with new config
```

#### PostSync Hook: Verify StatefulSet

**Location**: `argocd/hooks/verify-statefulset.yaml`

**Purpose**: Validates StatefulSets are healthy and rootless after sync

**Behavior**:
1. Runs after ArgoCD applies manifests
2. Waits for StatefulSets to reach desired replica count (5min timeout)
3. Verifies pods are running as non-root UID
4. Fails sync if:
   - StatefulSet doesn't become ready
   - Pod is running as root (UID 0)
   - Timeout exceeded

**Security Validation**:
```bash
# For each StatefulSet pod:
kubectl exec <pod> -- id -u
# Expected: 1001 (Bitnami), 977 (SearXNG), anything except 0
```

**Example Output**:
```
✅ StatefulSet postgresql is ready
✅ Verified: Running as non-root UID 1001
```

### 4. Self-Healing

**Trigger**: Manual changes to cluster

**Example**:
```bash
# Developer manually edits deployment
kubectl edit deployment open-webui -n ai-services

# ArgoCD detects drift (within 3 minutes)
# Automatically reverts to Git state
# Deployment returns to Helm chart configuration
```

**Override Self-Heal** (for debugging):
```bash
# Temporarily disable for one app
argocd app set open-webui --self-heal=false

# Make manual changes
kubectl edit deployment open-webui -n ai-services

# Re-enable after debugging
argocd app set open-webui --self-heal=true
```

## Setup Instructions

### 1. Create ArgoCD API Token

```bash
# Login to ArgoCD
argocd login argocd.vectorweight.com

# Create token (expires in 1 year)
argocd account generate-token \
  --account github-actions \
  --expires-in 8760h

# Copy token output
```

### 2. Add GitHub Secret

1. Navigate to GitHub repo: https://github.com/tzervas/self-hosted-ai
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ARGOCD_TOKEN`
5. Value: Paste token from step 1
6. Click **Add secret**

### 3. Verify Automation

```bash
# Make a test change
echo "# Test automation" >> helm/postgresql/values.yaml
git add helm/postgresql/values.yaml
git commit -m "test: verify automation"
git push origin main

# Watch GitHub Actions
# https://github.com/tzervas/self-hosted-ai/actions

# Watch ArgoCD sync
kubectl get applications -n argocd -w

# Verify pod recreation
kubectl get pods -n ai-services -w
```

## Workflow Examples

### Example 1: Update PostgreSQL Resource Limits

```bash
# 1. Edit Helm chart
vim helm/postgresql/values.yaml
# Change resources.limits.memory: 4Gi

# 2. Commit and push
git add helm/postgresql/values.yaml
git commit -m "feat(postgresql): increase memory limit to 4Gi"
git push origin main

# 3. Automation happens:
# GitHub Actions:
#   ✅ Detected helm/postgresql/ change
#   ✅ Refreshed postgresql app
#   ✅ Triggered sync
#   ✅ Monitoring sync...

# ArgoCD PreSync Hook:
#   ✅ Scaled postgresql to 0 replicas
#   ✅ Waited for pod termination

# ArgoCD Sync:
#   ✅ Applied new StatefulSet spec (4Gi memory)

# ArgoCD PostSync Hook:
#   ✅ Waited for postgresql-0 to be ready
#   ✅ Verified running as UID 1001

# GitHub Actions:
#   ✅ postgresql: Synced and Healthy
#   ✅ Workflow completed successfully

# Total time: ~2-3 minutes (fully automated)
```

### Example 2: Update Multiple Services

```bash
# 1. Edit multiple Helm charts
vim helm/open-webui/values.yaml   # Change image tag
vim helm/searxng/values.yaml      # Change resource limits
vim helm/n8n/values.yaml          # Add environment variable

# 2. Commit all changes
git add helm/
git commit -m "feat: update open-webui, searxng, and n8n configurations"
git push origin main

# 3. Automation (parallel):
# GitHub Actions triggers:
#   - open-webui sync
#   - searxng sync
#   - n8n sync

# All three sync in parallel, each with PreSync/PostSync hooks
# Total time: ~2-3 minutes (vs 6-9 minutes sequential)
```

### Example 3: Rollback Failed Deployment

```bash
# Bad change causes postgresql to crash
git push origin main

# GitHub Actions detects Degraded health
# ❌ postgresql: Sync failed, Health=Degraded
# Workflow exits with error

# Manual rollback:
git revert HEAD
git push origin main

# Automation re-deploys previous working config
# ✅ postgresql: Synced and Healthy
```

## Monitoring

### ArgoCD UI
- URL: https://argocd.vectorweight.com
- View sync status, health, events
- See hook execution logs

### GitHub Actions
- URL: https://github.com/tzervas/self-hosted-ai/actions
- View workflow runs
- Check sync monitoring output

### Kubectl
```bash
# Watch applications
kubectl get applications -n argocd -w

# Watch specific app
kubectl get application postgresql -n argocd -w

# View sync logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller -f

# Check hook jobs
kubectl get jobs -n ai-services
kubectl logs job/restart-statefulset-hook -n ai-services
kubectl logs job/verify-statefulset-hook -n ai-services
```

## Troubleshooting

### GitHub Actions Fails: "argocd: command not found"

**Issue**: ArgoCD CLI not installed in GitHub runner

**Fix**: Workflow installs it automatically, check install step logs

### GitHub Actions Fails: "unauthorized"

**Issue**: `ARGOCD_TOKEN` secret missing or expired

**Fix**:
```bash
# Generate new token
argocd account generate-token --account github-actions --expires-in 8760h

# Update GitHub secret
# Settings → Secrets → Actions → ARGOCD_TOKEN → Update
```

### PreSync Hook Fails: "StatefulSet not found"

**Issue**: Hook runs on Deployment (not StatefulSet)

**Fix**: This is expected. Hook exits gracefully if no StatefulSets found.

### PostSync Hook Timeout

**Issue**: StatefulSet takes >5 minutes to become ready

**Fix**:
```yaml
# Increase timeout in argocd/hooks/verify-statefulset.yaml
MAX_WAIT=600  # 10 minutes
```

### Self-Heal Reverts Manual Changes Too Quickly

**Issue**: Can't debug with manual kubectl edits

**Fix**:
```bash
# Temporarily disable self-heal
argocd app set <app-name> --self-heal=false

# Make changes
kubectl edit ...

# Re-enable when done
argocd app set <app-name> --self-heal=true
```

### Sync Loop (Constantly Out of Sync)

**Issue**: Helm chart generates different output each sync

**Fix**: Check for:
- Timestamps in manifests
- Random values
- Conditional logic based on cluster state

Use `--dry-run` to compare:
```bash
helm template helm/postgresql/ > /tmp/template.yaml
kubectl diff -f /tmp/template.yaml
```

## Best Practices

### 1. Always Use Git

❌ **Don't**:
```bash
kubectl edit deployment open-webui -n ai-services
```

✅ **Do**:
```bash
vim helm/open-webui/values.yaml
git commit -m "feat: update open-webui config"
git push
```

### 2. Test Helm Charts Locally

Before pushing:
```bash
# Render template
helm template helm/postgresql/ > /tmp/postgresql.yaml

# Validate
kubectl apply --dry-run=client -f /tmp/postgresql.yaml

# Check for differences
kubectl diff -f /tmp/postgresql.yaml
```

### 3. Monitor GitHub Actions

- Always check workflow run after push
- Verify all apps sync successfully
- Investigate failures immediately

### 4. Use Conventional Commits

Helps trace automation triggers:
```bash
feat(postgresql): increase memory limit
fix(redis): correct securityContext UID
docs(automation): update guide
```

### 5. Leverage Sync Waves

For ordered deployments:
```yaml
# argocd/applications/postgresql.yaml
annotations:
  argocd.argoproj.io/sync-wave: "0"  # Deploy first

# argocd/applications/litellm.yaml
annotations:
  argocd.argoproj.io/sync-wave: "5"  # Deploy after databases
```

## Security Considerations

### 1. ArgoCD Token Scope

- Use dedicated `github-actions` account (not admin)
- Limit to necessary permissions: `apiKey, applications:sync`
- Rotate annually

### 2. GitHub Secrets

- Never log `ARGOCD_TOKEN` in workflow output
- Use `env:` to pass to steps (not command-line args)
- Enable secret scanning in GitHub repo

### 3. Hook Permissions

Hooks use `argocd-application-controller` ServiceAccount:
```bash
# Verify permissions
kubectl auth can-i scale statefulsets \
  --as=system:serviceaccount:argocd:argocd-application-controller \
  -n ai-services
```

### 4. Prevent Manual Changes

Kyverno policy to block direct kubectl edits:
```yaml
# policies/kyverno/security/enforce-gitops.yaml
# Deny manual changes to ArgoCD-managed resources
```

## Future Enhancements

### Planned

- [ ] Slack/Discord notifications on sync failures
- [ ] Automatic rollback on PostSync hook failure
- [ ] Prometheus metrics for sync duration
- [ ] Canary deployments with progressive delivery
- [ ] Multi-cluster sync (homelab → akula-prime)

### Considered

- [ ] Blue/green deployments for zero-downtime updates
- [ ] Automatic backups before sync
- [ ] Integration tests in PostSync hook
- [ ] Cost estimation for resource changes

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design and ADRs
- [OPERATIONS.md](../OPERATIONS.md) - Day-to-day operations
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment procedures
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)

---

**Last Updated**: 2026-02-08
**Automation Status**: ✅ Fully Operational
