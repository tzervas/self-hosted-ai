# Self-Hosted AI Platform - Deployment Guide

This document provides instructions for deploying and customizing the self-hosted AI platform via ArgoCD GitOps.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HOMELAB SERVER (192.168.1.170)                   │
│                         K3s Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────────────┤
│  ArgoCD (GitOps)  →  Helm Charts  →  Kubernetes Resources           │
│                                                                      │
│  Namespaces:                                                         │
│  ├── ai-services    (Open WebUI, Ollama CPU, LiteLLM, PostgreSQL)   │
│  ├── automation     (n8n workflows)                                  │
│  ├── self-hosted-ai (MCP servers)                                    │
│  ├── gpu-workloads  (GPU services - optional)                        │
│  └── monitoring     (Prometheus, Grafana)                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP API (LAN)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 GPU WORKER (192.168.1.99) - Standalone               │
│                         Docker Compose                               │
├─────────────────────────────────────────────────────────────────────┤
│  ollama-gpu-worker  →  Port 11434  →  GPU Inference (RTX 5080)      │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Homelab Server
- K3s cluster installed
- ArgoCD deployed
- kubectl access configured
- kubeseal CLI (for SealedSecrets)

### GPU Worker
- Docker with NVIDIA Container Toolkit
- NVIDIA GPU drivers installed

## Fresh Deployment

### 1. Fork/Clone the Repository

```bash
git clone https://github.com/tzervas/self-hosted-ai.git
cd self-hosted-ai
```

### 2. Generate New Secrets

Create your own secrets - **never use the defaults in production**.

```bash
# Generate random passwords
POSTGRES_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
WEBUI_PASSWORD=$(openssl rand -base64 16)
LITELLM_KEY="sk-$(openssl rand -hex 32)"
WEBUI_SECRET=$(openssl rand -hex 32)
SEARXNG_SECRET=$(openssl rand -hex 32)

echo "Save these securely:"
echo "PostgreSQL: $POSTGRES_PASSWORD"
echo "Redis: $REDIS_PASSWORD"
echo "WebUI Admin: $WEBUI_PASSWORD"
echo "LiteLLM Key: $LITELLM_KEY"
echo "WebUI Secret: $WEBUI_SECRET"
echo "SearXNG Secret: $SEARXNG_SECRET"
```

### 3. Create Kubernetes Secrets

```bash
# PostgreSQL
kubectl create secret generic postgresql-secret -n ai-services \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --from-literal=password=$POSTGRES_PASSWORD \
  --from-literal=replication-password=$(openssl rand -hex 16) \
  --dry-run=client -o yaml | kubectl apply -f -

# Redis
kubectl create secret generic redis-secret -n ai-services \
  --from-literal=redis-password=$REDIS_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -

# Open WebUI
kubectl create secret generic webui-secret -n ai-services \
  --from-literal=admin-email=admin@yourdomain.com \
  --from-literal=admin-password=$WEBUI_PASSWORD \
  --from-literal=secret-key=$WEBUI_SECRET \
  --dry-run=client -o yaml | kubectl apply -f -

# LiteLLM
kubectl create secret generic litellm-secret -n ai-services \
  --from-literal=master-key=$LITELLM_KEY \
  --from-literal=database-url="postgresql://postgres:$POSTGRES_PASSWORD@postgresql:5432/litellm" \
  --dry-run=client -o yaml | kubectl apply -f -

# SearXNG
kubectl create secret generic searxng-secret -n ai-services \
  --from-literal=secret-key=$SEARXNG_SECRET \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 4. (Optional) Use SealedSecrets for GitOps

For fully GitOps-managed secrets:

```bash
# Install kubeseal
brew install kubeseal  # macOS
# or download from https://github.com/bitnami-labs/sealed-secrets/releases

# Seal a secret
kubectl create secret generic postgresql-secret -n ai-services \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --dry-run=client -o yaml | \
  kubeseal --controller-name=sealed-secrets --controller-namespace=kube-system \
  -o yaml > helm/postgresql/templates/sealed-secret.yaml

# Commit sealed secrets to git (safe to commit - encrypted)
git add helm/*/templates/sealed-secret.yaml
git commit -m "chore: add sealed secrets for deployment"
```

### 5. Configure Domain

Edit `helm/*/values.yaml` files to set your domain:

```yaml
# Example: helm/open-webui/values.yaml
ingress:
  enabled: true
  host: ai.yourdomain.com
  tls:
    secretName: your-wildcard-tls
```

### 6. Deploy via ArgoCD

```bash
# Bootstrap ArgoCD root application
kubectl apply -f argocd/apps/root.yaml

# Monitor deployment
watch kubectl get applications -n argocd
```

## Customization

### Helm Values Override

Each service can be customized via its `values.yaml`:

| Service | Values File | Key Settings |
|---------|-------------|--------------|
| Open WebUI | `helm/open-webui/values.yaml` | replicas, resources, ingress |
| LiteLLM | `helm/litellm/values.yaml` | models, rate limits |
| Ollama | `helm/ollama/values.yaml` | GPU config, models |
| n8n | `helm/n8n/values.yaml` | workflows, integrations |
| MCP Servers | `helm/mcp-servers/values.yaml` | enabled servers |

### Enable/Disable Components

```yaml
# helm/mcp-servers/values.yaml
servers:
  memory:
    enabled: true      # Enable memory server
  sequentialThinking:
    enabled: false     # Disable (package not available)
  kubernetes:
    enabled: true      # Enable K8s integration
```

```yaml
# helm/qemu-binfmt/values.yaml
enabled: false  # Disable ARM emulation if not needed
```

### ArgoCD Sync Waves

Deployment order is controlled by sync waves in `argocd/applications/*.yaml`:

```
Wave -2: SealedSecrets (foundation)
Wave -1: cert-manager, Longhorn
Wave  0: Traefik, GPU operator
Wave  1: Linkerd, Kyverno
Wave  2: Monitoring
Wave  5: AI Backend (Ollama, LiteLLM)
Wave  6: AI Frontend (Open WebUI, n8n)
Wave  7: CI/CD Runners
```

## GPU Worker Setup

### Deploy on GPU Workstation

```bash
cd gpu-worker

# Edit configuration
cp .env.example .env
vim .env  # Set OLLAMA_PORT, DATA_PATH, etc.

# Deploy
docker compose up -d

# Verify
curl http://localhost:11434/api/tags
```

### Connect from Homelab

The homelab services connect to GPU worker via LAN:
- URL: `http://192.168.1.99:11434`
- Configure in Open WebUI: Admin Settings → Connections → Add Ollama

## Service Endpoints

| Service | URL | Notes |
|---------|-----|-------|
| Open WebUI | https://ai.yourdomain.com | Chat interface |
| n8n | https://n8n.yourdomain.com | Workflows |
| ArgoCD | https://argocd.yourdomain.com | GitOps dashboard |
| LiteLLM | https://llm.yourdomain.com/v1 | OpenAI-compatible API |
| GPU Ollama | http://192.168.1.99:11434 | Direct GPU inference |

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n ai-services
kubectl logs -n ai-services deployment/open-webui
```

### Force ArgoCD Sync
```bash
kubectl patch application <app-name> -n argocd --type='json' \
  -p='[{"op": "add", "path": "/operation", "value": {"sync": {"force": true}}}]'
```

### Reset Secrets
```bash
# Delete and recreate
kubectl delete secret <secret-name> -n ai-services
# Then recreate using commands above
```

### Scale Deployments
```bash
# Temporarily scale down
kubectl scale deployment -n ai-services open-webui --replicas=0

# Scale back up
kubectl scale deployment -n ai-services open-webui --replicas=3
```

## Backup & Recovery

### Export Secrets
```bash
# Backup all secrets (store securely!)
kubectl get secrets -n ai-services -o yaml > secrets-backup.yaml
```

### Database Backup
```bash
# PostgreSQL
kubectl exec -n ai-services postgresql-0 -- pg_dump -U postgres litellm > litellm-backup.sql
```

## Security Notes

1. **Never commit plaintext secrets** - Use SealedSecrets or external secret managers
2. **Rotate credentials regularly** - Update secrets and restart deployments
3. **Use network policies** - Limit pod-to-pod communication
4. **Enable TLS everywhere** - Use cert-manager for automatic certificates
5. **Review ArgoCD access** - Limit who can sync applications

## Support

- Architecture: See `ARCHITECTURE.md`
- Operations: See `OPERATIONS.md`
- Contributing: See `CONTRIBUTING.md`
