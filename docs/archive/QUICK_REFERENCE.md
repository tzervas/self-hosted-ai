# Quick Reference: Self-Hosted AI Cluster Configuration

## 🎯 Essential URLs & Access Points

| Service | URL | Port | Type |
|---------|-----|------|------|
| **Open WebUI** | https://ai.homelab.local | 8080 | Web UI |
| **GitLab** | https://gitlab.homelab.local | 80/443 | Source Control |
| **LiteLLM API** | https://api.homelab.local | 4000 | API Gateway |
| **N8N** | https://n8n.homelab.local | 5678 | Automation |
| **SearXNG** | https://search.homelab.local | 8080 | Search |
| **Prometheus** | https://prometheus.homelab.local | 9090 | Metrics |
| **Ollama** | https://ollama.homelab.local | 11434 | Models |
| **Traefik Dashboard** | https://traefik.homelab.local | 9000 | Ingress |
| **Longhorn** | https://longhorn.homelab.local | 80 | Storage |
| **ArgoCD** | https://argocd.homelab.local | 443 | GitOps |

## 🚀 Deployment Commands

```bash
# Step 1: Generate TLS certificates
export DOMAIN=homelab.local SERVER_HOST=192.168.1.170 GPU_WORKER_HOST=192.168.1.99
./scripts/setup-traefik-tls.sh generate

# Step 2: Deploy ArgoCD and all applications
./scripts/bootstrap-argocd.sh

# Step 3: Monitor deployment
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Access: http://localhost:8080 (admin/<password from output>)

# Step 4: Setup GitHub runners (optional)
./scripts/setup-arc-github-app.sh --org <YOUR_ORG>
```

## 🏗️ Service Port Mapping

**Internal (ClusterIP)**:
- PostgreSQL: 5432
- Redis: 6379
- Ollama (CPU): 11434
- Ollama (GPU): 11434
- Open WebUI: 8080
- LiteLLM: 4000
- N8N: 5678
- SearXNG: 8080
- Prometheus: 9090

**External (LoadBalancer - Traefik)**:
- HTTP: 80 (redirects to 443)
- HTTPS: 443
- Traefik Dashboard: 9000

**GPU Worker (External Network)**:
- Ollama: 11434
- ComfyUI: 8188
- Whisper: 9000

## 📋 Deployment Order (ArgoCD Sync Waves)

```
Wave -2: SealedSecrets (encrypt all credentials)
Wave -1: Longhorn (distributed storage)
Wave  0: PostgreSQL, Redis, GPU Operator, Time-Slicing
Wave  1: Traefik (ingress controller)
Wave  2: Kyverno (policy engine), Prometheus
Wave  4: GitLab, Dify
Wave  5: Ollama (GPU), Ollama (CPU), LiteLLM
Wave  6: Open WebUI, N8N, SearXNG
Wave  7: ARC Controller & Runners (CI/CD)
```

## 🔐 Default Credentials

| Service | User | Password | Note |
|---------|------|----------|------|
| ArgoCD | admin | auto-generated | In bootstrap output |
| GitLab | root | sealed secret | From gitlab-initial-root-password |
| Open WebUI | - | sealed secret | From webui-secret |
| N8N | - | sealed secret | From n8n-secret |

**All secrets are encrypted via SealedSecrets and stored in Git**

## 🖥️ Hardware Configuration

| Component | Node | Spec |
|-----------|------|------|
| Control Plane | homelab | Intel CPU, 120GB RAM |
| GPU Worker | akula-prime | NVIDIA RTX 5080 (16GB), GPU time-slicing enabled |

## 🔒 TLS/Certificate Details

- **Type**: Self-signed (365 days validity)
- **Location**: `/data/traefik/certs/`
- **CN**: homelab.local
- **SANs**: *.homelab.local, localhost, *.localhost, 127.0.0.1, 192.168.1.170, 192.168.1.99

**Trust Instructions**:
```bash
# Linux
sudo cp /data/traefik/certs/cert.pem /usr/local/share/ca-certificates/self-hosted-ai.crt
sudo update-ca-certificates

# macOS
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain /data/traefik/certs/cert.pem
```

## 📊 AI Models Deployed

### GPU Ollama (RTX 5080)
- qwen2.5-coder:14b (primary coding)
- deepseek-coder-v2:16b
- codellama:13b
- llava:13b (vision)
- nomic-embed-text (embeddings)

### CPU Ollama (120GB RAM)
- mistral:7b (fallback chat)
- phi3:latest (lightweight)
- nomic-embed-text (embeddings)
- sqlcoder:15b (SQL generation)
- qwen2.5:7b (long context, 128k tokens)

## 🔧 Troubleshooting

```bash
# Check application sync status
kubectl get applications -n argocd

# View ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Check Traefik routes
kubectl logs -n traefik deploy/traefik | grep router

# Verify services
kubectl get svc -A | grep -E "ai-services|traefik|gitlab"

# Monitor model loading
kubectl logs -n ai-services deploy/ollama-gpu -f

# Check persistent volumes
kubectl get pvc -A
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| argocd/apps/root.yaml | Root Application (App-of-Apps) |
| config/traefik/dynamic.yml | Traefik routing configuration |
| helm/**/values.yaml | Service helm configurations |
| scripts/bootstrap-argocd.sh | Main deployment script |
| scripts/setup-traefik-tls.sh | Certificate generation |
| scripts/setup-arc-github-app.sh | GitHub runners setup |

## ⚙️ Environment Variables (.env)

```bash
DATA_PATH=/data                           # Storage location
GPU_WORKER_HOST=192.168.1.99             # GPU node IP
DOMAIN=homelab.local                      # Base domain
OLLAMA_KEEP_ALIVE=30m                    # Model cache duration
OLLAMA_NUM_PARALLEL=4                    # Concurrent GPU requests
ENABLE_RAG_WEB_SEARCH=true               # Web search in UI
```

## 🎓 Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster (k3s)             │
├──────────────────────────┬────────────────────────────────┤
│  Homelab (Control Plane) │   Akula-Prime (GPU Worker)    │
│  - Traefik LB            │   - NVIDIA RTX 5080           │
│  - PostgreSQL            │   - Ollama (GPU models)       │
│  - Redis                 │   - ComfyUI                   │
│  - Ollama (CPU)          │   - Longhorn (GPU-local)      │
│  - Open WebUI            │                               │
│  - LiteLLM               │                               │
│  - ArgoCD                │                               │
│  - GitLab                │                               │
│  - N8N                   │                               │
│  - Longhorn (2x replica) │                               │
└──────────────────────────┴────────────────────────────────┘
              │
              └─ All services routed through Traefik (443/TLS)
                 ↓
        Encrypted via self-signed cert
        Domain: homelab.local
```

## 📞 Support Resources

- Full documentation: [CLUSTER_CONTEXT_FINDINGS.md](CLUSTER_CONTEXT_FINDINGS.md)
- Deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Production features: [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md)
- Implementation guide: [implementation-guide.md](implementation-guide.md)
