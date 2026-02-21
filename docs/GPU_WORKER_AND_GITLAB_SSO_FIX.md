# GPU Worker and GitLab SSO Fixes

**Date**: 2026-02-21
**Status**: ✅ Ready for Deployment

---

## Issues Identified

### 1. GPU Worker (ollama-gpu) Not Available

**Symptoms**:
- `kubectl get pods -n gpu-workloads` shows ollama-gpu in "Completed" state
- Deployment shows "1 desired | 0 updated | 0 total | 0 available | 1 unavailable"
- GPU inference not available to cluster applications

**Root Cause**:
- ollama-gpu pod exited cleanly (exit code 0) instead of running continuously
- Deployment won't create new pod because it thinks the completed pod is still "there"
- Classic Kubernetes issue: pods that exit successfully don't trigger replacement

**Impact**:
- No GPU inference available
- Applications fall back to CPU-only Ollama
- GPU resources (RTX 5080 16GB) sitting idle

### 2. GitLab SSO Not Working

**Symptoms**:
- GitLab shows username/password login form
- No auto-redirect to Keycloak
- "Login with Keycloak" button not visible

**Root Cause**:
- `gitlab-oidc-provider` secret EXISTS and is CORRECT (verified)
- Secret is properly mounted in GitLab webservice pod
- GitLab OmniAuth configuration is correct in values.yaml
- **But**: GitLab webservice started BEFORE the secret was updated (needs restart)

**Impact**:
- Users can't use SSO to access GitLab
- Must use local credentials instead

### 3. Documentation Outdated

**Issue**:
- OPERATIONS.md says akula-prime is "standalone workstation, NOT a Kubernetes node"
- Reality: `kubectl get nodes` shows akula-prime IS the k3s **control-plane**
- Documentation describes Podman containers, but actually using containerd/K8s

---

## Changes Made

### Helm Chart Updates

**File**: `helm/gpu-worker/templates/ollama-gpu-deployment.yaml`

**Change**: Updated volume mount to use shared NFS storage instead of local PVC

```yaml
# OLD:
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: {{ include "self-hosted-ai-gpu-worker.fullname" . }}-ollama-gpu

# NEW:
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: shared-models-nfs  # Use NFS storage from homelab (192.168.1.170)
```

**Rationale**:
- Models stored centrally on homelab (192.168.1.170) NFS share
- Shared across CPU and GPU Ollama instances
- Easier management: download models once, use everywhere
- 500Gi NFS volume vs fragmented local storage

### Documentation Updates

**File**: `OPERATIONS.md`

**Change**: Updated GPU Worker section to reflect actual k3s cluster topology

**Old description**:
```
### GPU Worker (192.168.1.99 - akula-prime)

This is a **standalone workstation**, NOT a Kubernetes node.
Container Runtime: Rootless Podman
```

**New description**:
```
### GPU Worker (192.168.1.99 - akula-prime)

This is the **k3s control-plane node** with GPU resources (RTX 5080 16GB).

Hardware: 4x NVIDIA GPUs available
Role: Kubernetes control-plane + GPU workload execution
Container Runtime: containerd 2.1.5-k3s1
```

**Includes**:
- Correct kubectl commands for managing GPU workloads
- Model storage architecture (NFS)
- GPU operator status checks

### Automation Script

**File**: `scripts/fix-gpu-worker-and-gitlab-sso.sh`

**Purpose**: Automated fix script for both issues

**What it does**:
1. Deletes completed ollama-gpu pod to trigger new pod creation
2. Syncs GPU worker ArgoCD application (pulls updated Helm chart)
3. Restarts GitLab webservice deployment to load OIDC secret
4. Verifies both fixes
5. Tests connectivity

---

## Deployment Instructions

### Step 1: Commit and Push Changes

```bash
cd /home/kang/Documents/projects/github/homelab-cluster/self-hosted-ai

# Make script executable
chmod +x scripts/fix-gpu-worker-and-gitlab-sso.sh

# Stage changes
git add -A

# Commit
git commit -m "fix(gpu-worker): configure shared NFS storage and fix deployment

- Update ollama-gpu to use shared-models-nfs PVC from homelab
- Fix documentation: akula-prime is k3s control-plane, not standalone
- Add automated fix script for GPU worker and GitLab SSO
- Update OPERATIONS.md with correct cluster topology

Fixes:
- ollama-gpu stuck in Completed state (deployment 0/1 available)
- Models now centralized on homelab NFS (500Gi)
- GitLab SSO requires webservice restart to load secret

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to dev
git push origin dev
```

### Step 2: Run Fix Script

```bash
# Run the automated fix script
./scripts/fix-gpu-worker-and-gitlab-sso.sh
```

**What it will do**:
- ✅ Delete completed ollama-gpu pod
- ✅ Wait for new pod to be created
- ✅ Sync GPU worker Helm chart via ArgoCD
- ✅ Restart GitLab webservice deployment
- ✅ Verify both services are healthy
- ✅ Test API connectivity

**Expected Output**:
```
🔧 Fixing GPU Worker and GitLab SSO Issues
==========================================

Step 1: Fixing ollama-gpu deployment
-------------------------------------
  Current pod: ollama-gpu-c777c7887-slxjw (status: Succeeded)
  Deleting completed pod to trigger new pod creation...
✓ Completed pod deleted
  Waiting for new pod to be created (30s)...
  New pod: ollama-gpu-78b9f4d6c-xjk9m (status: Running)
✓ New pod created successfully

Step 2: Syncing GPU worker configuration
-----------------------------------------
  Syncing self-hosted-ai-gpu-worker ArgoCD application...
✓ GPU worker configuration synced

Step 3: Restarting GitLab for SSO
----------------------------------
  Restarting GitLab webservice deployment...
✓ GitLab webservice restart initiated
  Waiting for rollout to complete (60s timeout)...
✓ GitLab webservice restarted successfully

Step 4: Verification
--------------------
  Checking ollama-gpu deployment status...
✓ ollama-gpu deployment: 1/1 replicas available
  Checking GitLab webservice status...
✓ GitLab webservice: 2/2 replicas available

Step 5: Testing services
------------------------
  Testing ollama-gpu service...
✓ ollama-gpu API responding
  Testing GitLab webservice...
✓ GitLab health endpoint responding

==========================================
Summary
==========================================

✓ GPU Worker Fix: ollama-gpu pod recreated, now using shared NFS storage
✓ GitLab SSO Fix: Webservice restarted to load OIDC provider secret

✓ Script completed!
```

### Step 3: Verify Fixes

#### Verify ollama-gpu

```bash
# Check pod is running
kubectl get pods -n gpu-workloads | grep ollama-gpu
# Expected: Running status

# Check deployment
kubectl get deployment -n gpu-workloads ollama-gpu
# Expected: 1/1 READY

# Test API
kubectl run test-ollama --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -s http://ollama-gpu.gpu-workloads:11434/api/version
# Expected: {"version":"0.16.2"}

# Check model storage (should show NFS mount)
kubectl exec -n gpu-workloads deployment/ollama-gpu -- df -h /root/.ollama
# Expected: NFS mount from homelab (192.168.1.170)
```

#### Verify GitLab SSO

```bash
# Check GitLab pods
kubectl get pods -n gitlab | grep webservice
# Expected: All Running

# Open GitLab in browser
open https://git.vectorweight.com
```

**Expected behavior**:
1. Browser navigates to `https://git.vectorweight.com`
2. **Auto-redirects** to `https://auth.vectorweight.com/realms/vectorweight/...`
3. Keycloak login page appears
4. Enter credentials: `kang` / `banana12`
5. Redirects back to GitLab, logged in

**If still showing password form**:
```bash
# Check OmniAuth logs
kubectl logs -n gitlab deployment/gitlab-webservice-default -c webservice | grep -i omniauth

# Check secret is mounted
kubectl exec -n gitlab deployment/gitlab-webservice-default -c webservice -- \
  cat /etc/gitlab/gitlab-secrets/oidc/provider | head -5

# Force another restart
kubectl rollout restart deployment/gitlab-webservice-default -n gitlab
```

---

## Verification Checklist

- [ ] ollama-gpu pod is Running (not Completed)
- [ ] ollama-gpu deployment shows 1/1 READY
- [ ] ollama-gpu API responds to version check
- [ ] ollama-gpu uses NFS storage (check with `df -h /root/.ollama`)
- [ ] GitLab webservice pods are all Running
- [ ] GitLab auto-redirects to Keycloak (not password form)
- [ ] User `kang` can log in with `banana12`
- [ ] After login, GitLab shows user as authenticated

---

## Model Storage Architecture

**Before Fix**:
```
akula-prime (GPU node)
  └─ Local PVC: akula-prime-models (500Gi)
      └─ ollama-gpu models stored here

homelab (worker node)
  └─ Longhorn PVC: ollama-models (50Gi)
      └─ ollama (CPU) models stored here

❌ Problem: Models duplicated, separate management
```

**After Fix**:
```
homelab (worker node)
  └─ NFS PV: nfs-models-pv (500Gi)
      └─ Export: /data/models
          ├─ ollama (CPU) models
          └─ ollama-gpu (GPU) models

akula-prime (GPU node)
  └─ Mounts: shared-models-nfs PVC via NFS
      └─ Reads models from homelab

✅ Centralized: All models stored once, accessible from any node
```

**Benefits**:
- **Single source**: Download models once
- **Consistency**: CPU and GPU Ollama use same model files
- **Easier management**: `ollama pull` on either instance updates both
- **No duplication**: 500Gi shared vs 2x local storage

---

## Troubleshooting

### ollama-gpu Still Not Running

**Check pod logs**:
```bash
kubectl logs -n gpu-workloads deployment/ollama-gpu
```

**Common issues**:
- **GPU not available**: Check `kubectl describe node akula-prime | grep nvidia.com/gpu`
- **Image pull error**: Check image exists: `ollama/ollama:0.16.2`
- **Liveness probe failing**: API not responding on port 11434
- **NFS mount failing**: Check NFS server is accessible from akula-prime

**Manual restart**:
```bash
kubectl rollout restart deployment/ollama-gpu -n gpu-workloads
```

### GitLab Still Shows Password Login

**Check OmniAuth is enabled**:
```bash
kubectl exec -n gitlab deployment/gitlab-webservice-default -c webservice -- \
  grep -A 10 "omniauth:" /srv/gitlab/config/gitlab.yml
```

**Expected output**:
```yaml
omniauth:
  enabled: true
  allow_single_sign_on: ["openid_connect"]
  auto_sign_in_with_provider: "openid_connect"
  block_auto_created_users: false
```

**Check OIDC provider secret content**:
```bash
kubectl get secret gitlab-oidc-provider -n gitlab -o jsonpath='{.data.provider}' | base64 -d
```

**Expected**: Full OmniAuth provider JSON with Keycloak URLs

**Force complete rebuild**:
```bash
# Delete webservice pods to force complete restart
kubectl delete pods -n gitlab -l app=webservice

# Wait for new pods
kubectl get pods -n gitlab -w | grep webservice
```

### Models Not Showing on GPU Worker

**Check NFS mount**:
```bash
kubectl exec -n gpu-workloads deployment/ollama-gpu -- mount | grep nfs
```

**Expected**: NFS mount from homelab

**Check model directory**:
```bash
kubectl exec -n gpu-workloads deployment/ollama-gpu -- ls -lh /root/.ollama/models
```

**Pull a test model**:
```bash
kubectl exec -n gpu-workloads deployment/ollama-gpu -- ollama pull phi4:3.8b
```

**Verify from homelab**:
```bash
# SSH to homelab
ssh homelab

# Check NFS export
ls -lh /data/models/models/manifests/registry.ollama.ai/library/
```

---

## Rollback Procedure

If issues occur:

### Revert Helm Chart

```bash
cd /home/kang/Documents/projects/github/homelab-cluster/self-hosted-ai

# Revert the commit
git revert HEAD

# Push revert
git push origin dev

# Sync ArgoCD
argocd app sync self-hosted-ai-gpu-worker
```

### Restore Local Storage

```yaml
# helm/gpu-worker/templates/ollama-gpu-deployment.yaml
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: {{ include "self-hosted-ai-gpu-worker.fullname" . }}-ollama-gpu
```

---

## Future Improvements

1. **Model Sync Job**: Automated model synchronization from CPU to GPU Ollama
2. **Health Monitoring**: Alert if ollama-gpu pod exits/completes
3. **Auto-restart**: CronJob to check and restart failed GPU workloads
4. **Storage Metrics**: Monitor NFS usage and model inventory
5. **GPU Time-Slicing**: Enable multiple workloads to share GPU (already configured with nvidia-device-plugin)

---

## Files Changed

```
Modified:
  helm/gpu-worker/templates/ollama-gpu-deployment.yaml
  OPERATIONS.md

Created:
  scripts/fix-gpu-worker-and-gitlab-sso.sh
  docs/GPU_WORKER_AND_GITLAB_SSO_FIX.md (this file)
```

---

**Fix Status**: ✅ Ready for Deployment
**Estimated Fix Time**: 5-10 minutes
**Risk Level**: Low (changes are reversible, script includes safety checks)
