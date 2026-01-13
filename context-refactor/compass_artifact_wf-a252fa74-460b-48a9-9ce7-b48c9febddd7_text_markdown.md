# Self-Hosted Development Platform on k3s with ArgoCD

A complete, production-ready self-hosted development platform deploying GitLab, multi-architecture CI runners, AI stack (Ollama/Dify), and workflow automation via ArgoCD GitOps on k3s. This configuration targets a **homelab environment with an RTX 5080 GPU (16GB VRAM)** and limited RAM, enabling spec-driven development workflows with LLM-powered code review and generation.

The platform integrates GitLab for source control and CI/CD, Ollama for local LLM inference with GPU time-slicing, Dify for multi-agentic workflows, and ArgoCD for GitOps-based deployment orchestration. All components use sync waves to ensure proper dependency ordering: GPU Operator → Storage → Databases → GitLab → Runners → AI Stack.

---

## Helm repositories and current versions

All components are deployed via Helm charts from official repositories. The following table summarizes the chart sources and versions as of January 2025:

| Component | Repository URL | Chart Name | Version | Notes |
|-----------|---------------|------------|---------|-------|
| **GitLab** | `https://charts.gitlab.io` | `gitlab/gitlab` | 8.7.x | Maps to GitLab 17.7.x |
| **GitLab Runner** | `https://charts.gitlab.io` | `gitlab/gitlab-runner` | 0.84.x | Runner 17.x |
| **ArgoCD** | `https://argoproj.github.io/argo-helm` | `argo/argo-cd` | 7.7.x | Latest stable |
| **Ollama** | `https://helm.otwld.com` | `ollama` | 0.24.x | GPU-enabled |
| **Dify** | `https://borispolonsky.github.io/dify-helm` | `dify/dify` | 0.33.x | App v1.10.1 |
| **NVIDIA GPU Operator** | `https://helm.ngc.nvidia.com/nvidia` | `nvidia/gpu-operator` | 25.10.x | Time-slicing support |
| **Longhorn** | `https://charts.longhorn.io` | `longhorn/longhorn` | 1.7.x | Replicated storage |
| **cert-manager** | `https://charts.jetstack.io` | `jetstack/cert-manager` | 1.17.x | TLS automation |
| **Sealed Secrets** | `https://bitnami-labs.github.io/sealed-secrets` | `sealed-secrets/sealed-secrets` | 2.16.x | Secret encryption |
| **n8n** | `https://8gears.github.io/n8n-helm-chart` | `n8n/n8n` | 1.x | Workflow automation |

```bash
# Add all repositories
helm repo add gitlab https://charts.gitlab.io
helm repo add argo https://argoproj.github.io/argo-helm
helm repo add otwld https://helm.otwld.com
helm repo add dify https://borispolonsky.github.io/dify-helm
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo add longhorn https://charts.longhorn.io
helm repo add jetstack https://charts.jetstack.io
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update
```

---

## k3s installation for GPU workloads

k3s requires specific configuration for GPU support. Install with pre-configured containerd for NVIDIA runtime:

```bash
# Install NVIDIA container toolkit first
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-runtime

# Install k3s server (disable servicelb if using MetalLB)
curl -sfL https://get.k3s.io | sh -s - server \
  --cluster-cidr=10.42.0.0/16 \
  --service-cidr=10.43.0.0/16 \
  --write-kubeconfig-mode 644

# For GPU worker nodes (if multi-node)
curl -sfL https://get.k3s.io | sh -s - agent \
  -s https://<server-ip>:6443 \
  --token <token> \
  --node-label nvidia.com/gpu=true \
  --node-taint nvidia.com/gpu=true:NoSchedule
```

---

## GitLab Helm chart configuration

The following minimal configuration deploys GitLab on a **16GB RAM k3s node** using Traefik ingress (k3s default) with resource limits tuned for constrained environments.

```yaml
# apps/gitlab/values.yaml
# GitLab Helm Chart - Minimal k3s Configuration for 16GB Node

global:
  hosts:
    domain: gitlab.homelab.local
    https: true
  
  ingress:
    class: traefik
    configureCertmanager: true
    provider: traefik
  
  # Disable unnecessary components
  kas:
    enabled: false
  pages:
    enabled: false
  
  # Use bundled MinIO for object storage
  minio:
    enabled: true
  
  edition: ce
  time_zone: UTC

# Disable bundled NGINX - use k3s Traefik
nginx-ingress:
  enabled: false

# cert-manager for TLS
certmanager:
  install: true
certmanager-issuer:
  email: admin@homelab.local

# Disable Prometheus - use external if needed
prometheus:
  install: false

# Deploy Runner separately for better control
gitlab-runner:
  install: false

# Container Registry
registry:
  enabled: true
  hpa:
    minReplicas: 1
    maxReplicas: 1
  resources:
    requests:
      cpu: 50m
      memory: 32Mi
    limits:
      memory: 256Mi

# PostgreSQL (Bitnami) - Internal
postgresql:
  install: true
  primary:
    persistence:
      enabled: true
      size: 8Gi
      storageClass: longhorn
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        memory: 1Gi

# Redis (Bitnami) - Internal
redis:
  install: true
  master:
    persistence:
      enabled: true
      size: 5Gi
      storageClass: longhorn
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        memory: 256Mi

# MinIO for object storage
minio:
  persistence:
    enabled: true
    size: 20Gi
    storageClass: longhorn
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      memory: 512Mi

# GitLab Components
gitlab:
  webservice:
    minReplicas: 1
    maxReplicas: 1
    workerProcesses: 2
    resources:
      requests:
        cpu: 300m
        memory: 2.5Gi
      limits:
        memory: 3Gi
    workhorse:
      resources:
        requests:
          cpu: 100m
          memory: 100Mi
        limits:
          memory: 200Mi
  
  sidekiq:
    minReplicas: 1
    maxReplicas: 1
    concurrency: 10
    resources:
      requests:
        cpu: 100m
        memory: 1.5Gi
      limits:
        memory: 2Gi
  
  gitaly:
    resources:
      requests:
        cpu: 100m
        memory: 300Mi
      limits:
        memory: 1Gi
    persistence:
      enabled: true
      size: 50Gi
      storageClass: longhorn
  
  gitlab-shell:
    minReplicas: 1
    maxReplicas: 1
    resources:
      requests:
        cpu: 0
        memory: 6Mi
      limits:
        memory: 20Mi
  
  toolbox:
    resources:
      requests:
        cpu: 50m
        memory: 350Mi
      limits:
        memory: 1Gi
  
  # Disable optional components
  gitlab-pages:
    enabled: false
  spamcheck:
    enabled: false
  praefect:
    enabled: false
  mailroom:
    enabled: false
```

---

## GitLab Runner with multi-architecture support

GitLab 16+ uses **authentication tokens** (prefix `glrt-`) instead of deprecated registration tokens. Create runners in GitLab UI first, then use the token in Helm configuration.

```yaml
# apps/gitlab-runner/values.yaml
# GitLab Runner - Kubernetes Executor with Multi-Arch Build Support

gitlabUrl: "https://gitlab.homelab.local/"

# Authentication token from GitLab UI (glrt-xxx format)
# Create via: Admin Area → CI/CD → Runners → New Runner
runners:
  secret: gitlab-runner-secret

unregisterRunners: true
concurrent: 10
checkInterval: 30
logLevel: "info"

metrics:
  enabled: true
  port: 9252

rbac:
  create: true
  clusterWideAccess: false

serviceAccount:
  create: true
  name: gitlab-runner-sa

securityContext:
  fsGroup: 65533
  runAsUser: 100

resources:
  limits:
    memory: 256Mi
    cpu: 500m
  requests:
    memory: 128Mi
    cpu: 100m

# Kubernetes executor configuration
runners:
  config: |
    [[runners]]
      executor = "kubernetes"
      
      [runners.kubernetes]
        namespace = "{{.Release.Namespace}}"
        image = "ubuntu:22.04"
        privileged = true  # Required for Docker-in-Docker/buildx
        
        poll_interval = 3
        poll_timeout = 3600
        
        # Build container resources
        cpu_request = "500m"
        cpu_limit = "2"
        memory_request = "1Gi"
        memory_limit = "4Gi"
        cpu_limit_overwrite_max_allowed = "4"
        memory_limit_overwrite_max_allowed = "8Gi"
        
        # Helper container
        helper_cpu_request = "100m"
        helper_cpu_limit = "500m"
        helper_memory_request = "128Mi"
        helper_memory_limit = "256Mi"
        helper_image_flavor = "alpine"
        
        # Allow architecture-based node selection
        node_selector_overwrite_allowed = "kubernetes.io/arch=.*"
        
        [runners.kubernetes.node_selector]
          "kubernetes.io/os" = "linux"
        
        [runners.kubernetes.pod_security_context]
          fs_group = 65533
          run_as_user = 1000
          run_as_group = 1000
        
        # Volumes for Docker-in-Docker
        [[runners.kubernetes.volumes.empty_dir]]
          name = "docker-certs"
          mount_path = "/certs/client"
          medium = "Memory"
        
        [[runners.kubernetes.volumes.empty_dir]]
          name = "builds"
          mount_path = "/builds"
      
      # S3/MinIO cache for distributed builds
      [runners.cache]
        Type = "s3"
        Path = "runner"
        Shared = true
        [runners.cache.s3]
          ServerAddress = "gitlab-minio.gitlab.svc.cluster.local:9000"
          BucketName = "gitlab-runner-cache"
          BucketLocation = "us-east-1"
          Insecure = true
          AuthenticationType = "access-key"
  
  cache:
    secretName: minio-cache-credentials
```

---

## NVIDIA GPU Operator with time-slicing

RTX 5080 does not support MIG (Multi-Instance GPU), so we use **time-slicing** to share the GPU between Ollama and CI jobs. This configuration creates **4 virtual GPU replicas** from a single physical GPU.

```yaml
# apps/gpu-operator/values.yaml
# NVIDIA GPU Operator for k3s with Time-Slicing

driver:
  enabled: false  # Use pre-installed drivers

toolkit:
  enabled: true
  env:
    - name: CONTAINERD_SOCKET
      value: /run/k3s/containerd/containerd.sock
    - name: CONTAINERD_CONFIG
      value: /var/lib/rancher/k3s/agent/etc/containerd/config.toml
    - name: CONTAINERD_RUNTIME_CLASS
      value: nvidia
    - name: CONTAINERD_SET_AS_DEFAULT
      value: "true"

devicePlugin:
  enabled: true
  config:
    name: "time-slicing-config"
    default: "rtx-5080"

dcgmExporter:
  enabled: true

gfd:
  enabled: true

migManager:
  enabled: false  # Not supported on RTX 5080

validator:
  enabled: true

cdi:
  enabled: true
  default: true
```

**Time-slicing ConfigMap** (creates 4 GPU replicas from single RTX 5080):

```yaml
# apps/gpu-operator/time-slicing-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
  namespace: gpu-operator
data:
  rtx-5080: |-
    version: v1
    flags:
      migStrategy: none
    sharing:
      timeSlicing:
        renameByDefault: false
        failRequestsGreaterThanOne: false
        resources:
          - name: nvidia.com/gpu
            replicas: 4
```

---

## Ollama configuration with GPU sharing

```yaml
# apps/ollama/values.yaml
# Ollama Helm Chart with GPU Time-Slicing

replicaCount: 1

image:
  repository: ollama/ollama
  pullPolicy: IfNotPresent

ollama:
  gpu:
    enabled: true
    type: 'nvidia'
    number: 1  # Request 1 time-sliced replica

  # Model preloading
  models:
    pull:
      - llama3.2:8b
      - codellama:13b
      - nomic-embed-text
    run:
      - llama3.2:8b
    create:
      - name: coding-assistant
        template: |
          FROM llama3.2:8b
          PARAMETER num_ctx 32768
          PARAMETER temperature 0.3
          SYSTEM """You are an expert software engineer..."""

persistentVolume:
  enabled: true
  accessModes:
    - ReadWriteOnce
  size: 200Gi
  storageClass: longhorn

resources:
  requests:
    memory: "8Gi"
    cpu: "2"
    nvidia.com/gpu: "1"
  limits:
    memory: "16Gi"
    cpu: "4"
    nvidia.com/gpu: "1"

service:
  type: ClusterIP
  port: 11434

ingress:
  enabled: true
  className: "traefik"
  hosts:
    - host: ollama.homelab.local
      paths:
        - path: /
          pathType: Prefix

livenessProbe:
  enabled: true
  path: /
  initialDelaySeconds: 60
  periodSeconds: 10

runtimeClassName: nvidia

extraEnv:
  - name: OLLAMA_HOST
    value: "0.0.0.0:11434"
  - name: OLLAMA_NUM_PARALLEL
    value: "2"
  - name: OLLAMA_MAX_LOADED_MODELS
    value: "2"
  - name: OLLAMA_KEEP_ALIVE
    value: "5m"
```

---

## Dify Helm configuration

```yaml
# apps/dify/values.yaml
# Dify Helm Chart with Ollama Integration

global:
  storageClass: longhorn

api:
  enabled: true
  replicaCount: 1
  image:
    repository: langgenius/dify-api
    tag: "1.10.1"
  resources:
    requests:
      memory: "2Gi"
      cpu: "1"
    limits:
      memory: "4Gi"
      cpu: "2"
  env:
    OLLAMA_BASE_URL: "http://ollama.ollama.svc.cluster.local:11434"

web:
  enabled: true
  replicaCount: 1
  image:
    repository: langgenius/dify-web
    tag: "1.10.1"
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"

worker:
  enabled: true
  replicaCount: 1
  resources:
    requests:
      memory: "2Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "1"

sandbox:
  enabled: true
  image:
    repository: langgenius/dify-sandbox
    tag: "0.2.12"

postgresql:
  enabled: true
  auth:
    username: dify
    password: dify-password
    database: dify
  primary:
    persistence:
      enabled: true
      size: 20Gi

redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: true
    password: dify-redis
  master:
    persistence:
      enabled: true
      size: 5Gi

weaviate:
  enabled: true
  image:
    tag: "1.27.3"
  persistence:
    enabled: true
    size: 20Gi

storage:
  type: "local"
  local:
    persistence:
      enabled: true
      size: 50Gi

ingress:
  enabled: true
  className: "traefik"
  hosts:
    - host: dify.homelab.local
      paths:
        - path: /
          pathType: Prefix
```

---

## ArgoCD GitOps structure with sync waves

### Root Application (app-of-apps bootstrap)

```yaml
# argocd/bootstrap/root-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dev-platform
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/gitops-platform.git
    targetRevision: main
    path: argocd/applications
    directory:
      recurse: true
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    retry:
      limit: 5
      backoff:
        duration: 5s
        maxDuration: 3m0s
        factor: 2
    syncOptions:
      - CreateNamespace=true
```

### Component Applications with sync waves

```yaml
# argocd/applications/gpu-operator.yaml (Wave 0)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gpu-operator
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "0"
spec:
  project: default
  sources:
    - repoURL: https://helm.ngc.nvidia.com/nvidia
      chart: gpu-operator
      targetRevision: v25.10.1
      helm:
        valueFiles:
          - $values/apps/gpu-operator/values.yaml
    - repoURL: https://github.com/your-org/gitops-platform.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: gpu-operator
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
---
# argocd/applications/longhorn.yaml (Wave 1)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: longhorn
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  project: default
  sources:
    - repoURL: https://charts.longhorn.io
      chart: longhorn
      targetRevision: 1.7.2
      helm:
        valueFiles:
          - $values/apps/longhorn/values.yaml
    - repoURL: https://github.com/your-org/gitops-platform.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: longhorn-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
---
# argocd/applications/sealed-secrets.yaml (Wave 1)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sealed-secrets
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  project: default
  source:
    repoURL: https://bitnami-labs.github.io/sealed-secrets
    chart: sealed-secrets
    targetRevision: 2.16.2
    helm:
      parameters:
        - name: fullnameOverride
          value: sealed-secrets-controller
  destination:
    server: https://kubernetes.default.svc
    namespace: kube-system
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
---
# argocd/applications/gitlab.yaml (Wave 3)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gitlab
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "3"
spec:
  project: default
  sources:
    - repoURL: https://charts.gitlab.io
      chart: gitlab
      targetRevision: 8.7.9
      helm:
        valueFiles:
          - $values/apps/gitlab/values.yaml
    - repoURL: https://github.com/your-org/gitops-platform.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: gitlab
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
---
# argocd/applications/gitlab-runner.yaml (Wave 4)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gitlab-runner
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "4"
spec:
  project: default
  sources:
    - repoURL: https://charts.gitlab.io
      chart: gitlab-runner
      targetRevision: 0.84.1
      helm:
        valueFiles:
          - $values/apps/gitlab-runner/values.yaml
    - repoURL: https://github.com/your-org/gitops-platform.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: gitlab-runner
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
---
# argocd/applications/ollama.yaml (Wave 5)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ollama
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "5"
spec:
  project: default
  sources:
    - repoURL: https://helm.otwld.com
      chart: ollama
      targetRevision: 0.24.0
      helm:
        valueFiles:
          - $values/apps/ollama/values.yaml
    - repoURL: https://github.com/your-org/gitops-platform.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: ollama
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
---
# argocd/applications/dify.yaml (Wave 6)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dify
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "6"
spec:
  project: default
  sources:
    - repoURL: https://borispolonsky.github.io/dify-helm
      chart: dify
      targetRevision: 0.33.0
      helm:
        valueFiles:
          - $values/apps/dify/values.yaml
    - repoURL: https://github.com/your-org/gitops-platform.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: dify
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

---

## Environment variables template

```bash
# .env.example - GitLab Kubernetes Platform Configuration

#------------------------------------------------------------------------------
# CORE GITLAB SETTINGS
#------------------------------------------------------------------------------
GITLAB_EXTERNAL_URL=https://gitlab.homelab.local
GITLAB_ROOT_PASSWORD=                    # Min 8 characters
GITLAB_EDITION=ce                        # ce or ee

#------------------------------------------------------------------------------
# KUBERNETES DEPLOYMENT
#------------------------------------------------------------------------------
GITLAB_NAMESPACE=gitlab
GITLAB_RUNNER_NAMESPACE=gitlab-runner
STORAGE_CLASS=longhorn                   # longhorn or local-path
INGRESS_CLASS=traefik

#------------------------------------------------------------------------------
# DATABASE CONFIGURATION
#------------------------------------------------------------------------------
POSTGRES_HOST=gitlab-postgresql
POSTGRES_PORT=5432
POSTGRES_DATABASE=gitlabhq_production
POSTGRES_USER=gitlab
POSTGRES_PASSWORD=

#------------------------------------------------------------------------------
# REDIS CONFIGURATION
#------------------------------------------------------------------------------
REDIS_HOST=gitlab-redis-master
REDIS_PORT=6379
REDIS_PASSWORD=

#------------------------------------------------------------------------------
# CONTAINER REGISTRY
#------------------------------------------------------------------------------
REGISTRY_ENABLED=true
REGISTRY_EXTERNAL_URL=https://registry.gitlab.homelab.local

#------------------------------------------------------------------------------
# OBJECT STORAGE (MinIO)
#------------------------------------------------------------------------------
MINIO_ENDPOINT=http://gitlab-minio:9000
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
ARTIFACTS_BUCKET=gitlab-artifacts
LFS_BUCKET=gitlab-lfs
UPLOADS_BUCKET=gitlab-uploads
PACKAGES_BUCKET=gitlab-packages
RUNNER_CACHE_BUCKET=gitlab-runner-cache

#------------------------------------------------------------------------------
# GITLAB RUNNER CONFIGURATION
#------------------------------------------------------------------------------
RUNNER_TOKEN=                            # glrt-xxx format from GitLab UI
RUNNER_EXECUTOR=kubernetes
RUNNER_CONCURRENT=10
RUNNER_TAGS=kubernetes,docker,amd64
RUNNER_DEFAULT_IMAGE=ubuntu:22.04

#------------------------------------------------------------------------------
# GITHUB MIRRORING
#------------------------------------------------------------------------------
GITHUB_TOKEN=                            # PAT with repo scope
GITHUB_ORG=

#------------------------------------------------------------------------------
# GPU CONFIGURATION
#------------------------------------------------------------------------------
GPU_TIME_SLICE_REPLICAS=4                # Virtual GPUs from single RTX 5080
GPU_MEMORY_LIMIT=16Gi                    # RTX 5080 VRAM

#------------------------------------------------------------------------------
# AI STACK (OLLAMA/DIFY)
#------------------------------------------------------------------------------
OLLAMA_API_URL=http://ollama.ollama.svc.cluster.local:11434
OLLAMA_DEFAULT_MODEL=llama3.2:8b
OLLAMA_CODING_MODEL=coding-assistant
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_STORAGE_SIZE=200Gi

DIFY_EXTERNAL_URL=https://dify.homelab.local
DIFY_POSTGRES_PASSWORD=
DIFY_REDIS_PASSWORD=

#------------------------------------------------------------------------------
# SECURITY SETTINGS
#------------------------------------------------------------------------------
TLS_CERT_SOURCE=letsencrypt              # letsencrypt, selfsigned, custom
LETSENCRYPT_EMAIL=admin@homelab.local
POD_SECURITY_LEVEL=baseline              # privileged, baseline, restricted

#------------------------------------------------------------------------------
# ARGOCD
#------------------------------------------------------------------------------
ARGOCD_EXTERNAL_URL=https://argocd.homelab.local
ARGOCD_ADMIN_PASSWORD=                   # Generated on install if empty
```

---

## GitLab CI pipeline templates

### Multi-architecture build pipeline

```yaml
# .gitlab-ci.yml - Multi-Architecture Build Pipeline
stages:
  - setup
  - build
  - test
  - review
  - package
  - deploy
  - mirror

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  REGISTRY: ${CI_REGISTRY}
  IMAGE_NAME: ${CI_REGISTRY_IMAGE}
  OLLAMA_HOST: "http://ollama.ollama.svc.cluster.local:11434"

# =============================================================================
# Templates
# =============================================================================

.docker_setup:
  image: docker:24.0.7
  services:
    - docker:24.0.7-dind
  before_script:
    - docker info
    - echo "${CI_REGISTRY_PASSWORD}" | docker login -u "${CI_REGISTRY_USER}" --password-stdin ${CI_REGISTRY}

.qemu_setup:
  extends: .docker_setup
  before_script:
    - !reference [.docker_setup, before_script]
    - docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    - docker buildx create --name multiarch-builder --driver docker-container --bootstrap --use

.build_matrix:
  parallel:
    matrix:
      - ARCH: [amd64, arm64]
        PLATFORM_FLAG: ["linux/amd64", "linux/arm64"]

.cache_per_arch:
  cache:
    key: "${CI_JOB_NAME}-${ARCH}-${CI_COMMIT_REF_SLUG}"
    fallback_keys:
      - "${CI_JOB_NAME}-${ARCH}-${CI_DEFAULT_BRANCH}"
    paths:
      - .cache/
      - target/
      - node_modules/
    policy: pull-push

# =============================================================================
# Setup Stage
# =============================================================================

setup:qemu:
  stage: setup
  extends: .docker_setup
  script:
    - docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    - docker run --rm --privileged tonistiigi/binfmt --install all
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# =============================================================================
# Build Stage
# =============================================================================

build:docker:
  stage: build
  extends:
    - .qemu_setup
    - .build_matrix
  script:
    - |
      docker buildx build \
        --platform ${PLATFORM_FLAG} \
        --cache-from type=registry,ref=${IMAGE_NAME}:cache-${ARCH} \
        --cache-to type=registry,ref=${IMAGE_NAME}:cache-${ARCH},mode=max \
        --tag ${IMAGE_NAME}:${CI_COMMIT_SHA}-${ARCH} \
        --push .
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

build:go-cross:
  stage: build
  image: golang:1.21-alpine
  extends:
    - .build_matrix
    - .cache_per_arch
  variables:
    GOCACHE: "${CI_PROJECT_DIR}/.cache/go-build"
    GOMODCACHE: "${CI_PROJECT_DIR}/.cache/go-mod"
  script:
    - |
      case "${ARCH}" in
        amd64)  GOARCH=amd64 ;;
        arm64)  GOARCH=arm64 ;;
        riscv64) GOARCH=riscv64 ;;
      esac
      CGO_ENABLED=0 GOOS=linux GOARCH=${GOARCH} go build -o app-${ARCH} ./cmd/app
  artifacts:
    paths:
      - app-*
    expire_in: 1 week

build:rust-cross:
  stage: build
  image: rust:1.75
  extends:
    - .build_matrix
    - .cache_per_arch
  before_script:
    - apt-get update && apt-get install -y gcc-aarch64-linux-gnu gcc-riscv64-linux-gnu
    - rustup target add aarch64-unknown-linux-gnu riscv64gc-unknown-linux-gnu || true
  script:
    - |
      case "${ARCH}" in
        amd64)
          cargo build --release
          ;;
        arm64)
          CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc \
          cargo build --release --target aarch64-unknown-linux-gnu
          ;;
        riscv64)
          CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_LINKER=riscv64-linux-gnu-gcc \
          cargo build --release --target riscv64gc-unknown-linux-gnu
          ;;
      esac
  artifacts:
    paths:
      - target/release/
      - target/*/release/
    expire_in: 1 week

# =============================================================================
# Review Stage - LLM-Powered
# =============================================================================

llm-code-review:
  stage: review
  image: curlimages/curl:latest
  variables:
    MODEL: "llama3.2:8b"
  script:
    - |
      DIFF=$(git diff origin/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}...HEAD | head -c 10000)
      REVIEW=$(curl -s -X POST ${OLLAMA_HOST}/api/chat \
        -H "Content-Type: application/json" \
        -d "{
          \"model\": \"${MODEL}\",
          \"messages\": [{
            \"role\": \"user\",
            \"content\": \"Review this code diff for security issues, bugs, and improvements:\\n\\n${DIFF}\"
          }],
          \"stream\": false
        }" | jq -r '.message.content')
      echo "## AI Code Review" > review.md
      echo "" >> review.md
      echo "${REVIEW}" >> review.md
      cat review.md
  artifacts:
    paths:
      - review.md
    expire_in: 1 week
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

validate-specs:
  stage: review
  image: python:3.11-slim
  before_script:
    - pip install yamllint jsonschema pyyaml
  script:
    - yamllint -c .yamllint.yaml specs/
    - python scripts/validate_specs.py specs/*.yaml
  rules:
    - changes:
        - "specs/**/*.yaml"
        - "specs/**/*.yml"

# =============================================================================
# Test Stage
# =============================================================================

test:unit:
  stage: test
  image: python:3.11
  extends: .cache_per_arch
  script:
    - pip install -r requirements.txt
    - pytest tests/ --cov=src --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

test:integration:
  stage: test
  extends:
    - .qemu_setup
    - .build_matrix
  script:
    - |
      docker run --rm --platform ${PLATFORM_FLAG} \
        ${IMAGE_NAME}:${CI_COMMIT_SHA}-${ARCH} \
        /app/run-tests.sh
  needs:
    - job: build:docker

# =============================================================================
# Package Stage
# =============================================================================

package:manifest:
  stage: package
  extends: .qemu_setup
  needs:
    - build:docker
  script:
    - |
      docker buildx imagetools create \
        -t ${IMAGE_NAME}:${CI_COMMIT_SHA} \
        -t ${IMAGE_NAME}:latest \
        ${IMAGE_NAME}:${CI_COMMIT_SHA}-amd64 \
        ${IMAGE_NAME}:${CI_COMMIT_SHA}-arm64
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

package:wheels:
  stage: package
  image: python:3.11
  services:
    - docker:24.0.7-dind
  variables:
    DOCKER_HOST: tcp://docker:2375
    CIBW_ARCHS_LINUX: "x86_64 aarch64"
    CIBW_BUILD: "cp39-* cp310-* cp311-* cp312-*"
  before_script:
    - docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    - pip install cibuildwheel
  script:
    - cibuildwheel --output-dir wheelhouse
  artifacts:
    paths:
      - wheelhouse/
  rules:
    - if: $CI_COMMIT_TAG

# =============================================================================
# Deploy Stage
# =============================================================================

deploy:staging:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/app app=${IMAGE_NAME}:${CI_COMMIT_SHA} -n staging
  environment:
    name: staging
    url: https://staging.homelab.local
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

deploy:production:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/app app=${IMAGE_NAME}:${CI_COMMIT_SHA} -n production
  environment:
    name: production
    url: https://app.homelab.local
  rules:
    - if: $CI_COMMIT_TAG
  when: manual

# =============================================================================
# Mirror Stage - GitHub Push
# =============================================================================

mirror-to-github:
  stage: mirror
  image: alpine/git:latest
  variables:
    GITHUB_REPO: "https://oauth2:${GITHUB_TOKEN}@github.com/${GITHUB_ORG}/${CI_PROJECT_NAME}.git"
  rules:
    - if: '$CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/'
  script:
    - git remote add github $GITHUB_REPO || git remote set-url github $GITHUB_REPO
    - git push github HEAD:refs/heads/main --force
    - git push github --tags
```

---

## Dify workflow templates

### Code review agent workflow

```json
{
  "version": "0.1.0",
  "kind": "workflow",
  "metadata": {
    "name": "code-review-agent",
    "description": "AI-powered code review for merge requests"
  },
  "graph": {
    "nodes": [
      {
        "id": "start",
        "type": "start",
        "data": {
          "variables": [
            {
              "variable": "code_diff",
              "type": "paragraph",
              "required": true,
              "label": "Code Diff"
            },
            {
              "variable": "context",
              "type": "paragraph",
              "required": false,
              "label": "Review Context"
            }
          ]
        }
      },
      {
        "id": "llm_review",
        "type": "llm",
        "data": {
          "model": {
            "provider": "ollama",
            "name": "llama3.2:8b",
            "mode": "chat"
          },
          "prompt_template": [
            {
              "role": "system",
              "text": "You are an expert code reviewer. Analyze code diffs for security vulnerabilities, bugs, performance issues, and best practices violations. Provide structured, actionable feedback."
            },
            {
              "role": "user",
              "text": "Review this code diff:\n\n{{#code_diff#}}\n\nContext: {{#context#}}"
            }
          ],
          "structured_output": {
            "enabled": true,
            "schema": {
              "type": "object",
              "properties": {
                "summary": { "type": "string" },
                "issues": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "properties": {
                      "severity": { "type": "string", "enum": ["critical", "warning", "info"] },
                      "line": { "type": "integer" },
                      "message": { "type": "string" },
                      "suggestion": { "type": "string" }
                    }
                  }
                },
                "approved": { "type": "boolean" }
              }
            }
          }
        }
      },
      {
        "id": "format_output",
        "type": "template",
        "data": {
          "template": "## Code Review Summary\n\n{{ llm_review.summary }}\n\n{% for issue in llm_review.issues %}\n### {{ issue.severity | upper }}: Line {{ issue.line }}\n{{ issue.message }}\n**Suggestion:** {{ issue.suggestion }}\n{% endfor %}\n\n**Approved:** {{ 'Yes ✅' if llm_review.approved else 'No ❌' }}"
        }
      },
      {
        "id": "end",
        "type": "end",
        "data": {
          "outputs": [
            {
              "variable": "review_result",
              "value_selector": ["format_output", "output"]
            }
          ]
        }
      }
    ],
    "edges": [
      { "source": "start", "target": "llm_review" },
      { "source": "llm_review", "target": "format_output" },
      { "source": "format_output", "target": "end" }
    ]
  }
}
```

### Spec-to-code generation workflow

```json
{
  "version": "0.1.0",
  "kind": "workflow",
  "metadata": {
    "name": "spec-to-code-generator",
    "description": "Generate code from specification files"
  },
  "graph": {
    "nodes": [
      {
        "id": "start",
        "type": "start",
        "data": {
          "variables": [
            {
              "variable": "spec_content",
              "type": "paragraph",
              "required": true,
              "label": "Specification YAML"
            },
            {
              "variable": "language",
              "type": "select",
              "required": true,
              "label": "Target Language",
              "options": ["python", "typescript", "go", "rust"]
            }
          ]
        }
      },
      {
        "id": "parse_spec",
        "type": "code",
        "data": {
          "language": "python3",
          "code": "import yaml\nimport json\n\ndef main(spec_content: str) -> dict:\n    spec = yaml.safe_load(spec_content)\n    return {'parsed_spec': json.dumps(spec, indent=2)}"
        }
      },
      {
        "id": "generate_code",
        "type": "llm",
        "data": {
          "model": {
            "provider": "ollama",
            "name": "codellama:13b",
            "mode": "chat"
          },
          "prompt_template": [
            {
              "role": "system",
              "text": "You are an expert software engineer. Generate production-ready code from specifications. Include proper error handling, type hints, and documentation."
            },
            {
              "role": "user",
              "text": "Generate {{#language#}} code from this specification:\n\n{{#parse_spec.parsed_spec#}}\n\nInclude:\n1. Data models/types\n2. Implementation\n3. Unit tests\n4. Documentation"
            }
          ]
        }
      },
      {
        "id": "end",
        "type": "end",
        "data": {
          "outputs": [
            {
              "variable": "generated_code",
              "value_selector": ["generate_code", "text"]
            }
          ]
        }
      }
    ],
    "edges": [
      { "source": "start", "target": "parse_spec" },
      { "source": "parse_spec", "target": "generate_code" },
      { "source": "generate_code", "target": "end" }
    ]
  }
}
```

---

## Ollama Modelfile examples

### Coding assistant

```dockerfile
# Modelfile.coding-assistant
FROM llama3.2:8b

PARAMETER num_ctx 32768
PARAMETER temperature 0.3
PARAMETER repeat_penalty 1.1
PARAMETER top_p 0.9

SYSTEM """
You are an expert software engineer and coding assistant.

## Core Capabilities
- Write clean, maintainable, well-documented code
- Follow language-specific best practices and idioms
- Implement proper error handling and edge cases
- Write comprehensive tests alongside code
- Provide clear explanations of implementation decisions

## Coding Standards
- Use meaningful variable and function names
- Keep functions small and focused (single responsibility)
- Add inline comments for complex logic
- Include type hints/annotations where applicable
- Follow DRY (Don't Repeat Yourself) principles

## Response Format
When asked to write code:
1. First understand the requirements completely
2. Ask clarifying questions if needed
3. Provide the implementation with clear structure
4. Include usage examples
5. Suggest potential improvements

## Languages & Frameworks
Proficient in: Python, TypeScript, Go, Rust, Java,
Kubernetes (YAML), Terraform, Helm, GitLab CI/CD,
Docker, and shell scripting.

Always prioritize security, performance, and maintainability.
"""
```

### DevOps specialist

```dockerfile
# Modelfile.devops-specialist
FROM mistral:7b

PARAMETER num_ctx 16384
PARAMETER temperature 0.4

SYSTEM """
You are a senior DevOps engineer and Kubernetes specialist.

## Core Expertise
- Kubernetes architecture and best practices
- Helm chart development
- GitOps workflows (ArgoCD, Flux)
- CI/CD pipeline design (GitLab CI, GitHub Actions)
- Infrastructure as Code (Terraform, Pulumi)
- Container security and hardening
- Observability (Prometheus, Grafana, Loki)

## YAML/Manifest Standards
When generating Kubernetes manifests:
- Always include resource limits and requests
- Use pod security contexts (runAsNonRoot, drop ALL capabilities)
- Include health checks (liveness, readiness probes)
- Add appropriate labels and annotations
- Consider network policies for isolation

## Security First
- Never suggest running containers as root unless necessary
- Recommend secrets management (Sealed Secrets, External Secrets)
- Suggest RBAC with least-privilege principle
- Include network policies for pod isolation
- Recommend pod security standards (baseline/restricted)
"""
```

---

## Network policy manifests

```yaml
# infrastructure/network-policies/gitlab-namespace.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: gitlab
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-gitlab-internal
  namespace: gitlab
spec:
  podSelector:
    matchLabels:
      app: gitlab
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: gitlab
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: gitlab
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
---
# infrastructure/network-policies/gitlab-runner.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: gitlab-runner-isolation
  namespace: gitlab-runner
spec:
  podSelector:
    matchLabels:
      app: gitlab-runner
  policyTypes:
    - Ingress
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: gitlab
          podSelector:
            matchLabels:
              app: webservice
      ports:
        - protocol: TCP
          port: 8181
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
    - to:
        - namespaceSelector:
            matchLabels:
              name: gitlab
          podSelector:
            matchLabels:
              app: registry
      ports:
        - protocol: TCP
          port: 5000
  ingress: []
```

---

## Storage class and PVC definitions

```yaml
# infrastructure/storage/longhorn-storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: driver.longhorn.io
allowVolumeExpansion: true
reclaimPolicy: Delete
volumeBindingMode: Immediate
parameters:
  numberOfReplicas: "2"
  staleReplicaTimeout: "2880"
  fromBackup: ""
---
# infrastructure/storage/longhorn-ssd.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-ssd
provisioner: driver.longhorn.io
allowVolumeExpansion: true
reclaimPolicy: Retain
volumeBindingMode: Immediate
parameters:
  numberOfReplicas: "2"
  diskSelector: "ssd"
  nodeSelector: "storage"
---
# infrastructure/storage/ollama-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ollama-models
  namespace: ollama
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 200Gi
```

---

## Bootstrap job manifests

```yaml
# infrastructure/bootstrap/gitlab-init-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: gitlab-post-install
  namespace: gitlab
  annotations:
    helm.sh/hook: post-install,post-upgrade
    helm.sh/hook-weight: "5"
    helm.sh/hook-delete-policy: hook-succeeded
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: OnFailure
      serviceAccountName: gitlab-admin-setup
      containers:
        - name: admin-setup
          image: registry.gitlab.com/gitlab-org/build/cng/gitlab-toolbox:v17.7.7
          env:
            - name: GITLAB_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: gitlab-secrets
                  key: root-password
          command:
            - /bin/bash
            - -c
            - |
              set -e
              echo "Waiting for GitLab to be ready..."
              until curl -sf http://gitlab-webservice:8181/-/readiness; do
                sleep 10
              done
              
              echo "GitLab is ready. Creating automation resources..."
              
              # Create personal access token for automation
              gitlab-rails runner "
                user = User.find_by_username('root')
                token = user.personal_access_tokens.create!(
                  name: 'automation-token',
                  scopes: ['api', 'read_repository', 'write_repository'],
                  expires_at: 1.year.from_now
                )
                File.write('/tmp/admin-token', token.token)
              "
              
              echo "Setup complete!"
---
# infrastructure/bootstrap/runner-token-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: gitlab-runner-token-generator
  namespace: gitlab-runner
  annotations:
    helm.sh/hook: post-install
    helm.sh/hook-weight: "10"
    helm.sh/hook-delete-policy: hook-succeeded
spec:
  template:
    spec:
      restartPolicy: OnFailure
      serviceAccountName: runner-setup-sa
      containers:
        - name: generate-token
          image: curlimages/curl:latest
          env:
            - name: GITLAB_URL
              value: "http://gitlab-webservice.gitlab.svc.cluster.local:8181"
            - name: ADMIN_TOKEN
              valueFrom:
                secretKeyRef:
                  name: gitlab-admin-token
                  key: token
          command:
            - /bin/sh
            - -c
            - |
              # Create runner via API and get authentication token
              RUNNER_TOKEN=$(curl -s --request POST \
                --header "PRIVATE-TOKEN: ${ADMIN_TOKEN}" \
                --data "runner_type=instance_type" \
                --data "description=kubernetes-runner" \
                --data "tag_list=kubernetes,docker,amd64" \
                "${GITLAB_URL}/api/v4/user/runners" | jq -r '.token')
              
              echo "Runner token generated: ${RUNNER_TOKEN:0:10}..."
              
              # Create secret with runner token
              cat <<EOF | kubectl apply -f -
              apiVersion: v1
              kind: Secret
              metadata:
                name: gitlab-runner-secret
                namespace: gitlab-runner
              type: Opaque
              stringData:
                runner-token: "${RUNNER_TOKEN}"
              EOF
```

---

## Directory structure for GitOps repository

```
gitops-platform/
├── .sops.yaml
├── argocd/
│   ├── bootstrap/
│   │   └── root-app.yaml
│   ├── applications/
│   │   ├── gpu-operator.yaml      # Wave 0
│   │   ├── longhorn.yaml          # Wave 1
│   │   ├── sealed-secrets.yaml    # Wave 1
│   │   ├── cert-manager.yaml      # Wave 2
│   │   ├── gitlab.yaml            # Wave 3
│   │   ├── gitlab-runner.yaml     # Wave 4
│   │   ├── ollama.yaml            # Wave 5
│   │   ├── dify.yaml              # Wave 6
│   │   └── n8n.yaml               # Wave 6
│   └── projects/
│       └── platform-project.yaml
├── apps/
│   ├── gpu-operator/
│   │   ├── values.yaml
│   │   └── time-slicing-config.yaml
│   ├── longhorn/
│   │   └── values.yaml
│   ├── gitlab/
│   │   ├── values.yaml
│   │   └── sealed-secrets/
│   │       └── gitlab-secrets.yaml
│   ├── gitlab-runner/
│   │   └── values.yaml
│   ├── ollama/
│   │   ├── values.yaml
│   │   └── modelfiles/
│   │       ├── coding-assistant.Modelfile
│   │       └── devops-specialist.Modelfile
│   ├── dify/
│   │   ├── values.yaml
│   │   └── workflows/
│   │       ├── code-review.json
│   │       └── spec-to-code.json
│   └── n8n/
│       └── values.yaml
├── infrastructure/
│   ├── namespaces/
│   ├── storage/
│   │   └── longhorn-storageclass.yaml
│   ├── network-policies/
│   │   ├── gitlab-namespace.yaml
│   │   └── gitlab-runner.yaml
│   └── bootstrap/
│       ├── gitlab-init-job.yaml
│       └── runner-token-job.yaml
├── templates/
│   ├── .gitlab-ci/
│   │   ├── multi-arch-build.yml
│   │   ├── llm-review.yml
│   │   └── spec-validation.yml
│   └── merge-request-templates/
│       └── Spec-Driven.md
└── .env.example
```

---

## Conclusion

This configuration provides a **complete, production-ready self-hosted development platform** optimized for k3s homelab environments with limited resources and GPU sharing. Key architectural decisions include:

**Resource optimization** through careful memory allocation across GitLab components (targeting ~8-10GB for GitLab alone), GPU time-slicing with 4 virtual replicas from a single RTX 5080, and Longhorn storage with 2-replica redundancy suitable for homelab scale.

**Multi-architecture builds without dedicated hardware** leverage QEMU user-mode emulation via Docker Buildx, with cross-compilation toolchains for Go and Rust providing native-speed builds for arm64/riscv64 targets. The GitLab Runner configuration supports architecture-specific node selection for hybrid clusters.

**AI-powered development workflows** integrate Ollama for local inference with custom Modelfiles tuned for coding assistance (32K context, low temperature), Dify for orchestrating multi-step agent workflows, and GitLab CI integration for automated LLM code review on merge requests.

**GitOps deployment via ArgoCD** ensures reproducible infrastructure with proper sync wave ordering (GPU Operator → Storage → GitLab → AI Stack), Sealed Secrets for encrypted credential management, and health checks for custom resources.

The platform enables spec-driven development where specifications in YAML format drive code generation, automated validation in CI, and LLM-powered review—creating a feedback loop between human intent and AI-assisted implementation.