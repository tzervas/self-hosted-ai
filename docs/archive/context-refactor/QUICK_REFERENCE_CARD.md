# Quick Reference Card: Self-Hosted AI Platform v2.0

## ⚠️ CRITICAL CORRECTIONS FROM ORIGINAL PLAN

| Original Claim | Reality | Impact |
|----------------|---------|--------|
| `qwen2.5-coder:72b-instruct-q4_k_m` | **DOES NOT EXIST** - max is 32B | Deployment fails |
| `deepseek-coder-v2:33b-instruct-q5_k_m` | **DOES NOT EXIST** - V2 is 16B or 236B only | Deployment fails |
| 72B Q4 fits in 16GB VRAM | **IMPOSSIBLE** - needs ~47GB | OOM crashes |
| Ollama Helm repo `otwld.github.io` | **MIGRATED** to `helm.otwld.com` | Helm install fails |
| Continue.dev `config.json` | **DEPRECATED** - use `config.yaml` | Extension fails |
| `@codebase` feature | **DEPRECATED** - use Agent mode | Feature unavailable |

---

## ✅ Verified Helm Repositories

```bash
# Copy-paste ready
helm repo add gitlab https://charts.gitlab.io
helm repo add otwld https://helm.otwld.com
helm repo add dify https://borispolonsky.github.io/dify-helm
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo add longhorn https://charts.longhorn.io
helm repo add jetstack https://charts.jetstack.io
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
```

---

## ✅ Verified Models for RTX 5080 (16GB VRAM)

### Works Perfectly
| Model | Size | VRAM | Use Case |
|-------|------|------|----------|
| `llama3.2:8b` | 8B | ~5GB | Primary reasoning |
| `qwen2.5-coder:7b-instruct` | 7B | ~4GB | Fast autocomplete |
| `codellama:7b-instruct` | 7B | ~4GB | Quick code tasks |
| `nomic-embed-text` | 137M | ~274MB | Embeddings |
| `mistral:7b-instruct` | 7B | ~4GB | General assistant |

### Works with Caution
| Model | Size | VRAM | Notes |
|-------|------|------|-------|
| `codellama:13b` | 13B | ~8GB | Limit context to 8K |
| `llava:13b` | 13B | ~8GB | Vision, tight fit |
| `qwen2.5-coder:14b-instruct` | 14B | ~9GB | Good, reduce context |
| `deepseek-coder:6.7b` | 6.7B | ~4GB | V1, not V2 |

### WILL NOT WORK
| Model | Why |
|-------|-----|
| Any 32B+ model | Needs >20GB VRAM |
| Any 70B+ model | Needs >40GB VRAM |
| `qwen2.5-coder:32b` | 20GB+ needed |
| `deepseek-coder-v2:236b` | 120GB+ needed |

---

## ✅ ArgoCD Sync Wave Order

```
Wave 0: gpu-operator        # GPU support first
Wave 1: longhorn            # Storage
Wave 1: sealed-secrets      # Secret management
Wave 2: cert-manager        # TLS certificates
Wave 3: gitlab              # Git + CI/CD
Wave 4: gitlab-runner       # CI runners
Wave 5: ollama              # LLM inference
Wave 6: dify                # RAG + agents
Wave 6: n8n                 # Workflow automation
```

---

## ✅ GitLab Runner Token Format (GitLab 16+)

```bash
# OLD (DEPRECATED) - Will NOT work:
registration_token: "GR1348941xxxxx"

# NEW (REQUIRED) - Get from GitLab UI:
# Admin → CI/CD → Runners → New Instance Runner
runner_token: "glrt-xxxxxxxxxxxx"
```

---

## ✅ GPU Time-Slicing Configuration

```yaml
# ConfigMap for NVIDIA GPU Operator
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
  namespace: gpu-operator
data:
  rtx-5080: |-
    version: v1
    flags:
      migStrategy: none  # MIG not supported on RTX 5080
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
          - name: nvidia.com/gpu
            replicas: 4  # Creates 4 virtual GPUs
```

---

## ✅ Continue.dev Config (YAML Format)

```yaml
# ~/.continue/config.yaml (NOT config.json!)
name: Homelab AI
version: 0.0.1
schema: v1

models:
  - name: Code Assistant
    provider: ollama
    model: codellama:13b
    apiBase: http://ollama.homelab.local:11434
    roles: [chat, edit]
    
  - name: Fast Complete
    provider: ollama
    model: qwen2.5-coder:7b-instruct
    apiBase: http://ollama.homelab.local:11434
    roles: [autocomplete]
    
  - name: Embeddings
    provider: ollama
    model: nomic-embed-text
    apiBase: http://ollama.homelab.local:11434
    roles: [embed]
```

---

## ✅ Resource Requirements Summary

| Component | CPU Request | Memory Request | Storage |
|-----------|-------------|----------------|---------|
| GitLab (all) | ~1 core | ~8GB | 80GB |
| GitLab Runner | 500m | 256MB | - |
| Ollama | 2 cores | 8GB | 200GB |
| Dify | 1.5 cores | 4GB | 90GB |
| Longhorn | 500m | 512MB | - |
| **Total** | **~5.5 cores** | **~21GB** | **~370GB** |

⚠️ **Minimum viable**: 8 cores, 32GB RAM, 500GB storage

---

## ✅ Network Endpoints (Internal)

| Service | Cluster DNS | Port |
|---------|-------------|------|
| Ollama API | `ollama.ollama.svc.cluster.local` | 11434 |
| GitLab Web | `gitlab-webservice.gitlab.svc.cluster.local` | 8181 |
| GitLab SSH | `gitlab-gitlab-shell.gitlab.svc.cluster.local` | 22 |
| Dify API | `dify-api.dify.svc.cluster.local` | 5001 |
| Dify Web | `dify-web.dify.svc.cluster.local` | 3000 |

---

## ✅ Quick Deployment Commands

```bash
# 1. Install k3s with GPU support
curl -sfL https://get.k3s.io | sh -s - server

# 2. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Get ArgoCD password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# 4. Apply root application
kubectl apply -f argocd/bootstrap/root-app.yaml

# 5. Watch deployment
watch kubectl get pods -A
```

---

## ✅ Validation Commands

```bash
# Check GPU availability
kubectl get nodes -o=custom-columns='NAME:.metadata.name,GPU:.status.capacity.nvidia\.com/gpu'

# Check Ollama models
kubectl exec -n ollama deploy/ollama -- ollama list

# Test Ollama API
curl http://ollama.homelab.local:11434/api/tags

# Check ArgoCD sync status
kubectl get applications -n argocd

# View GitLab runner status
kubectl logs -n gitlab-runner -l app=gitlab-runner -f
```

---

## File Locations

| File | Purpose |
|------|---------|
| `SYSTEM_PROMPT_SPEC_DRIVEN_AGENT.md` | Complete system prompt for coding agent |
| `env.example` | All environment variables with documentation |
| This file | Quick reference for verified configurations |
