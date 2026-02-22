---
title: Deployment Guide
description: Complete deployment procedures for the platform
---

# Deployment Guide

## Prerequisites

- k3s cluster (v1.28+)
- `kubectl` configured with cluster access
- Helm 3.x installed
- ArgoCD installed in the cluster
- Python 3.12+ with uv

## Fresh Deployment

### 1. Bootstrap ArgoCD

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
```

### 2. Deploy App-of-Apps

```bash
# Apply all ArgoCD applications
kubectl apply -f argocd/applications/
```

ArgoCD will deploy services in [sync wave order](sync-waves.md), starting from infrastructure (Wave -2) through to user-facing applications (Wave 6-7).

### 3. Generate Secrets

```bash
cd scripts
uv sync
uv run scripts/secrets_manager.py generate
```

### 4. Validate

```bash
# Run validation suite
uv run scripts/validate_cluster.py

# Or use task runner
task validate:all
```

## Service Configuration

Each service is defined as:

1. **Helm chart** in `helm/<service>/` - templates and default values
2. **ArgoCD Application** in `argocd/applications/<service>.yaml` - sync policy and overrides
3. **SealedSecret** in `argocd/sealed-secrets/` (if credentials needed)

To modify a service:

```bash
# Edit values
vim helm/<service>/values.yaml

# Commit to dev branch
git add helm/<service>/values.yaml
git commit -m "fix(<service>): update resource limits"
git push origin dev

# ArgoCD auto-syncs (or manual sync)
argocd app sync <service>
```

## Adding a New Service

1. Create Helm chart in `helm/<service-name>/`
2. Create ArgoCD application in `argocd/applications/<service-name>.yaml`
3. Set appropriate [sync wave](sync-waves.md)
4. Create SealedSecret if credentials are needed
5. Commit to `dev` branch
6. ArgoCD deploys automatically
