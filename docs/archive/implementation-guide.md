# Self-Hosted AI Kubernetes Platform: Implementation Guide

This comprehensive R&D platform implementation guide provides guardrails for development, testing, and security across your k3s homelab environment with GitOps workflows.

**Bottom line**: Building a sophisticated homelab Kubernetes platform requires layered automation—from btrfs+Longhorn storage foundations through GitOps deployment patterns to policy-enforced guardrails. This guide integrates **8 research domains** into actionable implementation patterns optimized for your dual-node k3s cluster (homelab: 28 cores/120GB RAM + akula-prime: RTX 5080 16GB VRAM).

---

## Part 1: Implementation Prompt with Guardrails

### Storage Foundation: btrfs + Longhorn Architecture

**Critical finding**: Longhorn does NOT support btrfs as a PV filesystem type—only ext4 and xfs. However, btrfs works excellently as the **host filesystem** under Longhorn's data path, enabling btrfs features (compression, snapshots) at the infrastructure layer while Longhorn manages Kubernetes volumes with ext4.

**Host filesystem setup**:
```bash
# Create dedicated btrfs subvolume for Longhorn
btrfs subvolume create /mnt/storage/@longhorn

# Mount with optimized options for NVMe/SSD
# /etc/fstab entry:
UUID=<btrfs-uuid> /var/lib/longhorn btrfs subvol=@longhorn,noatime,compress=zstd:1,space_cache=v2,discard=async 0 0
```

**Longhorn storage classes for homelab**:
```yaml
# Default StorageClass (2-replica for data redundancy across nodes)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-homelab
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
parameters:
  numberOfReplicas: "2"
  dataLocality: "best-effort"
  fsType: "ext4"
provisioner: driver.longhorn.io
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
---
# Strict-local for GPU workloads (single replica, pinned to GPU node)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-gpu-local
parameters:
  numberOfReplicas: "1"
  dataLocality: "strict-local"
  fsType: "ext4"
provisioner: driver.longhorn.io
```

**Compression recommendation**: Use `zstd:1` for NVMe (minimal CPU overhead), `zstd:3` for SATA SSD. Compression benefits Longhorn metadata and sparse files, not data inside PVs (Longhorn uses block storage).

---

### GitOps Architecture: ArgoCD + Helmfile Patterns

**Repository structure** (mono-repo for homelab):
```
gitops-homelab/
├── argocd/
│   ├── bootstrap/
│   │   └── root-app.yaml              # App-of-apps root
│   ├── applications/
│   │   ├── infrastructure/
│   │   │   ├── longhorn.yaml
│   │   │   ├── cert-manager.yaml
│   │   │   └── traefik.yaml
│   │   └── apps/
│   │       ├── gitlab.yaml
│   │       ├── ollama.yaml
│   │       └── n8n.yaml
│   └── projects/
│       └── homelab.yaml
├── infrastructure/
│   ├── longhorn/
│   │   ├── Chart.yaml
│   │   └── values.yaml
│   └── traefik/
├── apps/
│   ├── gitlab/
│   │   ├── base/
│   │   └── overlays/homelab/
│   └── ai-services/
│       ├── ollama/
│       └── litellm/
├── policies/
│   └── kyverno/
├── secrets/                            # SealedSecrets only
│   └── homelab/
└── .sops.yaml                          # SOPS configuration
```

**Multi-source ArgoCD Application** (public Helm chart + private values):
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: gitlab
  namespace: argocd
spec:
  project: default
  sources:
    - repoURL: https://charts.gitlab.io/
      chart: gitlab
      targetRevision: 8.0.0
      helm:
        valueFiles:
          - $values/apps/gitlab/values-homelab.yaml
    - repoURL: https://github.com/yourorg/gitops-homelab
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
```

**Sync wave ordering for dependencies**:
```yaml
# Wave -2: Namespaces and CRDs
# Wave -1: ConfigMaps, Secrets, storage prerequisites
# Wave 0: Core services (databases, message queues)
# Wave 1: Primary applications
# Wave 2: Ingress, monitoring, auxiliary services
# Wave 3: CI/CD runners, batch jobs
```

---

### GitLab CE Deployment: Resource-Optimized Configuration

**Minimal homelab values** (~4-8GB RAM, 2-4 cores baseline):
```yaml
global:
  edition: ce
  hosts:
    domain: homelab.lan
    externalIP: 10.0.0.100
  ingress:
    enabled: true
    class: traefik
    configureCertmanager: false

nginx-ingress:
  enabled: false        # Using Traefik

certmanager:
  install: false        # Self-signed or existing

gitlab-runner:
  install: false        # Deploy separately for control

prometheus:
  install: false        # Use external or skip

gitlab:
  webservice:
    replicaCount: 1
    workerProcesses: 2
    resources:
      requests: { cpu: 300m, memory: 2.5Gi }
      limits: { cpu: 2000m, memory: 4Gi }
  
  sidekiq:
    replicas: 1
    resources:
      requests: { cpu: 100m, memory: 650Mi }
      limits: { cpu: 1000m, memory: 1.5Gi }
  
  gitaly:
    persistence:
      size: 50Gi
      storageClass: longhorn-homelab
    resources:
      requests: { cpu: 100m, memory: 200Mi }
      limits: { cpu: 1500m, memory: 1Gi }
  
  kas:
    enabled: false
  
  gitlab-exporter:
    enabled: false

postgresql:
  primary:
    persistence:
      size: 8Gi
    resources:
      requests: { cpu: 100m, memory: 256Mi }
      limits: { cpu: 1000m, memory: 1Gi }

redis:
  master:
    persistence:
      size: 2Gi
    resources:
      requests: { cpu: 50m, memory: 64Mi }
      limits: { cpu: 500m, memory: 256Mi }

registry:
  replicaCount: 1
  persistence:
    storageClass: longhorn-homelab
```

**Estimated total footprint**: ~4.2GB RAM requested, ~9.5GB limits, ~800m CPU requested.

---

### GitHub Org-Level Runners: Actions Runner Controller (ARC)

**ARC installation** (GitHub-supported controller):
```bash
# 1. Install controller
helm install arc \
  --namespace arc-systems --create-namespace \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set-controller

# 2. Create GitHub App secret
kubectl create secret generic github-app-secret \
  --namespace=arc-runners \
  --from-literal=github_app_id=YOUR_APP_ID \
  --from-literal=github_app_installation_id=YOUR_INSTALLATION_ID \
  --from-file=github_app_private_key=private-key.pem

# 3. Deploy org-level runner scale set
helm install arc-homelab \
  --namespace arc-runners --create-namespace \
  --set githubConfigUrl="https://github.com/YOUR_ORG" \
  --set githubConfigSecret=github-app-secret \
  --set runnerGroup="homelab-runners" \
  --set minRunners=1 --set maxRunners=10 \
  oci://ghcr.io/actions/actions-runner-controller-charts/gha-runner-scale-set
```

**Important ARC limitation**: Runner Scale Sets use a **single label** (the installation name). Deploy multiple scale sets for different workload types:
- `arc-linux-standard` for general CI
- `arc-linux-gpu` for GPU workloads (with nodeSelector)

**gh CLI commands for runner management**:
```bash
# Generate org-level registration token
gh api --method POST /orgs/YOUR_ORG/actions/runners/registration-token

# Create runner group with repo restrictions
gh api --method POST /orgs/YOUR_ORG/actions/runner-groups \
  -d '{"name":"homelab-runners","visibility":"selected","selected_repository_ids":[123,456]}'

# List runners
gh api /orgs/YOUR_ORG/actions/runners
```

---

### Security Hardening: LAN-Only R&D Posture

**Pod Security Standards namespace configuration**:
```yaml
# Baseline for R&D workloads
apiVersion: v1
kind: Namespace
metadata:
  name: ai-services
  labels:
    pod-security.kubernetes.io/enforce: "baseline"
    pod-security.kubernetes.io/audit: "restricted"
    pod-security.kubernetes.io/warn: "restricted"
---
# Privileged for GPU/system workloads
apiVersion: v1
kind: Namespace
metadata:
  name: gpu-workloads
  labels:
    pod-security.kubernetes.io/enforce: "privileged"
    pod-security.kubernetes.io/audit: "baseline"
```

**Network policies (default deny + explicit allow)**:
```yaml
# Default deny for namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ai-services
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# Allow DNS egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: ai-services
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - { protocol: UDP, port: 53 }
        - { protocol: TCP, port: 53 }
---
# Allow LAN access to Ollama
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ollama-allow-lan
  namespace: ai-services
spec:
  podSelector:
    matchLabels:
      app: ollama
  policyTypes: [Ingress]
  ingress:
    - from:
        - ipBlock:
            cidr: 192.168.0.0/16    # Your LAN CIDR
      ports:
        - { protocol: TCP, port: 11434 }
```

**SealedSecrets workflow**:
```bash
# Install controller
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# Fetch public cert
kubeseal --fetch-cert --controller-namespace=kube-system > pub-sealed-secrets.pem

# Seal a secret
kubectl create secret generic api-key \
  --from-literal=key='supersecret' \
  --dry-run=client -o yaml | \
kubeseal --cert pub-sealed-secrets.pem -o yaml > sealed-api-key.yaml

# CRITICAL: Backup sealing keys
kubectl get secret -n kube-system \
  -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml > sealed-secrets-backup.yaml
```

---

### Testing Workflows: Multi-Layer Validation

**Tool stack recommendation** (2024-2025):
- **kubeconform** over kubeval (kubeval unmaintained since K8s 1.18)
- **Ruff** over flake8/pylint for Python (10-100x faster, unified tooling)
- **Kyverno** over OPA/Gatekeeper for homelab (YAML-native, lower overhead)

**Complete pre-commit configuration**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--unsafe]
        exclude: ^charts/.*/templates/
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks:
      - id: shellcheck
        args: [--severity=warning]

  - repo: https://github.com/adrienverge/yamllint
    rev: v1.35.1
    hooks:
      - id: yamllint
        args: [-c, .yamllint]
        exclude: ^charts/.*/templates/

  - repo: https://github.com/yannh/kubeconform
    rev: v0.6.7
    hooks:
      - id: kubeconform
        args:
          - -strict
          - -ignore-missing-schemas
          - -kubernetes-version=1.29.0
          - -schema-location=default
          - -schema-location=https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json
        exclude: ^charts/

  - repo: https://github.com/norwoodj/helm-docs
    rev: v1.14.2
    hooks:
      - id: helm-docs

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]
```

**CI pipeline stages** (GitHub Actions):
```yaml
name: Platform Validation
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-ruff@v2
      - run: ruff check .
      - run: yamllint -c .yamllint manifests/ charts/
      
  validate:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Kubeconform validation
        run: |
          for chart in charts/*/; do
            helm template test "$chart" | kubeconform -strict -summary
          done
          kubeconform -strict -summary manifests/
          
  security:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: config
          severity: HIGH,CRITICAL
          exit-code: '1'
          
  policy:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Kyverno policy check
        run: |
          kyverno apply policies/ --resource manifests/ --table
```

---

### Guardrails: Policy Enforcement with Kyverno

**Installation**:
```bash
helm install kyverno kyverno/kyverno -n kyverno --create-namespace \
  --set replicaCount=1  # Single replica for homelab
```

**Essential security policies**:
```yaml
# Require non-root, disallow privileged, block latest tag
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: pod-security-baseline
spec:
  validationFailureAction: Enforce
  rules:
    - name: require-run-as-non-root
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        message: "Containers must run as non-root"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: true
    - name: disallow-privileged
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        message: "Privileged containers not allowed"
        pattern:
          spec:
            containers:
              - securityContext:
                  privileged: "!true"
    - name: disallow-latest-tag
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        message: "Using 'latest' tag is not allowed"
        pattern:
          spec:
            containers:
              - image: "!*:latest"
```

**Policy exception for system namespaces**:
```yaml
apiVersion: kyverno.io/v2
kind: PolicyException
metadata:
  name: system-namespace-exception
  namespace: kyverno
spec:
  exceptions:
    - policyName: pod-security-baseline
      ruleNames: [disallow-privileged, require-run-as-non-root]
  match:
    any:
      - resources:
          namespaces: [kube-system, kyverno, gpu-workloads]
          kinds: [Pod]
```

---

## Part 2: Context Document

### Environment Mappings

| Component | Primary | Secondary | Storage Class |
|-----------|---------|-----------|---------------|
| **GitLab CE** | homelab | - | longhorn-homelab (2 replicas) |
| **Ollama** | akula-prime | homelab (fallback) | longhorn-gpu-local (1 replica) |
| **LiteLLM** | homelab | - | longhorn-homelab |
| **Open WebUI** | homelab | - | longhorn-homelab |
| **n8n** | homelab | - | longhorn-homelab |
| **SearXNG** | homelab | - | - (stateless) |
| **ARC Runners** | homelab | akula-prime | ephemeral |

### Technology Stack Reference

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| **Orchestration** | k3s | 1.29+ | Lightweight Kubernetes |
| **GitOps** | ArgoCD | 2.10+ | Application deployment |
| **Helm Management** | Helmfile | 0.160+ | Helm release orchestration |
| **Storage** | Longhorn | 1.6+ | Distributed block storage |
| **Policy** | Kyverno | 1.12+ | Admission control, mutation |
| **Secrets** | SealedSecrets | 0.27+ | GitOps-safe secrets |
| **CI/CD** | GitLab Runner | 17+ | Primary CI |
| **CI/CD** | ARC | Latest | GitHub Actions runners |
| **Scanning** | Trivy | 0.50+ | Vulnerability scanning |
| **Validation** | kubeconform | 0.6+ | Manifest validation |
| **Python** | Ruff | 0.8+ | Linting + formatting |

### Success Criteria

**Storage Infrastructure**:
- [ ] btrfs subvolume created at `/var/lib/longhorn` with zstd:1 compression
- [ ] Longhorn installed with 2-replica default, 1-replica GPU-local storage classes
- [ ] Recurring Longhorn snapshots configured (daily, 7-day retention)
- [ ] btrfs host snapshots scheduled weekly

**GitOps Platform**:
- [ ] ArgoCD deployed with app-of-apps bootstrapping
- [ ] Multi-source Applications configured for public charts + private values
- [ ] Sync waves ordered correctly (-2 through +3)
- [ ] SealedSecrets integrated, keys backed up securely

**GitLab Deployment**:
- [ ] GitLab CE running with <8GB RAM baseline
- [ ] Container registry functional with garbage collection
- [ ] GitLab Runner deployed separately in Kubernetes mode
- [ ] Self-signed certificates distributed to clients

**GitHub Runners**:
- [ ] ARC controller installed in arc-systems namespace
- [ ] Org-level runner scale set registered
- [ ] GitHub App authentication configured (not PAT)
- [ ] Runner group with repository access restrictions

**Security Posture**:
- [ ] Pod Security Standards enforced (Baseline default, Privileged exempt)
- [ ] Network policies default-deny per namespace
- [ ] SealedSecrets workflow documented and tested
- [ ] Trivy Operator scanning existing workloads

**Testing Pipeline**:
- [ ] Pre-commit hooks installed and passing
- [ ] CI pipeline validating all manifests
- [ ] Kyverno policies in Enforce mode for critical rules
- [ ] Policy reports accessible via kubectl

**Code Quality**:
- [ ] Ruff configured for Python (pyproject.toml)
- [ ] ShellCheck + shfmt for all shell scripts
- [ ] yamllint configured for Kubernetes YAML
- [ ] helm-docs generating chart documentation

### Key Configuration Files

Create these files in your GitOps repository:

```
gitops-homelab/
├── pyproject.toml              # Python: Ruff, mypy, pytest
├── .yamllint                   # YAML linting rules
├── .shellcheckrc               # Shell script linting
├── .editorconfig               # Editor settings
├── .pre-commit-config.yaml     # Git hooks
├── .sops.yaml                  # SOPS encryption config
├── ct.yaml                     # chart-testing config
├── Taskfile.yml                # Task automation
└── policies/
    └── kyverno/
        ├── security/
        ├── best-practices/
        └── exceptions/
```

### Quick Start Commands

```bash
# 1. Initialize storage
btrfs subvolume create /mnt/storage/@longhorn
mount -o subvol=@longhorn,noatime,compress=zstd:1 /dev/sda2 /var/lib/longhorn

# 2. Install Longhorn
helm install longhorn longhorn/longhorn -n longhorn-system --create-namespace \
  --set defaultSettings.defaultReplicaCount=2 \
  --set defaultSettings.defaultDataLocality=best-effort

# 3. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 4. Install Kyverno
helm install kyverno kyverno/kyverno -n kyverno --create-namespace --set replicaCount=1

# 5. Install SealedSecrets
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# 6. Setup pre-commit
pip install pre-commit
pre-commit install
pre-commit run --all-files

# 7. Bootstrap ArgoCD app-of-apps
kubectl apply -f argocd/bootstrap/root-app.yaml
```

### Monitoring & Troubleshooting

```bash
# Check Longhorn volumes
kubectl -n longhorn-system get volumes.longhorn.io

# Check ArgoCD sync status
argocd app list
kubectl get applications -n argocd

# Check Kyverno policy reports
kubectl get policyreport -A
kubectl get clusterpolicyreport

# Check ARC runners
kubectl get pods -n arc-runners
kubectl logs -n arc-systems -l app.kubernetes.io/name=gha-runner-scale-set-controller

# Validate manifests locally
helm template ./charts/myapp | kubeconform -strict -summary
kyverno apply policies/ --resource manifests/ --table
```

---

This implementation guide provides a production-grade foundation for your homelab R&D platform. Start with storage and ArgoCD foundation (Week 1), add GitLab and security policies (Week 2), then integrate testing workflows and runners (Week 3). The guardrails ensure quality gates at every layer—from pre-commit through admission control to runtime policy enforcement.