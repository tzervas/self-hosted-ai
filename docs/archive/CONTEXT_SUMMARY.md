# Context Gathering Summary - Self-Hosted AI K3s Cluster

**Date**: January 15, 2026  
**Workspace**: `/home/kang/self-hosted-ai`  
**Status**: ✅ Comprehensive Context Complete

---

## 📋 Deliverables Generated

### 1. **CLUSTER_CONTEXT_FINDINGS.md** (2,147 lines)
**Comprehensive technical reference covering:**
- Traefik/Ingress routing configuration (all 13 services mapped)
- Service port assignments and health checks
- Bootstrap script analysis (274-line bootstrap-argocd.sh)
- TLS certificate configuration (self-signed, 365 days, SANs defined)
- Authentication setup (ArgoCD, GitLab, Open WebUI, N8N)
- Deployment structure (20 applications, 7 sync waves, 11 namespaces)
- GitHub Actions Runner (ARC) configuration
- Hardware topology (homelab + akula-prime GPU worker)
- AI models inventory (text, vision, embeddings)
- Environment variables and configuration
- Deployment procedures and troubleshooting

### 2. **QUICK_REFERENCE.md** (250 lines)
**Quick lookup guide:**
- Service URLs and access points (10 services)
- Port mappings (internal vs. external)
- Deployment commands (4 quick steps)
- Default credentials template
- AI models list
- Troubleshooting commands
- Architecture diagram

### 3. **CLUSTER_DEPLOYMENT_READINESS.md** (450 lines)
**Deployment checklist and verification:**
- Pre-deployment status (8 categories)
- Deployment readiness checklist (20 applications)
- Critical configuration points
- Resource requirements (CPU, memory, storage)
- Pre-deployment verification steps (5 phases)
- Post-deployment verification (5 phases)
- Troubleshooting quick reference
- Deployment checklist

---

## 🎯 Key Findings at a Glance

### Traefik/Ingress Configuration
✅ **Type**: Native Kubernetes Ingress + Traefik CRD provider  
✅ **Ports**: 80→443 (HTTP redirect), 443 (HTTPS), 9000 (dashboard)  
✅ **Services**: 13 ingress routes defined across namespaces  
✅ **Routing**: Hostname-based (e.g., ai.homelab.local, api.homelab.local)  
✅ **TLS**: Self-signed certificates with dynamic config  

### Service Port Assignments
✅ **No conflicts detected** - ClusterIP services use internal DNS  
✅ **All ports documented** and mapped in dynamic.yml  
✅ **Health checks** configured for critical services  
✅ **External services** on separate GPU worker network (192.168.1.99)  

### Bootstrap Script Status
✅ **ArgoCD 7.7.7** - Fully configured, ready to deploy  
✅ **SealedSecrets** - Automatic encryption of credentials  
✅ **App-of-Apps** - Root application with 20 child apps  
✅ **Sync Waves** - 7 deployment phases with dependencies  
✅ **Git Source** - GitHub repository (tzervas/self-hosted-ai)  

### Certificate Configuration
✅ **Self-signed** - 365-day validity  
✅ **Location**: /data/traefik/certs/  
✅ **SANs**: *.homelab.local, localhost, *.localhost, 2 IP addresses  
✅ **Trust Instructions** - Documented for Linux, macOS, Windows, Firefox  
✅ **Renewal**: Manual (365-day cycle)  

### Authentication Configuration
✅ **ArgoCD**: Admin user (password auto-generated)  
✅ **GitLab**: Root user (sealed secret)  
✅ **Open WebUI**: Admin account (sealed secret)  
✅ **LiteLLM**: Master key (sealed secret)  
✅ **N8N**: Basic auth (sealed secret)  
✅ **SealedSecrets**: Auto-encryption in kube-system  

### Service Deployment Status
✅ **20 Applications** configured and ready  
✅ **Deployment Order**: 7 sync waves (-2 to 7)  
✅ **Namespaces**: 11 namespaces across cluster  
✅ **Storage**: Longhorn distributed storage configured  
✅ **Monitoring**: Prometheus + Grafana stack included  

### Runner Configuration (GitHub Actions)
✅ **ARC** (Actions Runner Controller) - 0.9.3 configured  
✅ **Standard Runners** - Min 1, Max 10 (homelab node)  
✅ **GPU Runners** - Min 0, Max 2 (akula-prime node)  
✅ **Setup Script** - setup-arc-github-app.sh (226 lines)  
⚠️ **Manual GitHub App** - Requires creation and secret setup  

### Hardware & Nodes
✅ **Homelab Server**: 120GB RAM, Intel CPU (control plane + services)  
✅ **Akula-Prime**: NVIDIA RTX 5080 (16GB VRAM), GPU time-slicing enabled  
✅ **Storage**: Longhorn with btrfs subvolumes  
✅ **GPU Operator**: v25.10.1, RTX 5080 compatible  

### AI Models & Inference
✅ **GPU Ollama**: 8 models including qwen2.5-coder:14b  
✅ **CPU Ollama**: 10 models for fallback and specialized tasks  
✅ **LiteLLM API**: Gateway (port 4000) for unified access  
✅ **Embeddings**: nomic-embed-text for semantic search  
✅ **Vision**: llava:13b for image understanding  

---

## 📊 Configuration Inventory

### Helm Charts (15 unique charts)
- Traefik (32.0.0)
- SealedSecrets (2.16.2)
- Longhorn (1.7.2)
- NVIDIA GPU Operator (v25.10.1)
- Kyverno (3.3.3)
- Prometheus (80.13.3)
- GitLab (9.7.1)
- Dify (3.7.3)
- Ollama (custom)
- LiteLLM (custom)
- Open WebUI (custom)
- N8N (custom)
- SearXNG (custom)
- PostgreSQL (custom)
- Redis (custom)
- ARC Components (0.9.3)

### Applications (20 total)
- Wave -2: SealedSecrets
- Wave -1: Longhorn
- Wave 0: PostgreSQL, Redis, GPU Operator, GPU Time-Slicing
- Wave 1: Traefik
- Wave 2: Kyverno, Prometheus
- Wave 4: GitLab, Dify
- Wave 5: Ollama (GPU), Ollama (CPU), LiteLLM
- Wave 6: Open WebUI, N8N, SearXNG
- Wave 7: ARC Controller, ARC Runners (std + GPU)

### Namespaces (11 total)
- argocd (root application)
- ai-services (core AI services)
- gitlab (source control)
- dify (AI workflows)
- automation (N8N)
- monitoring (Prometheus)
- traefik (ingress)
- kube-system (system services + SealedSecrets)
- arc-systems (ARC controller)
- arc-runners (ARC runner pools)
- Others (longhorn-system, gpu-operator-system, etc.)

---

## 🔐 Security & Secrets

**Secrets Management**:
- ✅ SealedSecrets for encryption at rest
- ✅ Sealed secret for each service (gitlab, webui, litellm, n8n)
- ✅ PostgreSQL credentials (sealed)
- ✅ Redis credentials (sealed)
- ✅ API keys and master keys (sealed)

**TLS/HTTPS**:
- ✅ All services behind Traefik with HTTPS
- ✅ Self-signed certificate for homelab.local
- ✅ TLS 1.2+ enforced
- ✅ Modern cipher suites configured

**Network Security**:
- ✅ Service-to-service via ClusterIP (internal DNS)
- ✅ Ingress via Traefik LoadBalancer (controlled entry point)
- ✅ Kyverno policy engine for admission control
- ✅ RBAC implied (sealed-secrets, argocd roles)

---

## 📁 File Reference Matrix

| Category | File | Lines | Purpose |
|----------|------|-------|---------|
| **Bootstrap** | scripts/bootstrap-argocd.sh | 274 | ArgoCD & root app deployment |
| **Bootstrap** | scripts/bootstrap.sh | 428+ | Initial setup & model syncing |
| **TLS** | scripts/setup-traefik-tls.sh | 194 | Certificate generation |
| **Runners** | scripts/setup-arc-github-app.sh | 226 | GitHub App configuration |
| **Config** | config/traefik/dynamic.yml | 150 | Traefik routing rules |
| **Config** | .env | 40 | Environment variables |
| **ArgoCD** | argocd/apps/root.yaml | 45 | Root App-of-Apps |
| **Helm** | argocd/helm/gitlab/values.yaml | 236 | GitLab configuration |
| **Helm** | argocd/helm/prometheus/values.yaml | 207 | Prometheus monitoring |
| **Helm** | argocd/helm/ollama/values.yaml | 170 | Ollama GPU models |
| **Helm** | argocd/helm/dify/values.yaml | 258 | Dify AI platform |
| **Helm** | helm/open-webui/values.yaml | 72 | Open WebUI configuration |
| **Helm** | helm/litellm/values.yaml | 114 | LiteLLM API gateway |
| **Helm** | helm/n8n/values.yaml | 65 | N8N workflow engine |
| **Helm** | helm/server/values.yaml | 452 | Composite server config |

---

## 🚀 Deployment Timeline (Estimated)

| Phase | Component | Duration | Actions |
|-------|-----------|----------|---------|
| Pre | Generate Certificates | 5 min | `setup-traefik-tls.sh generate` |
| Pre | Trust Certificates | 5 min | System-dependent (see docs) |
| 1 | ArgoCD Bootstrap | 10 min | `bootstrap-argocd.sh` |
| 2 | Wave -2 (SealedSecrets) | 2 min | Auto-deployed |
| 3 | Wave -1 (Longhorn) | 3 min | Auto-deployed |
| 4 | Wave 0 (DB + GPU) | 10 min | Auto-deployed, GPU driver install |
| 5 | Wave 1 (Traefik) | 3 min | Auto-deployed |
| 6 | Wave 2 (Policies + Monitoring) | 5 min | Auto-deployed |
| 7 | Wave 4 (GitLab + Dify) | 20 min | Auto-deployed, database init |
| 8 | Wave 5 (Ollama + LiteLLM) | 40 min | Auto-deployed, **model downloads** |
| 9 | Wave 6 (UIs + Automation) | 5 min | Auto-deployed |
| 10 | Wave 7 (CI/CD Runners) | 3 min | Auto-deployed (if GitHub App configured) |
| **Total** | **Full Stack** | **~115 minutes** | **1.5-2 hours** |

*Note: Model download time varies by network speed. Can be 20-60 minutes.*

---

## ✅ Quick Verification Commands

```bash
# 1. Check cluster status
kubectl get nodes -o wide

# 2. Verify ArgoCD deployment
kubectl get applications -n argocd

# 3. Check service readiness
kubectl get all -A --field-selector=status.phase!=Running | grep -E "Pending|Error"

# 4. Verify ingress setup
kubectl get ingress -A

# 5. Check model downloads
kubectl logs -n ai-services statefulset/ollama-gpu -f

# 6. Verify storage
kubectl get pvc -A

# 7. Test services
curl -k https://ai.homelab.local/health
curl -k https://api.homelab.local/health/readiness

# 8. Check Traefik logs
kubectl logs -n traefik deploy/traefik | grep -E "error|router|service"

# 9. Monitor resource usage
kubectl top nodes
kubectl top pods -A

# 10. Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

---

## 🎓 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Self-Hosted AI Cluster (k3s)                 │
├──────────────────────────────────┬────────────────────────────────┤
│                                  │                                │
│   HOMELAB SERVER (Control Plane) │  AKULA-PRIME (GPU Worker)     │
│   IP: 192.168.1.170              │  IP: 192.168.1.99             │
│   CPU: Intel                      │  GPU: NVIDIA RTX 5080 (16GB)  │
│   RAM: 120GB                      │  Time-Slicing: 4x concurrent  │
│                                  │                                │
│   ┌─────────────────────────┐    │  ┌──────────────────────────┐ │
│   │  INGRESS & ROUTING      │    │  │  GPU INFERENCE           │ │
│   │  - Traefik LoadBalancer │    │  │  - Ollama (GPU models)   │ │
│   │  - TLS: 443 (homelab)   │    │  │  - ComfyUI               │ │
│   │  - 13 routes to services│    │  │  - Whisper (audio)       │ │
│   └─────────────────────────┘    │  │  - Long-form models      │ │
│                                  │  └──────────────────────────┘ │
│   ┌─────────────────────────┐    │  ┌──────────────────────────┐ │
│   │  CORE AI SERVICES       │    │  │  GPU STORAGE             │ │
│   │  - Open WebUI (8080)    │    │  │  - Longhorn (local)      │ │
│   │  - LiteLLM API (4000)   │    │  │  - 150GB for models      │ │
│   │  - SearXNG (8080)       │    │  │  - Strict-local replica  │ │
│   │  - Ollama CPU (11434)   │    │  │  - 1x replica (GPU node) │ │
│   └─────────────────────────┘    │  └──────────────────────────┘ │
│                                  │                                │
│   ┌─────────────────────────┐    │                                │
│   │  INFRASTRUCTURE         │    │                                │
│   │  - PostgreSQL (5432)    │    │                                │
│   │  - Redis (6379)         │    │                                │
│   │  - GitLab              │    │                                │
│   │  - Prometheus          │    │                                │
│   └─────────────────────────┘    │                                │
│                                  │                                │
│   ┌─────────────────────────┐    │                                │
│   │  ORCHESTRATION          │    │                                │
│   │  - ArgoCD              │    │                                │
│   │  - Kyverno (policies)  │    │                                │
│   │  - SealedSecrets       │    │                                │
│   │  - ARC Controllers     │    │                                │
│   └─────────────────────────┘    │                                │
│                                  │                                │
│   ┌─────────────────────────┐    │                                │
│   │  STORAGE (Longhorn)     │    │                                │
│   │  - 2x replicas (HA)     │    │                                │
│   │  - 500GB available      │    │                                │
│   │  - btrfs compression    │    │                                │
│   └─────────────────────────┘    │                                │
│                                  │                                │
└──────────────────────────────────┴────────────────────────────────┘
                        ↑
                All traffic via Traefik (443/TLS)
                Domain: homelab.local
                Encrypted with self-signed cert
```

---

## 🎯 Next Steps

### Immediate (Before Deployment)
1. [ ] Verify k3s cluster is healthy: `kubectl cluster-info`
2. [ ] Create `/data/traefik/` directory on homelab node
3. [ ] Verify btrfs subvolume at `/var/lib/longhorn` exists
4. [ ] Verify NVIDIA drivers on akula-prime: `nvidia-smi`
5. [ ] Configure DNS or `/etc/hosts` for homelab.local

### Deployment
1. [ ] Generate TLS certificates: `./scripts/setup-traefik-tls.sh generate`
2. [ ] Run bootstrap: `./scripts/bootstrap-argocd.sh`
3. [ ] Save ArgoCD admin password from output
4. [ ] Trust certificates on client machines
5. [ ] Monitor deployment: `watch kubectl get applications -n argocd`

### Post-Deployment
1. [ ] Access ArgoCD: https://argocd.homelab.local
2. [ ] Verify all applications healthy (green status)
3. [ ] Access Open WebUI: https://ai.homelab.local
4. [ ] Test model inference
5. [ ] Configure GitHub App for runners (optional)

### Documentation
- ✅ Read: [CLUSTER_CONTEXT_FINDINGS.md](CLUSTER_CONTEXT_FINDINGS.md) - Complete reference
- ✅ Bookmark: [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Daily lookup
- ✅ Review: [CLUSTER_DEPLOYMENT_READINESS.md](CLUSTER_DEPLOYMENT_READINESS.md) - Before deployment

---

## 📞 Documentation Cross-References

| Question | Answer Location |
|----------|------------------|
| What services are deployed? | CLUSTER_CONTEXT_FINDINGS.md - Section 6 |
| How do I access services? | QUICK_REFERENCE.md - Section "Essential URLs" |
| What ports are used? | CLUSTER_CONTEXT_FINDINGS.md - Section 2 |
| How is TLS configured? | CLUSTER_CONTEXT_FINDINGS.md - Section 4 |
| How do I deploy? | CLUSTER_DEPLOYMENT_READINESS.md - "Deployment Checklist" |
| How do I troubleshoot? | QUICK_REFERENCE.md - "Troubleshooting" |
| What are the credentials? | QUICK_REFERENCE.md - "Default Credentials" |
| How do I setup runners? | CLUSTER_CONTEXT_FINDINGS.md - Section 7 |
| What models are loaded? | CLUSTER_CONTEXT_FINDINGS.md - Section 10 |
| How long does deployment take? | This document - "Deployment Timeline" |

---

**Generated**: January 15, 2026  
**Time Spent**: ~30 minutes comprehensive context gathering  
**Files Created**: 3 detailed documentation files  
**Total Documentation**: 2,847 lines of technical reference  
**Status**: ✅ **READY FOR DEPLOYMENT**
