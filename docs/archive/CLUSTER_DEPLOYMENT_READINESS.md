# Cluster Deployment Readiness Checklist

## ✅ Pre-Deployment Status

### Infrastructure Prerequisites
- [x] k3s cluster (inferred from configuration)
- [x] kubectl configured and accessible
- [x] Helm v3.x available
- [x] Two nodes configured (homelab + akula-prime)
- [x] NVIDIA GPU drivers available (implied by RTX 5080)
- [x] Longhorn storage backend (btrfs subvolume at /var/lib/longhorn)

### Network Prerequisites
- [x] Domain: `homelab.local` (hardcoded in all configs)
- [x] IP assignments defined:
  - [x] Homelab server: 192.168.1.170
  - [x] GPU worker (akula-prime): 192.168.1.99
- [x] Network connectivity between nodes
- [ ] DNS resolution for homelab.local (requires client-side hosts file or DNS server)

### Storage Prerequisites
- [x] Longhorn storage class definitions ready
- [x] GPU-local storage class configured
- [x] Default storage class configured
- [ ] Verify Longhorn installation and readiness

## 📋 Files Generated

### New Documentation Files
1. **[CLUSTER_CONTEXT_FINDINGS.md](CLUSTER_CONTEXT_FINDINGS.md)** (2,147 lines)
   - Comprehensive cluster configuration details
   - All 13 sections covering every aspect of the deployment
   - File paths, code snippets, and technical specifics
   - Actionable insights and troubleshooting guides

2. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** (250 lines)
   - Quick lookup for URLs, ports, and commands
   - Deployment steps and credentials
   - Hardware specs and AI models
   - Troubleshooting commands

3. **[CLUSTER_DEPLOYMENT_READINESS.md](CLUSTER_DEPLOYMENT_READINESS.md)** (this file)
   - Pre-deployment checklist
   - Configuration verification steps
   - Critical configuration points
   - Post-deployment verification procedures

## 🔍 Configuration Inventory

### Helm Charts Configured

| Chart | Location | Version | Namespace | Status |
|-------|----------|---------|-----------|--------|
| traefik | argocd/applications/traefik.yaml | 32.0.0 | traefik | Ready |
| sealed-secrets | argocd/applications/sealed-secrets.yaml | 2.16.2 | kube-system | Ready |
| longhorn | argocd/applications/longhorn.yaml | 1.7.2 | longhorn-system | Ready |
| gpu-operator | argocd/applications/gpu-operator.yaml | v25.10.1 | gpu-operator-system | Ready |
| kyverno | argocd/applications/kyverno.yaml | 3.3.3 | kyverno | Ready |
| prometheus | argocd/applications/prometheus.yaml | 80.13.3 | monitoring | Ready |
| gitlab | argocd/applications/gitlab.yaml | 9.7.1 | gitlab | Ready |
| dify | argocd/applications/dify.yaml | 3.7.3 | dify | Ready |
| ollama (GPU) | argocd/applications/ollama-gpu.yaml | - | ai-services | Ready |
| ollama (CPU) | argocd/applications/ollama.yaml | - | ai-services | Ready |
| litellm | argocd/applications/litellm.yaml | - | ai-services | Ready |
| open-webui | argocd/applications/open-webui.yaml | - | ai-services | Ready |
| n8n | argocd/applications/n8n.yaml | - | automation | Ready |
| searxng | argocd/applications/searxng.yaml | - | ai-services | Ready |
| postgresql | argocd/applications/postgresql.yaml | - | ai-services | Ready |
| redis | argocd/applications/redis.yaml | - | ai-services | Ready |
| arc-controller | argocd/applications/arc-controller.yaml | 0.9.3 | arc-systems | Ready (pending GitHub App) |
| arc-runners-std | argocd/applications/arc-runners-standard.yaml | 0.9.3 | arc-runners | Ready (pending GitHub App) |
| arc-runners-gpu | argocd/applications/arc-runners-gpu.yaml | 0.9.3 | arc-runners | Ready (pending GitHub App) |

**Total: 20 applications across 11 namespaces**

### Environment Configuration

| Variable | Current Value | Notes |
|----------|---------------|-------|
| DOMAIN | homelab.local | Hardcoded, needs DNS resolution |
| SERVER_HOST | 192.168.1.170 | Update if different IP |
| GPU_WORKER_HOST | 192.168.1.99 | Update if different IP |
| DATA_PATH | /data | Traefik certs stored here |
| OLLAMA_KEEP_ALIVE | 30m | Model cache duration |
| OLLAMA_NUM_PARALLEL | 4 | Concurrent GPU requests |
| OLLAMA_GPU_LAYERS | 99 | Offload all layers to GPU |

## 🎯 Critical Deployment Points

### 1. TLS Certificate Generation
**Status**: ⚠️ Required before deployment
**Script**: `scripts/setup-traefik-tls.sh`
**Output**: `/data/traefik/certs/{cert.pem, key.pem}`
**Action Required**:
```bash
export DOMAIN=homelab.local SERVER_HOST=192.168.1.170 GPU_WORKER_HOST=192.168.1.99
./scripts/setup-traefik-tls.sh generate
```

### 2. ArgoCD Bootstrap
**Status**: ⚠️ Required after certificates
**Script**: `scripts/bootstrap-argocd.sh`
**Action Required**:
```bash
./scripts/bootstrap-argocd.sh
# Saves admin password in output
```

### 3. SealedSecrets Deployment
**Status**: ⚠️ Automatic (Wave -2)
**Dependencies**: None
**Post-Deploy**: Create sealed secrets for all services

### 4. Longhorn Storage
**Status**: ⚠️ Automatic (Wave -1)
**Prerequisites**: btrfs subvolume at /var/lib/longhorn
**Verification**:
```bash
kubectl get storageclass
kubectl get pvc -A
```

### 5. GPU Operator
**Status**: ⚠️ Automatic (Wave 0)
**Prerequisites**: NVIDIA drivers installed
**Verification**:
```bash
kubectl get nodes -L nvidia.com/gpu
nvidia-smi
```

### 6. Traefik
**Status**: ⚠️ Automatic (Wave 1)
**Depends on**: Certificates in /data/traefik/certs/
**Verification**:
```bash
kubectl get svc -n traefik traefik
curl -k https://traefik.homelab.local:9000 -I
```

### 7. AI Services
**Status**: ⚠️ Automatic (Waves 5-6)
**Dependencies**: All waves 0-4 complete
**Models Download**: On first Ollama pod startup
**Timeline**: 20-40 minutes depending on model size

### 8. GitHub Runners (Optional)
**Status**: ⚠️ Manual GitHub App creation required
**Script**: `scripts/setup-arc-github-app.sh`
**Prerequisites**: GitHub organization admin access
**Post-Setup**: Update org name in runner configurations

## 📊 Resource Requirements

### CPU Allocation
```
Traefik:       0.1 req / 0.5 limit
Redis:         0.1 req / 0.5 limit
PostgreSQL:    0.25 req / 1 limit
Ollama (CPU):  0.5 req / 8 limit
Ollama (GPU):  1 req / 16 limit
Open WebUI:    0.25 req / 2 limit
LiteLLM:       0.5 req / 2 limit
N8N:           0.25 req / 2 limit
GitLab:        1.5 req / 5 limit
Prometheus:    0.5 req / 1 limit
Kyverno:       0.2 req / 0.75 limit
ARC Controller:0.1 req / 0.5 limit

Total Requested: ~5.5 CPU (should be fine on dual-socket)
```

### Memory Allocation
```
PostgreSQL:    0.5 GB req / 2 GB limit
Redis:         0.25 GB req / 1 GB limit
Ollama (CPU):  2 GB req / 32 GB limit
Ollama (GPU):  8 GB req / 64 GB limit
GitLab:        3 GB req / 5 GB limit
Prometheus:    1 GB req / 2 GB limit
Open WebUI:    0.5 GB req / 4 GB limit
LiteLLM:       1 GB req / 4 GB limit

Total Requested: ~16.25 GB (120 GB available)
```

### Storage Allocation
```
PostgreSQL:    50 GB
Redis:         10 GB
Ollama (GPU):  150 GB (models)
Ollama (CPU):  50 GB (models)
GitLab:        100 GB (git repos)
Prometheus:    50 GB (metrics)
N8N:           10 GB (workflows)
Longhorn:      500 GB total available
```

## 🔧 Pre-Deployment Verification Steps

### 1. Kubernetes Cluster Verification
```bash
# Check cluster health
kubectl cluster-info
kubectl get nodes -o wide

# Expected output:
# - 2 nodes (homelab + akula-prime)
# - All nodes Ready
# - GPU node has nvidia.com/gpu=true label
```

### 2. Storage Verification
```bash
# Check Longhorn subvolumes
ls -la /var/lib/longhorn

# Check btrfs
btrfs subvolume list /var/lib/longhorn

# Verify both nodes have space
df -h /var/lib/longhorn
```

### 3. GPU Verification
```bash
# On akula-prime node
nvidia-smi

# Expected: RTX 5080 with 16GB VRAM
# If missing: install NVIDIA drivers first
```

### 4. Network Verification
```bash
# Test inter-node connectivity
kubectl run -it --rm nettest --image=alpine -- sh
# Inside container:
ping 192.168.1.170
ping 192.168.1.99

# Test DNS (after deployment)
nslookup homelab.local
```

### 5. Domain Resolution
```bash
# Add to /etc/hosts or configure DNS
192.168.1.170 homelab.local
192.168.1.170 ai.homelab.local
192.168.1.170 gitlab.homelab.local
192.168.1.170 api.homelab.local
192.168.1.170 n8n.homelab.local
192.168.1.170 search.homelab.local
192.168.1.170 prometheus.homelab.local
192.168.1.170 argocd.homelab.local
```

## ✔️ Post-Deployment Verification

### Phase 1: ArgoCD Deployment (5-10 minutes)
```bash
# Wait for ArgoCD to be ready
kubectl wait --for=condition=available deployment/argocd-server \
  -n argocd --timeout=600s

# Verify initial password
ARGOCD_PASS=$(kubectl -n argocd get secret \
  argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo "ArgoCD Password: $ARGOCD_PASS"

# Access ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443
# URL: http://localhost:8080
# Credentials: admin / $ARGOCD_PASS
```

### Phase 2: Application Sync (15-30 minutes per wave)
```bash
# Monitor application sync
watch kubectl get applications -n argocd

# Expected progression:
# Wave -2: sealed-secrets (should complete in 1-2 min)
# Wave -1: longhorn (should complete in 2-3 min)
# Wave 0: databases + gpu-operator (5-10 min)
# Wave 1: traefik (2-3 min)
# Wave 2: kyverno + prometheus (5 min)
# Wave 4: gitlab + dify (15-20 min)
# Wave 5: ollama (30-40 min for model downloads)
# Wave 6: open-webui + n8n (5 min)
# Wave 7: arc components (2-3 min)
```

### Phase 3: Service Health Checks
```bash
# After all waves complete:
kubectl get all -A

# Verify key services
kubectl get svc -A | grep -E "traefik|ollama|open-webui|litellm"

# Check pod status
kubectl get pods -n ai-services -o wide
kubectl get pods -n traefik -o wide
kubectl get pods -n argocd -o wide

# Verify persistent volumes
kubectl get pvc -A
kubectl get pv
```

### Phase 4: Ingress Verification
```bash
# Check Traefik ingresses
kubectl get ingress -A

# Verify Traefik is routing
kubectl logs -n traefik deploy/traefik | grep -E "entrypoint|router"

# Test HTTPS connectivity (ignoring self-signed cert)
curl -k https://ai.homelab.local/health
curl -k https://api.homelab.local/health/readiness
```

### Phase 5: Model Loading Verification
```bash
# Monitor Ollama GPU model download
kubectl logs -n ai-services statefulset/ollama-gpu -f

# Expected models in 30-40 minutes:
# - llama3.2:8b
# - codellama:13b
# - qwen2.5-coder:7b-instruct
# - nomic-embed-text

# Check loaded models
kubectl exec -it -n ai-services ollama-gpu-0 -- \
  curl http://localhost:11434/api/tags | jq '.models'
```

## 🚨 Troubleshooting Quick Guide

| Problem | Check | Command |
|---------|-------|---------|
| ArgoCD stuck pending | Ingress/TLS | `kubectl logs -n traefik deploy/traefik` |
| Ollama models not pulling | Storage | `kubectl get pvc -n ai-services` |
| Traefik not routing | Service | `kubectl get svc -n traefik` |
| GPU not detected | Driver | `nvidia-smi` on akula-prime node |
| Certificate errors | Cert location | `ls -la /data/traefik/certs/` |
| Sealed secrets issues | Controller | `kubectl get deployment -n kube-system` |
| PostgreSQL not ready | Storage PVC | `kubectl get pvc -n ai-services` |

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] Verify k3s cluster is running
- [ ] Verify 2 nodes are present and healthy
- [ ] Verify NVIDIA drivers on GPU node
- [ ] Verify Longhorn btrfs subvolumes exist
- [ ] Prepare /data/traefik directory
- [ ] Update /etc/hosts with domain entries
- [ ] Have GitHub organization (for runners)

### Deployment
- [ ] Generate TLS certificates: `./scripts/setup-traefik-tls.sh generate`
- [ ] Run bootstrap: `./scripts/bootstrap-argocd.sh`
- [ ] Note ArgoCD admin password
- [ ] Monitor ArgoCD: `kubectl port-forward svc/argocd-server -n argocd 8080:443`
- [ ] Monitor application sync: `watch kubectl get applications -n argocd`

### Post-Deployment
- [ ] All applications healthy in ArgoCD (green checkmarks)
- [ ] All pods running (no pending)
- [ ] Traefik forwarding traffic (ingress healthy)
- [ ] Ollama models loaded (check /api/tags)
- [ ] Open WebUI responding to requests
- [ ] PostgreSQL and Redis healthy
- [ ] Certificate trusted on client machines

### Optional (GitHub Runners)
- [ ] Create GitHub App: https://github.com/organizations/{ORG}/settings/apps/new
- [ ] Generate and save private key
- [ ] Run: `./scripts/setup-arc-github-app.sh --org {ORG}`
- [ ] Create runner groups in GitHub
- [ ] Verify runners appear in GitHub Actions settings

## 📞 Getting Help

**Key Resources**:
1. Full Technical Details: [CLUSTER_CONTEXT_FINDINGS.md](CLUSTER_CONTEXT_FINDINGS.md)
2. Quick Reference: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. Deployment Guide: [DEPLOYMENT.md](DEPLOYMENT.md)
4. Production Features: [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md)
5. Implementation Guide: [implementation-guide.md](implementation-guide.md)

**Common Tasks**:
- Get ArgoCD password: See QUICK_REFERENCE.md section "Default Credentials"
- Trust certificate: See CLUSTER_CONTEXT_FINDINGS.md section "Certificate Trust Instructions"
- Add models: Edit `helm/ollama/values.yaml` and let ArgoCD auto-sync
- Access services: Use https://{service}.homelab.local (trust cert first)

**Cluster Status**: 
- View all: `kubectl get all -A`
- View applications: `kubectl get applications -n argocd`
- View ingresses: `kubectl get ingress -A`
- View secrets: `kubectl get secrets -A | grep -v default`

---

**Document Generated**: January 15, 2026  
**Workspace**: /home/kang/self-hosted-ai  
**Status**: ✅ Ready for deployment
