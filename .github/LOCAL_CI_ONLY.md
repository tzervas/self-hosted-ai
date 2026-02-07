# Local CI Only Policy

This project uses **local validation only** to reduce remote CI costs and GitHub Actions usage.

## Validation Commands

Run these locally before committing:

### Helm Charts
```bash
for chart in helm/*/; do
  if [[ -f "${chart}Chart.yaml" ]]; then
    helm lint "$chart"
  fi
done
```

### Kubernetes Manifests
```bash
# ArgoCD applications
kubectl apply --dry-run=client -f argocd/applications/

# Kyverno policies
kubectl apply --dry-run=client -f policies/kyverno/ -R
```

### Python Tests
```bash
cd scripts
uv sync
uv run pytest tests/
```

### Security Scans
```bash
# Trivy config scan
trivy config . --severity HIGH,CRITICAL

# Secret detection
gitleaks detect --no-git
```

## Pre-Commit Hooks

The project uses pre-commit hooks for automatic local validation:
```bash
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit run --all-files
```

## Why Local CI Only?

1. **Cost Reduction**: No GitHub Actions minutes consumed
2. **Faster Feedback**: Immediate validation without waiting for remote runners
3. **Privacy**: Sensitive infrastructure configs stay local
4. **GitOps Workflow**: ArgoCD handles deployment validation in-cluster

## ArgoCD Validation

After pushing to `dev` or `main`, ArgoCD performs additional validation:
- Helm chart rendering
- Kubernetes API validation
- Policy enforcement (Kyverno)
- Health checks

Monitor deployments:
```bash
kubectl get applications -n argocd
argocd app sync <app-name>
```
