# Self-Hosted AI Platform - Operations Manual

Quick reference for daily operations, troubleshooting, and service access.

---

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| **Open WebUI** | https://ai.vectorweight.com | AI chat interface |
| **LiteLLM** | https://llm.vectorweight.com | OpenAI-compatible API proxy |
| **ArgoCD** | https://argocd.vectorweight.com | GitOps dashboard |
| **n8n** | https://n8n.vectorweight.com | Workflow automation |
| **Grafana** | https://grafana.vectorweight.com | Monitoring dashboards |
| **Prometheus** | https://prometheus.vectorweight.com | Metrics |
| **SearXNG** | https://search.vectorweight.com | Privacy search |
| **GitLab** | https://git.vectorweight.com | Source control |
| **Traefik** | https://traefik.vectorweight.com | Ingress dashboard |
| **Longhorn** | https://longhorn.vectorweight.com | Storage UI |

### Internal Services (ClusterIP)

| Service | Namespace | Port | Notes |
|---------|-----------|------|-------|
| PostgreSQL | self-hosted-ai | 5432 | LiteLLM database |
| Redis | self-hosted-ai | 6379 | Cache/queues |
| Ollama (CPU) | self-hosted-ai | 11434 | CPU inference |
| Ollama (GPU) | gpu-workloads | 11434 | GPU inference |
| Alertmanager | monitoring | 9093 | Alert routing |

### GPU Worker (192.168.1.99 - akula-prime)

This is a **standalone workstation**, NOT a Kubernetes node. Services are accessed over LAN via HTTP.

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Ollama | 11434 | http://192.168.1.99:11434 | GPU inference (RTX 5080) |
| ComfyUI | 8188 | http://192.168.1.99:8188 | Image generation |
| Whisper | 9000 | http://192.168.1.99:9000 | Speech-to-text |

```bash
# Test GPU worker connectivity from homelab
curl http://192.168.1.99:11434/api/tags

# Check GPU status (SSH to akula-prime)
ssh akula-prime nvidia-smi
```

---

## GitHub Actions Runners (ARC)

Self-hosted runners managed by Actions Runner Controller, all running on homelab k3s.

| Runner Set | Labels | Min/Max | Notes |
|------------|--------|---------|-------|
| `self-hosted-ai-amd64` | `self-hosted, linux, amd64` | 0/4 | Scale-to-zero, general builds |
| `self-hosted-ai-gpu` | `self-hosted, linux, gpu` | 0/2 | Access GPU over LAN |
| `self-hosted-ai-arm64` | `self-hosted, linux, arm64` | 0/2 | QEMU emulation on amd64 |

### Runner Operations

```bash
# Check runner pods
kubectl get pods -n arc-runners

# View runner logs
kubectl logs -n arc-runners -l app.kubernetes.io/component=runner -f

# Scale runners manually (if needed)
kubectl scale runnerdeployment -n arc-runners <name> --replicas=N
```

---

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
# List models on GPU worker
curl http://192.168.1.99:11434/api/tags | jq '.models[].name'

# Pull a model
curl -X POST http://192.168.1.99:11434/api/pull -d '{"name":"qwen2.5-coder:14b"}'

# Sync models from manifest
uv run shai-bootstrap models
```

### Secrets Management

```bash
# Generate new credentials
uv run shai-secrets generate --apply

# Rotate specific service
uv run shai-secrets rotate --service litellm --apply

# Export credentials document
uv run shai-secrets export -o ADMIN_CREDENTIALS.local.md
```

### Backup & Restore

```bash
# Full backup
uv run shai-backup create

# List backups
uv run shai-backup list

# Restore from backup
uv run shai-backup restore --date 2026-01-15
```

---

## Troubleshooting

### Common Issues

#### Pod CrashLoopBackOff

```bash
# Check logs for errors
kubectl logs deployment/<name> -n <namespace> --previous

# Check events
kubectl describe pod -l app=<name> -n <namespace>

# Common fixes:
# - Memory limits: Increase in values.yaml
# - Config errors: Check ConfigMaps/Secrets
# - Dependency: Check dependent services are running
```

#### Certificate Issues

```bash
# Check certificate status
kubectl get certificates -n cert-manager -o wide

# Check challenges
kubectl get challenges -n cert-manager

# Force certificate renewal
kubectl delete certificate <name> -n cert-manager
# ArgoCD will recreate it
```

#### DNS Resolution

```bash
# Test from inside cluster
kubectl run -it --rm debug --image=busybox -- nslookup ai.vectorweight.com

# Check CoreDNS
kubectl logs -n kube-system -l k8s-app=kube-dns

# Restart CoreDNS
kubectl rollout restart deployment/coredns -n kube-system
```

#### Ingress/Traefik

```bash
# Check Traefik logs
kubectl logs -n traefik -l app.kubernetes.io/name=traefik

# Verify IngressRoutes
kubectl get ingressroute -A

# Test connectivity
curl -k https://ai.vectorweight.com/health
```

### Performance Issues

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods -A --sort-by=memory

# Check Ollama model memory
curl http://192.168.1.99:11434/api/ps | jq

# Unload unused models
curl -X POST http://192.168.1.99:11434/api/generate \
  -d '{"model":"unused-model","keep_alive":0}'
```

#### Slow Inference

```bash
# Check GPU utilization
nvidia-smi  # On GPU worker

# Check LiteLLM queue
curl -s https://llm.vectorweight.com/queue/status

# Check rate limits
kubectl logs deployment/litellm -n self-hosted-ai | grep rate
```

---

## Maintenance Tasks

### Daily

- [ ] Check ArgoCD sync status
- [ ] Review Grafana alerts
- [ ] Verify backup completed

### Weekly

- [ ] Review resource utilization trends
- [ ] Check for pending security updates
- [ ] Review and cleanup old logs

### Monthly

- [ ] Rotate credentials (`uv run shai-secrets rotate --all`)
- [ ] Review and update models
- [ ] Test backup restore procedure
- [ ] Update dependencies (Helm charts, images)

---

## Emergency Procedures

### Full Cluster Recovery

```bash
# 1. Verify node connectivity
kubectl get nodes

# 2. Check ArgoCD
kubectl get pods -n argocd
argocd app sync --prune root

# 3. Verify critical services
kubectl get pods -n self-hosted-ai
kubectl get pods -n monitoring

# 4. Test endpoints
curl -k https://ai.vectorweight.com/health
```

### Database Recovery

```bash
# 1. Stop dependent services
kubectl scale deployment litellm --replicas=0 -n self-hosted-ai

# 2. Restore from backup
uv run shai-backup restore --target postgresql --date <date>

# 3. Restart services
kubectl scale deployment litellm --replicas=1 -n self-hosted-ai
```

### Secret Recovery

```bash
# If SealedSecrets key is lost, you must regenerate all secrets
# and update all applications

# 1. Backup current secrets (if accessible)
kubectl get secrets -A -o yaml > secrets-backup.yaml

# 2. Reinstall SealedSecrets
kubectl delete -n kube-system deploy sealed-secrets-controller
argocd app sync sealed-secrets

# 3. Regenerate and apply secrets
uv run shai-secrets generate --apply

# 4. Restart all deployments
kubectl rollout restart deployment -A
```

---

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

### Open WebUI

```bash
# Health check
curl https://ai.vectorweight.com/health

# API (requires auth token from login)
curl https://ai.vectorweight.com/api/models \
  -H "Authorization: Bearer $WEBUI_TOKEN"
```

### n8n Webhooks

```bash
# Trigger workflow (example)
curl -X POST https://n8n.vectorweight.com/webhook/ai-pipeline \
  -H "Content-Type: application/json" \
  -d '{"input": "Process this"}'
```

---

*For credentials, see `ADMIN_CREDENTIALS.local.md` (generated by `uv run shai-secrets export`)*
