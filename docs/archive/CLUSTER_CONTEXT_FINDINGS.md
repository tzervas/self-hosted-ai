# Self-Hosted AI K3s Cluster - Comprehensive Context Findings

**Generated:** January 15, 2026  
**Workspace:** `/home/kang/self-hosted-ai`

---

## 1. TRAEFIK/INGRESS CONFIGURATION

### Port Mappings & Entrypoints

**Traefik Service Configuration** ([argocd/applications/traefik.yaml](argocd/applications/traefik.yaml)):
- **Web (HTTP)**: Port 8000 (internal) → 80 (external), redirects to websecure
- **WebSecure (HTTPS)**: Port 8443 (internal) → 443 (external), TLS enabled
- **Traefik Dashboard**: Port 9000 (internal), exposed as 9000 (external)
- **Service Type**: LoadBalancer

### Routing Configuration

All ingress routes use **Traefik CRD provider** (Kubernetes-native) with the following setup:

**Ingress Routes** (native Kubernetes Ingress resources with Traefik annotations):

| Service | Hostname | Port | Entrypoint | TLS |
|---------|----------|------|------------|-----|
| Open WebUI | `ai.homelab.local` | 8080 | websecure | Yes |
| LiteLLM API | `llm.homelab.local` or `api.homelab.local` | 4000 | websecure | Yes |
| N8N | `n8n.homelab.local` | 5678 | websecure | Yes |
| SearXNG | `search.homelab.local` | 8080 | websecure | Yes |
| GitLab | `gitlab.homelab.local` | 80 | websecure | Yes |
| Registry | `registry.homelab.local` | 443 | websecure | Yes |
| Prometheus | `prometheus.homelab.local` | 9090 | websecure | Yes |
| Grafana | `grafana.homelab.local` | 3000 | websecure | Yes |
| Ollama | `ollama.homelab.local` | 11434 | websecure | Yes |
| Traefik Dashboard | `traefik.homelab.local` | 9000 | websecure | Yes |
| Longhorn | `longhorn.homelab.local` | 80 | websecure | No |

**Traefik Configuration Details** ([argocd/applications/traefik.yaml](argocd/applications/traefik.yaml)):
```yaml
providers:
  kubernetesCRD:
    enabled: true
    allowCrossNamespace: true
  kubernetesIngress:
    enabled: true
    publishedService:
      enabled: true
```

**Dynamic Configuration** ([config/traefik/dynamic.yml](config/traefik/dynamic.yml)):
- Uses templated configuration with environment variable substitution
- Defines routers for all services
- Health checks configured for key services
- Load balancing with multiple server backends where applicable

### TLS Configuration

**Type**: Self-signed certificates (manual generation required)

**Certificate Paths** (as referenced in Traefik config):
- Cert file: `/certs/cert.pem`
- Key file: `/certs/key.pem`

**Certificate Details**:
- **Duration**: 365 days
- **CN**: `homelab.local`
- **SANs**: 
  - `*.homelab.local`
  - `localhost`
  - `*.localhost`
  - IP: `127.0.0.1`
  - IP: `192.168.1.170` (homelab server)
  - IP: `192.168.1.99` (akula-prime GPU worker)

**TLS Options**:
```yaml
tlsOptions:
  default:
    minVersion: VersionTLS12
    cipherSuites:
      - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
      - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
      - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
      - TLS_AES_128_GCM_SHA256
      - TLS_AES_256_GCM_SHA384
      - TLS_CHACHA20_POLY1305_SHA256
```

**Certificate Generation Script**: [scripts/setup-traefik-tls.sh](scripts/setup-traefik-tls.sh)
- Generates self-signed certificates with openssl
- Creates configuration files at `$DATA_PATH/traefik/certs/`
- Provides trust instructions for Linux, macOS, Windows, and Firefox

---

## 2. SERVICE PORT ASSIGNMENTS

### Core AI Services

| Service | Namespace | Port | Type | Function |
|---------|-----------|------|------|----------|
| **open-webui** | ai-services | 8080/TCP | ClusterIP | Web UI for AI models |
| **litellm** | ai-services | 4000/TCP | ClusterIP | API gateway for LLM requests |
| **ollama** (CPU) | ai-services | 11434/TCP | ClusterIP | CPU-based model inference |
| **ollama-gpu** | ai-services | 11434/TCP | ClusterIP | GPU-based model inference (RTX 5080) |
| **searxng** | ai-services | 8080/TCP | ClusterIP | Metasearch engine |

### Infrastructure Services

| Service | Namespace | Port | Type | Function |
|---------|-----------|------|------|----------|
| **postgresql** | ai-services | 5432/TCP | ClusterIP | Database backend |
| **redis-master** | ai-services | 6379/TCP | ClusterIP | Caching/session store |
| **traefik** | traefik | 80/TCP, 443/TCP, 9000/TCP | LoadBalancer | Ingress controller |

### Application Services

| Service | Namespace | Port | Type | Function |
|---------|-----------|------|------|----------|
| **gitlab** | gitlab | 80/TCP, 443/TCP | Ingress (Traefik) | Source control & CI/CD |
| **n8n** | automation | 5678/TCP | ClusterIP | Workflow automation |
| **prometheus** | monitoring | 9090/TCP | ClusterIP | Metrics collection |
| **alertmanager** | monitoring | 9093/TCP | ClusterIP | Alert management |
| **pushgateway** | monitoring | 9091/TCP | ClusterIP | Metrics push gateway |
| **dify** | dify | 80/TCP | Ingress (Traefik) | AI agent workflow platform |

### GPU Worker Services (External)

These run outside Kubernetes on `192.168.1.99`:
- **ollama** (GPU): 11434/TCP
- **comfyui**: 8188/TCP
- **whisper** (Audio): 9000/TCP
- **automatic1111**: 7860/TCP

### Service Health Checks

**Open WebUI**:
```
Path: /health
Interval: 30s
Timeout: 5s
```

**LiteLLM**:
```
Path: /health/readiness
Interval: 10s
Timeout: 5s
Port: 4000
```

**SearXNG**:
```
Path: /healthz
Interval: 30s
Timeout: 5s
```

### Port Conflict Analysis

**No conflicts detected**:
- Kubernetes services use ClusterIP (internal DNS resolution only)
- Traefik LoadBalancer binds to host ports 80/443
- Ingress rules route by hostname, not port
- GPU Worker services run on external host (separate network)

---

## 3. BOOTSTRAP SCRIPT STATUS

### bootstrap-argocd.sh Script Overview

**Location**: [scripts/bootstrap-argocd.sh](scripts/bootstrap-argocd.sh)  
**Size**: 274 lines  
**Purpose**: Deploy ArgoCD and root App-of-Apps infrastructure

### Script Flow

**Phase 1: Preflight Checks**
- Verifies kubectl availability
- Verifies helm v3.x installation
- Tests cluster connectivity

**Phase 2: ArgoCD Installation**
```bash
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --version 7.7.7 \
  --set server.ingress.enabled=true \
  --set server.ingress.ingressClassName=traefik \
  --set server.ingress.hosts[0]=argocd.homelab.local \
  --set server.ingress.tls[0].hosts[0]=argocd.homelab.local \
  --set configs.params.server\.insecure=true
```

**ArgoCD Configuration**:
- Namespace: `argocd`
- Version: 7.7.7
- Ingress: Traefik with hostname `argocd.homelab.local`
- Insecure mode: Enabled (for development)
- Resource limits:
  - Redis: 100m CPU / 128Mi RAM
  - Server: 100m CPU / 256Mi RAM
  - Controller: 250m CPU / 512Mi RAM
  - RepoServer: 100m CPU / 256Mi RAM

**Phase 3: SealedSecrets Installation**
```bash
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=64Mi
```

**Phase 4: Secrets Generation**
- Calls `scripts/generate-secrets.sh` (not yet examined)
- Creates sealed secrets for services

**Phase 5: Root Application Deployment**
- Applies `argocd/apps/root.yaml`
- Enables App-of-Apps GitOps pattern
- Git source: `https://github.com/tzervas/self-hosted-ai.git`
- Branch: `main`
- Path: `argocd/applications/*.yaml`

### Initial Admin Access

**Default Credentials**:
- Username: `admin`
- Password: Retrieved from secret `argocd-initial-admin-secret`

**Access Methods**:
1. HTTPS: `https://argocd.homelab.local`
2. Port-forward: `kubectl port-forward svc/argocd-server -n argocd 8080:443`

### Script Flags

```bash
--skip-argocd          # Skip ArgoCD installation
--skip-secrets         # Skip secrets generation
--no-sealed-secrets    # Don't install SealedSecrets
--repo <url>           # Custom Git repository
--branch <branch>      # Custom branch (default: main)
```

### Current Deployment Status

✅ **ArgoCD 7.7.7** is configured for deployment  
✅ **SealedSecrets** controller configured  
❓ **Root application** status unknown (needs verification)  
❓ **Actual deployment** status unknown (requires `kubectl get applications`)

---

## 4. CERTIFICATE CONFIGURATION

### Current Setup

**Type**: Self-signed certificates  
**Source**: Manual generation via `setup-traefik-tls.sh`  
**No cert-manager or Let's Encrypt configured**

### TLS Setup Script Details

**File**: [scripts/setup-traefik-tls.sh](scripts/setup-traefik-tls.sh)  
**Functions**:
1. `generate_self_signed_cert()` - Create self-signed certificate
2. `setup_config()` - Configure Traefik dynamic config
3. `trust_certificate()` - Provide OS-specific trust instructions

### Certificate Generation

**Command** (from script):
```bash
openssl genrsa -out $CERT_DIR/key.pem 4096
openssl req -new -x509 -sha256 -days 365 \
  -key $CERT_DIR/key.pem \
  -out $CERT_DIR/cert.pem \
  -config $CERT_DIR/csr.conf
```

**Certificate Details**:
- **Algorithm**: RSA 4096-bit
- **Signature**: SHA256
- **Validity**: 365 days
- **Subject CN**: `homelab.local` (configurable via $DOMAIN env var)

**Subject Alt Names (SANs)**:
```
DNS.1 = homelab.local
DNS.2 = *.homelab.local
DNS.3 = localhost
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = 192.168.1.170 (homelab server - configurable)
IP.3 = 192.168.1.99 (GPU worker - configurable)
```

### Certificate Trust Instructions

**Linux (Debian/Ubuntu)**:
```bash
sudo cp $CERT_DIR/cert.pem /usr/local/share/ca-certificates/self-hosted-ai.crt
sudo update-ca-certificates
```

**macOS**:
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/cert.pem
```

**Windows (PowerShell as Admin)**:
```powershell
Import-Certificate -FilePath $CERT_DIR/cert.pem -CertStoreLocation Cert:\LocalMachine\Root
```

**Firefox**: Manual import via `Preferences > Privacy & Security > Certificates`

### Certificate Storage Location

`$DATA_PATH/traefik/certs/` (typically `/data/traefik/certs/`)
- `cert.pem` - Public certificate
- `key.pem` - Private key (mode 600)
- `csr.conf` - Certificate signing request config

### Renewal

**Manual renewal required** - 365 days  
**Process**: Re-run `setup-traefik-tls.sh generate` before expiration

---

## 5. AUTHENTICATION CONFIGURATION

### ArgoCD

**Location**: [scripts/bootstrap-argocd.sh](scripts/bootstrap-argocd.sh)  
**Admin User**: `admin`  
**Initial Password**: Auto-generated and stored in:
```
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

**Retrieval Command**:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
```

**Note**: Script displays password during bootstrap:
```
Password: <auto-generated-password>
```

### GitLab

**Location**: [argocd/helm/gitlab/values.yaml](argocd/helm/gitlab/values.yaml)  
**Initial Root Password**:
```yaml
initialRootPassword:
  secret: gitlab-initial-root-password
```

**Storage**: Kubernetes secret in `gitlab` namespace  
**Key**: TBD (stored as sealed secret)  
**Access**: `https://gitlab.homelab.local`

### Open WebUI

**Location**: [helm/open-webui/values.yaml](helm/open-webui/values.yaml)  
**Authentication**: Enabled by default
```yaml
ENABLE_AUTH: "true"
ENABLE_SIGNUP: "false"
```

**Admin Credentials**:
```yaml
WEBUI_ADMIN_EMAIL: <from secret webui-secret>
WEBUI_ADMIN_PASSWORD: <from secret webui-secret>
WEBUI_ADMIN_NAME: "Administrator"
```

**Secret Storage**: `webui-secret` in `ai-services` namespace

### LiteLLM

**Location**: [helm/litellm/values.yaml](helm/litellm/values.yaml)  
**Master Key**:
```yaml
secrets:
  litellmMasterKey:
    secretName: litellm-secret
    key: master-key
```

**Database URL**: Also from `litellm-secret`

### N8N

**Location**: [helm/n8n/values.yaml](helm/n8n/values.yaml)  
**Basic Auth**:
```yaml
secretEnv:
  N8N_ENCRYPTION_KEY: <from n8n-secret>
  N8N_BASIC_AUTH_USER: <from n8n-secret>
  N8N_BASIC_AUTH_PASSWORD: <from n8n-secret>
```

### Sealed Secrets Controller

**Location**: [argocd/applications/sealed-secrets.yaml](argocd/applications/sealed-secrets.yaml)  
**Namespace**: `kube-system`  
**Version**: 2.16.2  
**Deployment Wave**: -2 (first to deploy)

**Sealing Key Location**: Automatically generated in `kube-system` namespace  
**Usage**: All sensitive credentials stored as SealedSecrets in Git

---

## 6. CURRENT SERVICE DEPLOYMENT STATUS

### Deployment Order (Sync Waves)

```
Wave -2:  SealedSecrets (secret infrastructure)
Wave -1:  Longhorn (storage)
Wave  0:  PostgreSQL, Redis, GPU Operator, GPU Time-Slicing Config (databases + GPU)
Wave  1:  Traefik (ingress infrastructure)
Wave  2:  Kyverno (policy engine)
Wave  3:  Prometheus (monitoring - not in current file list)
Wave  4:  GitLab, Dify (source control + AI platform)
Wave  5:  Ollama (GPU), Ollama (CPU), LiteLLM (inference)
Wave  6:  Open WebUI, N8N, SearXNG (user-facing apps)
Wave  7:  ARC Controller, ARC Runners (CI/CD runners)
```

### Application Deployment Structure

**Root Application**: [argocd/apps/root.yaml](argocd/apps/root.yaml)
- Type: App-of-Apps pattern
- Git source: `https://github.com/tzervas/self-hosted-ai.git` (main branch)
- Path: `argocd/applications/`
- Auto-prune: **Disabled** (to prevent accidental deletion)
- Self-healing: **Enabled**

### Deployed Applications List

[argocd/applications/](argocd/applications/) contains 20 application files:

1. **arc-controller.yaml** (Wave 7) - GitHub Actions Runner Controller
2. **arc-runners-gpu.yaml** (Wave 7) - GPU-accelerated CI/CD runners
3. **arc-runners-standard.yaml** (Wave 7) - Standard CPU runners
4. **dify.yaml** (Wave 4) - AI agent workflow platform
5. **gitlab.yaml** (Wave 4) - GitLab source control
6. **gpu-operator.yaml** (Wave 0) - NVIDIA GPU support
7. **gpu-time-slicing-config.yaml** (Wave 0) - GPU time-slicing
8. **kyverno.yaml** (Wave 2) - Policy enforcement
9. **litellm.yaml** (Wave 5) - LLM API gateway
10. **longhorn.yaml** (Wave -1) - Distributed storage
11. **n8n.yaml** (Wave 6) - Workflow automation
12. **ollama-gpu.yaml** (Wave 5) - GPU-based Ollama (RTX 5080)
13. **ollama.yaml** (Wave 5) - CPU-based Ollama
14. **open-webui.yaml** (Wave 6) - Web UI for models
15. **postgresql.yaml** (Wave 0) - PostgreSQL database
16. **prometheus.yaml** (Wave 2) - Prometheus monitoring
17. **redis.yaml** (Wave 0) - Redis cache
18. **sealed-secrets.yaml** (Wave -2) - Secret encryption
19. **searxng.yaml** (Wave 6) - Metasearch engine
20. **traefik.yaml** (Wave 1) - Traefik ingress controller

### Namespaces

- `argocd` - ArgoCD and root application
- `ai-services` - Core AI services (Open WebUI, LiteLLM, Ollama, SearXNG)
- `gitlab` - GitLab
- `dify` - Dify AI platform
- `automation` - N8N workflow engine
- `monitoring` - Prometheus stack
- `traefik` - Traefik ingress
- `kube-system` - System services (SealedSecrets)
- `arc-systems` - ARC controller
- `arc-runners` - ARC runner pools

### Storage Classes

- **longhorn** - Default distributed storage
- **longhorn-homelab** - Non-GPU nodes (2 replicas)
- **longhorn-gpu-local** - GPU node local storage (strict-local, 1 replica)

---

## 7. RUNNER CONFIGURATION (GitHub Actions)

### ARC (Actions Runner Controller) Setup

**Script**: [scripts/setup-arc-github-app.sh](scripts/setup-arc-github-app.sh)  
**Size**: 226 lines  
**Purpose**: Configure GitHub App for self-hosted runner authentication

### Configuration Steps

**Step 1: Create GitHub App**
- URL: `https://github.com/organizations/{ORG}/settings/apps/new`
- App Name: `arc-homelab-runners`
- Homepage URL: `https://github.com/{ORG}`
- Webhook: Disabled

**Required Permissions**:
- **Repository Permissions**:
  - Actions: Read-only
  - Administration: Read & write (required for runners)
  - Checks: Read-only
  - Metadata: Read-only

- **Organization Permissions**:
  - Self-hosted runners: Read & write

**Step 2: Generate Private Key**
- Download .pem file from app settings
- Store securely (deleted after verification)

**Step 3: Install App**
- Install in organization
- Choose "All repositories" or specific repos
- Note installation ID from URL

**Step 4: Create Runner Groups**
- `homelab-runners` - Standard workloads
- `homelab-gpu-runners` - GPU workloads

**Step 5: Create Kubernetes Secret**
```bash
kubectl create secret generic github-app-secret \
  --namespace=arc-runners \
  --from-literal=github_app_id="<APP_ID>" \
  --from-literal=github_app_installation_id="<INSTALLATION_ID>" \
  --from-literal=github_app_private_key="<PRIVATE_KEY>"
```

### ARC Deployment Configuration

#### ARC Controller

**File**: [argocd/applications/arc-controller.yaml](argocd/applications/arc-controller.yaml)  
**Chart**: `gha-runner-scale-set-controller`  
**Version**: 0.9.3  
**Namespace**: `arc-systems`  
**Wave**: 7 (CI/CD tier)

**Resources**:
```yaml
replicaCount: 1
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

**Metrics**:
```yaml
metrics:
  controllerManagerAddr: ":8080"
  listenerAddr: ":8080"
  listenerEndpoint: "/metrics"
```

#### Standard CPU Runners

**File**: [argocd/applications/arc-runners-standard.yaml](argocd/applications/arc-runners-standard.yaml)  
**Chart**: `gha-runner-scale-set`  
**Version**: 0.9.3  
**Namespace**: `arc-runners`  
**Wave**: 7

**Configuration**:
```yaml
githubConfigUrl: "https://github.com/tzervas"  # Replace with org
githubConfigSecret: github-app-secret
runnerGroup: "homelab-runners"
minRunners: 1
maxRunners: 10

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 4000m
    memory: 8Gi

nodeSelector:
  kubernetes.io/hostname: homelab  # Run on main server
```

#### GPU Runners

**File**: [argocd/applications/arc-runners-gpu.yaml](argocd/applications/arc-runners-gpu.yaml)  
**Chart**: `gha-runner-scale-set`  
**Version**: 0.9.3  
**Namespace**: `arc-runners`  
**Wave**: 7

**Configuration**:
```yaml
githubConfigUrl: "https://github.com/tzervas"  # Replace with org
githubConfigSecret: github-app-secret
runnerGroup: "homelab-gpu-runners"
minRunners: 0
maxRunners: 2

resources:
  requests:
    cpu: 1000m
    memory: 4Gi
    nvidia.com/gpu: "1"
  limits:
    cpu: 8000m
    memory: 32Gi
    nvidia.com/gpu: "1"

nodeSelector:
  kubernetes.io/hostname: akula-prime
  nvidia.com/gpu.present: "true"

tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

### Runner Registration

**Workflow Labels**:
```yaml
# Standard runners
runs-on: [self-hosted, linux, homelab-runners]

# GPU runners
runs-on: [self-hosted, linux, homelab-gpu-runners]
```

### Running ARC Setup

```bash
./scripts/setup-arc-github-app.sh --org <YOUR_ORG_NAME>
```

**Prerequisites**:
- `gh` CLI installed and authenticated
- `kubectl` configured
- Access to GitHub organization settings

### Current ARC Status

❓ **Not yet deployed** - requires manual GitHub App setup  
✅ **Helm charts configured** - ready for deployment via ArgoCD  
❓ **Runner groups** - need to be created via GitHub API

---

## 8. HARDWARE & NODE CONFIGURATION

### Node Topology

| Node | Hostname | Role | CPU | RAM | GPU | Storage |
|------|----------|------|-----|-----|-----|---------|
| Server | homelab | Control + Worker | Intel (unspecified) | 120GB | None | Longhorn |
| GPU Worker | akula-prime | Worker | Intel (unspecified) | Unspecified | NVIDIA RTX 5080 (16GB) | Longhorn (GPU-local) |

### GPU Configuration

**Model**: NVIDIA RTX 5080 Blackwell  
**VRAM**: 16GB GDDR7  
**Time-Slicing**: Enabled (4 concurrent workloads)  
**Node**: akula-prime  
**Taints**: `nvidia.com/gpu=true:NoSchedule`

**GPU Operator**:
- Chart: `nvidia/gpu-operator`
- Version: v25.10.1
- Driver: Enabled
- Toolkit: Enabled with containerd config for k3s
- Device Plugin: Enabled
- DCGM Exporter: Enabled
- MIG: Disabled (not supported on RTX 5080)

### Storage

**Longhorn** (distributed block storage):
- Chart: `longhorn/longhorn`
- Version: 1.7.2
- Deployment: Homelab storage via btrfs subvolume at `/var/lib/longhorn`

**Mount Options**:
```
subvol=@longhorn,noatime,compress=zstd:1,space_cache=v2,discard=async
```

**Storage Classes**:
1. **longhorn-homelab** - 2 replicas (non-GPU nodes)
2. **longhorn-gpu-local** - 1 replica strict-local (GPU node only)

**Snapshots**: Recurring daily/weekly backup jobs

**Default Settings**:
- Default replicas: 2
- Data locality: best-effort
- Auto-delete pods on volume detach: Enabled
- Node drain policy: block-for-eviction

---

## 9. ENVIRONMENT VARIABLES & CONFIGURATION

### .env File Location
[.env](.env)

### Key Environment Variables

**Cluster Configuration**:
```bash
DATA_PATH=/data
GPU_WORKER_HOST=192.168.1.99
```

**Web UI**:
```bash
WEBUI_PORT=3001
WEBUI_SECRET_KEY=super_secret_key_2026_replace_with_real
WEBUI_NAME=Self-Hosted AI Server
ENABLE_SIGNUP=true
ENABLE_COMMUNITY_SHARING=false
```

**Search & RAG**:
```bash
ENABLE_RAG_WEB_SEARCH=true
RAG_WEB_SEARCH_ENGINE=searxng
SEARXNG_QUERY_URL=http://searxng:8080/search?q=<query>&format=json
```

**Image Generation**:
```bash
ENABLE_IMAGE_GENERATION=true
IMAGE_GENERATION_ENGINE=auto
COMFYUI_BASE_URL=http://192.168.1.99:8188
AUTOMATIC1111_BASE_URL=http://192.168.1.99:7860
```

**Code Execution**:
```bash
ENABLE_CODE_EXECUTION=true
CODE_EXECUTION_ENGINE=gvisor
CODE_EXECUTION_API_URL=http://code-executor:8080
```

**Ollama Configuration**:
```bash
OLLAMA_PORT=11434
OLLAMA_CPU_NUM_PARALLEL=8
OLLAMA_CPU_MAX_LOADED_MODELS=4
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=30m
OLLAMA_GPU_LAYERS=99
OLLAMA_FLASH_ATTENTION=1
OLLAMA_HOST=0.0.0.0
```

**ComfyUI Configuration**:
```bash
COMFYUI_PORT=8188
COMFYUI_CLI_ARGS=--listen 0.0.0.0 --preview-method auto
COMFYUI_WEB_USER=admin
```

---

## 10. AI MODELS & INFERENCE CONFIGURATION

### GPU Worker Models (RTX 5080 16GB)

**Ollama GPU** ([argocd/helm/ollama/values.yaml](argocd/helm/ollama/values.yaml)):

**Text Generation**:
- `qwen2.5-coder:14b` - Primary coding model
- `deepseek-coder-v2:16b` - Advanced coding
- `codellama:13b` - Code completion
- `phi4:latest` - Reasoning & math
- `llama3.1:8b` - General reasoning
- `mistral:7b-instruct-v0.3` - Function calling

**Vision Models**:
- `llava:13b` - Image understanding & OCR
- `bakllava:latest` - Advanced image analysis

**Embeddings**:
- `nomic-embed-text` - Semantic search & RAG

**Resource Allocation**:
```yaml
requests:
  memory: 8Gi
  cpu: 2
  nvidia.com/gpu: "1"
limits:
  memory: 14Gi
  cpu: 4
  nvidia.com/gpu: "1"
```

### CPU Server Models (120GB RAM)

**Ollama CPU** ([helm/ollama/values.yaml](helm/ollama/values.yaml)) - note: this is actually in [helm/server/values.yaml](helm/server/values.yaml)):

**Fast Models**:
- `mistral:7b` - Fast general chat
- `phi3:latest` - Lightweight tasks
- `gemma2:2b` - Ultra-fast testing

**Embeddings**:
- `nomic-embed-text:latest` - Primary
- `mxbai-embed-large:latest` - High-quality
- `nomic-embed-text:137m-v1.5-q8_0` - Fast code embeddings

**Specialized**:
- `sqlcoder:15b` - SQL generation
- `llama3.1:8b-instruct-q8_0` - Document analysis
- `deepseek-math:7b` - Mathematical reasoning
- `qwen2.5:7b` - Long context (128k tokens)

**Resource Allocation**:
```yaml
requests:
  cpu: 500m
  memory: 2Gi
limits:
  cpu: 8000m
  memory: 32Gi
```

### LiteLLM Configuration

**File**: [helm/litellm/values.yaml](helm/litellm/values.yaml)

**Port**: 4000 (HTTP)  
**Metrics Port**: 9090 (Prometheus)

**Backend URLs**:
```bash
OLLAMA_GPU_URL: "http://gpu-worker-ollama.gpu-worker:11434"
OLLAMA_CPU_URL: "http://ollama.ollama:11434"
REDIS_HOST: "redis-master.self-hosted-ai"
REDIS_PORT: "6379"
```

**Configuration**:
- Database: Disabled (Prisma query engine issues)
- Spend logs: Disabled
- Model storage in DB: Disabled

### Model Resource Limits

**GPU Worker Ollama**:
```yaml
gpu:
  enabled: true
  type: 'nvidia'
  number: 1  # 1 of 4 time-sliced replicas
```

**Persistence**: 150Gi volume for models (Longhorn GPU-local)

---

## 11. DEPLOYMENT PROCEDURE SUMMARY

### Prerequisites Checklist

- ✅ k3s cluster (implied by kubeconfig)
- ✅ kubectl configured
- ✅ Helm v3.x installed
- ✅ Domain: `homelab.local`
- ✅ IP assignments: 192.168.1.170 (homelab), 192.168.1.99 (akula-prime)
- ⚠️ Longhorn storage configured (btrfs subvolume)
- ⚠️ NVIDIA drivers on GPU node
- ⚠️ GitHub App created (for ARC)

### Deployment Steps

**Step 1: Generate TLS Certificates**
```bash
./scripts/setup-traefik-tls.sh generate
# Generates: /data/traefik/certs/{cert.pem, key.pem}
```

**Step 2: Bootstrap ArgoCD**
```bash
./scripts/bootstrap-argocd.sh
# Installs:
#   - ArgoCD 7.7.7
#   - SealedSecrets controller
#   - Root Application
# Outputs: Admin password for argocd.homelab.local
```

**Step 3: Configure GitHub App for ARC** (Optional)
```bash
./scripts/setup-arc-github-app.sh --org <YOUR_ORG>
# Creates GitHub App and Kubernetes secret
```

**Step 4: Monitor Deployment**
```bash
kubectl get applications -n argocd
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Access: http://localhost:8080 (admin/<password>)
```

### Troubleshooting References

**Certificate Issues**:
- Trust certificate on client machines (see Section 4)
- Verify Traefik pod logs: `kubectl logs -n traefik deploy/traefik`

**ArgoCD Issues**:
- Check: `kubectl get applications -n argocd`
- Logs: `kubectl logs -n argocd deploy/argocd-server`

**Service Connectivity**:
- Check ingress: `kubectl get ingress -A`
- Check services: `kubectl get svc -A`
- Traefik routes: `kubectl logs -n traefik deploy/traefik`

---

## 12. KEY FILES REFERENCE

### Configuration Files
- [config/traefik/dynamic.yml](config/traefik/dynamic.yml) - Traefik routing config
- [.env](.env) - Environment variables

### Helm Values
- [argocd/helm/gitlab/values.yaml](argocd/helm/gitlab/values.yaml) - GitLab
- [argocd/helm/prometheus/values.yaml](argocd/helm/prometheus/values.yaml) - Prometheus
- [argocd/helm/ollama/values.yaml](argocd/helm/ollama/values.yaml) - GPU Ollama
- [argocd/helm/dify/values.yaml](argocd/helm/dify/values.yaml) - Dify AI platform
- [helm/open-webui/values.yaml](helm/open-webui/values.yaml) - Open WebUI
- [helm/litellm/values.yaml](helm/litellm/values.yaml) - LiteLLM API
- [helm/n8n/values.yaml](helm/n8n/values.yaml) - N8N automation
- [helm/searxng/values.yaml](helm/searxng/values.yaml) - SearXNG search
- [helm/server/values.yaml](helm/server/values.yaml) - Composite server config

### ArgoCD Applications
- [argocd/apps/root.yaml](argocd/apps/root.yaml) - Root App-of-Apps
- [argocd/applications/](argocd/applications/) - 20 application manifests

### Bootstrap Scripts
- [scripts/bootstrap-argocd.sh](scripts/bootstrap-argocd.sh) - ArgoCD bootstrap
- [scripts/bootstrap.sh](scripts/bootstrap.sh) - Initial setup
- [scripts/setup-traefik-tls.sh](scripts/setup-traefik-tls.sh) - TLS cert generation
- [scripts/setup-arc-github-app.sh](scripts/setup-arc-github-app.sh) - ARC configuration

### Documentation
- [README.md](README.md) - Project overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md) - Production capabilities
- [implementation-guide.md](implementation-guide.md) - Implementation details

---

## 13. ACTIONABLE INSIGHTS & NEXT STEPS

### Current Cluster State

**Fully Configured**:
- ✅ Traefik with dynamic routing
- ✅ Self-signed TLS certificates
- ✅ ArgoCD bootstrap script ready
- ✅ 20 applications defined with sync waves
- ✅ SealedSecrets for encrypted storage
- ✅ Comprehensive monitoring stack
- ✅ Multi-model AI inference (CPU + GPU)

**Ready for Deployment**:
- ⚠️ TLS certificates (require generation)
- ⚠️ ArgoCD bootstrap (requires execution)
- ⚠️ GitHub App (requires manual creation for ARC)
- ⚠️ Longhorn storage backend (may need verification)

**Manual Requirements**:
- 🔧 Domain registration/DNS for `homelab.local`
- 🔧 Trust self-signed certificates on client machines
- 🔧 Create GitHub App for runner authentication
- 🔧 Verify Longhorn storage class availability

### Quick Start Commands

```bash
# 1. Generate certificates
export DOMAIN=homelab.local
export SERVER_HOST=192.168.1.170
export GPU_WORKER_HOST=192.168.1.99
./scripts/setup-traefik-tls.sh generate

# 2. Bootstrap ArgoCD
./scripts/bootstrap-argocd.sh

# 3. Monitor deployment (in separate terminal)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# 4. Watch application sync
watch kubectl get applications -n argocd

# 5. Configure GitHub App (when ready for runners)
./scripts/setup-arc-github-app.sh --org YOUR_ORG_NAME
```

### Critical Configuration Points

1. **Domain**: All services expect `homelab.local` - change via `$DOMAIN` env var
2. **IPs**: Update 192.168.1.170 and 192.168.1.99 if using different network
3. **Storage**: Ensure Longhorn storage classes available before deployment
4. **GPU**: RTX 5080 specific - adjust if using different hardware
5. **Models**: Update Ollama model lists in helm/values.yaml as needed

---

## Document Metadata

**Last Updated**: January 15, 2026  
**Cluster Version**: k3s (implied)  
**ArgoCD Version**: 7.7.7  
**Traefik Version**: v3.6.6  
**Ollama Version**: 0.5.4 (CPU), 0.5.4 (GPU)  
**Kubernetes**: API v1  
**Helm**: v3.x required  

---

**End of Comprehensive Context Findings**
