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

**Container Runtime**: Rootless Podman (migrated from Docker)

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

# Check Podman containers (rootless)
ssh akula-prime podman ps

# GPU access validation
ssh akula-prime 'podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.8.0-base nvidia-smi'
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
# List models across all locations
uv run scripts/sync_models.py list

# List models on GPU worker directly
curl http://192.168.1.99:11434/api/tags | jq '.models[].name'

# Pull a model
curl -X POST http://192.168.1.99:11434/api/pull -d '{"name":"qwen2.5-coder:14b"}'

# Push models to GPU worker
uv run scripts/sync_models.py push --all

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
# Full backup (PostgreSQL, Qdrant, OpenWebUI)
uv run scripts/backup.py create --all

# List backups
uv run scripts/backup.py list

# Restore from backup
uv run scripts/backup.py restore 20260115_120000

# Cleanup old backups (keep last 5)
uv run scripts/backup.py cleanup --keep 5
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

## Distributed Tracing

The platform uses **Tempo** (traces), **OpenObserve** (logs/metrics), and **Grafana** (visualization) for observability.

### Architecture

```
Services → OpenTelemetry Collector → Tempo (traces) + OpenObserve (logs/metrics)
                                   ↓
                                Grafana (dashboards)
```

### Tracing Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| **Tempo** | http://tempo.monitoring:3100 | Trace storage and query |
| **OpenObserve** | https://observe.vectorweight.com | Logs, metrics, traces UI |
| **OTel Collector** | http://otel-collector-opentelemetry-collector.monitoring:4318 | OTLP/HTTP receiver |
| **Grafana** | https://grafana.vectorweight.com | Unified observability UI |

### Querying Traces

**Via Grafana Explore**:
1. Navigate to https://grafana.vectorweight.com/explore
2. Select "Tempo" datasource
3. Search by:
   - Service name (e.g., `litellm`, `open-webui`)
   - Trace ID
   - Duration (slow requests)
   - Tags (e.g., `http.status_code=500`)

**Example TraceQL queries**:
```traceql
# Find slow LiteLLM requests (>5s)
{service.name="litellm"} | duration > 5s

# Find errors
{service.name="litellm" && status=error}

# Find specific model requests
{service.name="litellm" && resource.model="qwen2.5-coder:14b"}

# Trace by ID
{trace_id="abc123"}
```

### Common Tracing Queries

```bash
# Query Tempo directly
curl -G 'http://tempo.monitoring:3100/api/search' \
  --data-urlencode 'q={service.name="litellm"}' \
  --data-urlencode 'start=1640000000' \
  --data-urlencode 'end=1640100000'

# Get trace by ID
curl 'http://tempo.monitoring:3100/api/traces/<trace-id>'

# Check Tempo metrics
curl 'http://tempo.monitoring:3100/metrics'
```

### Instrumented Services

| Service | Status | Span Types |
|---------|--------|------------|
| **LiteLLM** | ✅ Enabled | HTTP requests, LLM inference, model routing |
| **Open WebUI** | ✅ Enabled | HTTP requests, database queries, API calls |
| **n8n** | ✅ Enabled | Workflow executions, node operations |

### Trace-to-Logs Correlation

Grafana supports jumping from traces to related logs:

1. In Grafana Explore, view a trace
2. Click "Logs for this span" button
3. Automatically queries OpenObserve for logs matching:
   - Same service name
   - Same time range
   - Same trace ID (if propagated)

### Troubleshooting Tracing

**No traces appearing**:
```bash
# Check OTel Collector is running
kubectl get pods -n monitoring -l app.kubernetes.io/name=opentelemetry-collector

# Check collector logs
kubectl logs -n monitoring -l app.kubernetes.io/name=opentelemetry-collector -f

# Verify service has OTEL env vars
kubectl get deployment litellm -n ai-services -o yaml | grep OTEL
```

**Traces incomplete**:
```bash
# Check trace sampling rate (default 100%)
kubectl get configmap -n monitoring otel-collector-config -o yaml | grep sampling

# Check for dropped spans (too many traces)
kubectl logs -n monitoring -l app.kubernetes.io/name=opentelemetry-collector | grep dropped
```

**Tempo query slow**:
```bash
# Check Tempo ingestion rate
curl http://tempo.monitoring:3100/metrics | grep tempo_ingester_bytes_received_total

# Check storage backend (should be local filesystem)
kubectl exec -n monitoring deployment/tempo -- df -h /var/tempo
```

---

## Security

### Pod Security Standards (PSS)

The platform enforces **PSS Baseline** on AI workload namespaces.

**Enforced Namespaces**:
- `ai-services`: baseline
- `gpu-workloads`: baseline
- `automation`: baseline

**What's Enforced** (PSS Baseline):
- ✅ `seccompProfile: RuntimeDefault`
- ✅ `allowPrivilegeEscalation: false`
- ✅ `capabilities.drop: ALL`
- ✅ Prevents privileged containers
- ✅ Prevents host namespace access (hostPID, hostNetwork, hostIPC)

**Check PSS Status**:
```bash
# View PSS labels on namespace
kubectl get namespace ai-services -o jsonpath='{.metadata.labels}' | jq

# Test if a pod violates PSS (dry-run)
kubectl apply --dry-run=server -f pod.yaml

# View PSS warnings
kubectl get events --field-selector reason=FailedCreate -n ai-services
```

### NetworkPolicy

**Default-Deny Enforcement**:
All AI namespaces have default-deny NetworkPolicies with explicit allow-rules.

```bash
# List NetworkPolicies
kubectl get networkpolicies -n ai-services
kubectl get networkpolicies -n gpu-workloads

# Test network connectivity
kubectl run -it --rm nettest --image=busybox -n ai-services -- wget -T 5 https://huggingface.co
# Should succeed (allowed by allow-model-downloads policy)

kubectl run -it --rm nettest --image=busybox -n ai-services -- wget -T 5 https://google.com
# Should timeout (blocked by default-deny)
```

### Container Runtime (Podman)

The GPU worker uses **rootless Podman** instead of Docker for enhanced security.

**Security Benefits**:
- No Docker daemon running as root
- User namespace isolation (container UID 0 → host UID 100000+)
- No docker group (eliminates root-equivalent access)
- GPU access via CDI (no privileged mode needed)

**Verification**:
```bash
# On GPU worker (akula-prime)
podman info | grep -A 3 "rootless:"
# Should show rootless: true

# Verify user not in docker group
groups | grep docker || echo "✓ Not in docker group"

# Verify Docker daemon stopped
systemctl is-active docker
# Should show "inactive"
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

- [ ] Rotate credentials (`uv run scripts/secrets_manager.py rotate`)
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
uv run scripts/backup.py restore 20260115_120000 --component postgresql

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
uv run scripts/secrets_manager.py generate

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

*For credentials, see `ADMIN_CREDENTIALS.local.md` (generated by `uv run scripts/secrets_manager.py export`)*
