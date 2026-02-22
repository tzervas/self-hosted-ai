---
title: Operations Runbook
description: Daily operations, service management, and maintenance procedures
---

# Operations Runbook

## Quick Commands

### Cluster Status

```bash
# Overall cluster health
kubectl get nodes
kubectl get pods -A | grep -v Running

# ArgoCD sync status
argocd app list

# Certificate status
kubectl get certificates -n cert-manager
```

### Service Operations

```bash
# Restart a deployment
kubectl rollout restart deployment/<name> -n <namespace>

# View logs
kubectl logs -f deployment/<name> -n <namespace>

# Execute into pod
kubectl exec -it deployment/<name> -n <namespace> -- /bin/sh

# Port forward for local access
kubectl port-forward -n self-hosted-ai svc/postgresql 5432:5432
kubectl port-forward -n monitoring svc/grafana 3000:80
```

### Model Management

```bash
# List models across all locations
uv run scripts/sync_models.py list

# Pull a model
curl -X POST http://192.168.1.99:11434/api/pull \
  -d '{"name":"qwen2.5-coder:14b"}'

# Compare models between locations
uv run scripts/sync_models.py diff
```

### Secrets Management

```bash
# Generate new credentials
uv run scripts/secrets_manager.py generate

# Rotate specific service
uv run scripts/secrets_manager.py rotate --service litellm

# Export credentials document
uv run scripts/secrets_manager.py export -o ADMIN_CREDENTIALS.local.md
```

### Backup & Restore

```bash
# Full backup
uv run scripts/backup.py create --all

# List backups
uv run scripts/backup.py list

# Restore from backup
uv run scripts/backup.py restore 20260115_120000

# Cleanup old backups (keep last 5)
uv run scripts/backup.py cleanup --keep 5
```

## GitHub Actions Runners (ARC)

| Runner Set | Labels | Min/Max | Notes |
|------------|--------|---------|-------|
| `self-hosted-ai-amd64` | `self-hosted, linux, amd64` | 0/4 | Scale-to-zero |
| `self-hosted-ai-gpu` | `self-hosted, linux, gpu` | 0/2 | GPU over LAN |
| `self-hosted-ai-arm64` | `self-hosted, linux, arm64` | 0/2 | QEMU emulation |

```bash
# Check runner pods
kubectl get pods -n arc-runners

# View runner logs
kubectl logs -n arc-runners -l app.kubernetes.io/component=runner -f
```

## API Reference

### LiteLLM (OpenAI-Compatible)

```bash
# Chat completion
curl -X POST https://llm.vectorweight.com/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:14b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# List models
curl https://llm.vectorweight.com/v1/models \
  -H "Authorization: Bearer $LITELLM_KEY"
```

## Maintenance Schedule

### Daily

- [ ] Check ArgoCD sync status
- [ ] Review Grafana alerts
- [ ] Verify backup completed

### Weekly

- [ ] Review resource utilization trends
- [ ] Check for pending security updates
- [ ] Review and cleanup old logs

### Monthly

- [ ] Rotate credentials
- [ ] Review and update models
- [ ] Test backup restore procedure
- [ ] Update dependencies (Helm charts, images)
