# Quick Start: Token Configuration

This guide helps you complete the v0.3.0 deployment by configuring required authentication tokens.

## 🔑 HuggingFace Token (Required for Uncensored Models)

### 1. Get Your HuggingFace Token

1. Visit https://huggingface.co/settings/tokens
2. Create a new token with "Read" permissions
3. Copy the token (starts with `hf_...`)

### 2. Apply Token to Cluster

```bash
# Replace the placeholder secret
kubectl create secret generic huggingface-token \
  -n ai-services \
  --from-literal=HF_TOKEN=hf_YOUR_ACTUAL_TOKEN_HERE \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify secret was created
kubectl get secret huggingface-token -n ai-services
```

### 3. Test Model Download

```bash
cd /home/kang/self-hosted-ai

# Download your first uncensored model (smaller one for testing)
python scripts/sync_models.py download-hf wan2.5-7b-uncensored

# Sync to GPU worker
python scripts/sync_models.py sync-hf wan2.5-7b-uncensored

# Optional: Quantize larger model to save VRAM
python scripts/sync_models.py quantize wan2.5-14b-uncensored Q4_K_M
```

### 4. Available Uncensored Models

Once HF token is configured, you can download:

**Text Generation**:
- `wan2.5-14b-uncensored` (28GB → 8GB with Q4_K_M quantization)
- `wan2.5-7b-uncensored` (14GB, lighter weight)
- `dolphin-mistral-7b` (14GB, alternative option)

**Voice Generation**:
- `xtts-v2` (1.8GB, multilingual TTS, voice cloning)
- `bark` (5GB, expressive TTS, music generation)

**Sound Effects**:
- `audioldm2-large` (3.5GB, text-to-audio)
- `audiogen-medium` (1.5GB, environmental sounds)

**Music**:
- `musicgen-large` (3.3GB, text-to-music)

---

## 🤖 GitHub App (Required for ARC Runners)

### 1. Create GitHub App (if you don't have one)

1. Go to https://github.com/settings/apps/new
2. Fill in:
   - **GitHub App name**: `self-hosted-arc-runners` (or your choice)
   - **Homepage URL**: `https://github.com/tzervas`
   - **Webhook**: Uncheck "Active"
   - **Permissions**:
     - Repository permissions:
       - Actions: Read & Write
       - Administration: Read & Write
       - Checks: Read & Write
       - Contents: Read
       - Metadata: Read
       - Pull requests: Read & Write
     - Organization permissions (if using org):
       - Self-hosted runners: Read & Write
3. Click "Create GitHub App"
4. Note down the **App ID**
5. Generate and download a **Private Key** (you'll get a `.pem` file)

### 2. Install App to Your Account/Org

1. On the app page, click "Install App"
2. Select your account (`tzervas`) and/or organization (`Vector-Weight-Technologies`)
3. Choose:
   - "All repositories" (recommended)
   - OR select specific repositories
4. Complete installation
5. Note down the **Installation ID** from the URL (e.g., `https://github.com/settings/installations/12345678` → ID is `12345678`)

### 3. Apply GitHub App Secret to Cluster

```bash
# Navigate to where you saved the private key
cd ~/path/to/github/app

# Create secret for ARC runners
kubectl create secret generic github-app-secret \
  -n arc-runners \
  --from-literal=github_app_id=YOUR_APP_ID \
  --from-literal=github_app_installation_id=YOUR_INSTALLATION_ID \
  --from-file=github_app_private_key=path/to/your-app.private-key.pem

# Verify secret was created
kubectl get secret github-app-secret -n arc-runners
```

### 4. Verify Runner Deployment

```bash
# ArgoCD will auto-sync within ~3 minutes
# Check runner scale sets
kubectl get ephemeralrunnersets -n arc-runners

# Expected output (after sync):
# NAME                DESIRED   CURRENT   READY   AGE
# arc-runners-amd64   0         0         0       2m
# arc-runners-gpu     0         0         0       2m
# arc-runners-arm64   0         0         0       2m
# arc-runners-org     0         0         0       2m

# All should show 0/0 (scale-to-zero when no jobs)
```

### 5. Test Runner Auto-Scaling

Create a test workflow in any repository:

```yaml
# .github/workflows/test-arc.yml
name: Test ARC Runner
on: [push]
jobs:
  test:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: echo "Running on self-hosted ARC runner!"
      - run: uname -a
```

Push this workflow and watch:
```bash
# Monitor runner pod creation
watch kubectl get pods -n arc-runners

# You should see ephemeral runner pods spin up within 15 seconds
```

---

## 🔐 Optional: Sealed Secrets (Production)

For production deployments, convert regular secrets to SealedSecrets:

```bash
# Install kubeseal if not already installed
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar xfz kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# Seal HuggingFace token
kubectl create secret generic huggingface-token \
  -n ai-services \
  --from-literal=HF_TOKEN=hf_YOUR_ACTUAL_TOKEN \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > argocd/secrets/huggingface-token-sealed.yaml

# Seal GitHub App secret
kubectl create secret generic github-app-secret \
  -n arc-runners \
  --from-literal=github_app_id=YOUR_APP_ID \
  --from-literal=github_app_installation_id=YOUR_INSTALLATION_ID \
  --from-file=github_app_private_key=path/to/key.pem \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > argocd/secrets/github-app-sealed.yaml

# Apply sealed secrets
kubectl apply -f argocd/secrets/huggingface-token-sealed.yaml
kubectl apply -f argocd/secrets/github-app-sealed.yaml
```

---

## 📋 Verification Checklist

- [ ] HuggingFace token applied and verified
- [ ] Test model downloaded successfully
- [ ] GitHub App created and installed
- [ ] GitHub App secret applied to cluster
- [ ] ARC runner scale sets deployed (4 total)
- [ ] Test workflow triggered runner pod creation
- [ ] Runner scaled to zero after job completion

---

## 🆘 Troubleshooting

### HuggingFace Token Issues

**Error: "Repository not found"**
- Token needs "Read" permission
- Some models require accepting terms on HuggingFace website

**Error: "Authentication failed"**
- Check token starts with `hf_`
- Verify secret was created in correct namespace (`ai-services`)

### GitHub App Issues

**Error: "No runners available"**
- Check App has correct permissions (Actions: Read & Write)
- Verify Installation ID is correct
- Ensure App is installed to the repository/org

**Runners not scaling down**
- Normal behavior: 5-minute grace period after job completion
- Check `kubectl describe ephemeralrunnerset` for scale-down policy

### General Debug Commands

```bash
# Check all secrets
kubectl get secrets -A | grep -E "huggingface|github-app"

# View HPA status
kubectl get hpa -n self-hosted-ai

# View resource quotas
kubectl get resourcequota -A

# Check ArgoCD app sync status
kubectl get applications -n argocd | grep -E "arc-|litellm|open-webui"

# Monitor cluster resources
kubectl top nodes
kubectl top pods -A
```

---

**Need Help?** Check the main [OPERATIONS.md](../OPERATIONS.md) for detailed troubleshooting steps.
