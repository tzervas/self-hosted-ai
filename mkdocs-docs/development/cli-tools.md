---
title: CLI Tools
description: Command-line tools for platform management
---

# CLI Tools

All operations use Python scripts managed with uv:

## shai (Main CLI)

```bash
shai --help
```

## shai-bootstrap

```bash
# Full bootstrap
shai-bootstrap all

# Configure services via APIs
shai-bootstrap services

# Pull AI models
shai-bootstrap models
```

## shai-validate

```bash
# All checks
shai-validate all

# Individual checks
shai-validate dns            # DNS resolution
shai-validate tls            # TLS certificates
shai-validate services       # API health
shai-validate kubernetes     # K8s resources
```

## shai-secrets

```bash
# Generate all credentials
shai-secrets generate

# Export to markdown
shai-secrets export --format markdown

# Rotate all secrets
shai-secrets rotate

# Display credentials
shai-secrets show
```

## kubectl Common Commands

```bash
# Cluster status
kubectl get nodes
kubectl get pods -A | grep -v Running

# Service logs
kubectl logs -f deployment/<name> -n <namespace>

# Execute into pod
kubectl exec -it deployment/<name> -n <namespace> -- /bin/sh

# Port forward
kubectl port-forward -n self-hosted-ai svc/postgresql 5432:5432
```

## argocd Commands

```bash
# List all applications
argocd app list

# Sync a specific app
argocd app sync <app-name>

# Get app details
argocd app get <app-name>

# Diff live vs desired
argocd app diff <app-name>
```
