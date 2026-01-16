# Self-Hosted AI Platform: Context Document

> **Purpose**: Supplement to Implementation Prompt. Contains all configuration details, mappings, references, requirements, and success criteria.

---

## 1. Infrastructure Mapping

### Node Assignments

| Node | Hostname | IP | Role | Resources |
|------|----------|----|----|-----------|
| Primary | homelab | 192.168.1.170 | Control plane + workloads | 28c/56t, 120GB RAM |
| GPU Worker | akula-prime | 192.168.1.99 | GPU inference + CI | RTX 5080 16GB VRAM |

### Service-to-Node Mapping

| Service | Namespace | Node | Storage | Replicas |
|---------|-----------|------|---------|----------|
| ArgoCD | argocd | homelab | - | 1 |
| Longhorn | longhorn-system | both | host path | 1 per node |
| Kyverno | kyverno | homelab | - | 1 |
| SealedSecrets | kube-system | homelab | - | 1 |
| GitLab CE | gitlab | homelab | longhorn-homelab | 1 |
| Ollama (GPU) | ai-services | akula-prime | longhorn-gpu-local | 1 |
| Ollama (CPU) | ai-services | homelab | longhorn-homelab | 1 |
| LiteLLM | ai-services | homelab | longhorn-homelab | 1 |
| Open WebUI | ai-services | homelab | longhorn-homelab | 1 |
| n8n | automation | homelab | longhorn-homelab | 1 |
| SearXNG | ai-services | homelab | - (stateless) | 1 |
| Traefik | kube-system | homelab | - | 1 |
| ARC Controller | arc-systems | homelab | - | 1 |
| ARC Runners | arc-runners | both | ephemeral | 1-10 |
| GitLab Runner | gitlab | homelab | ephemeral | 1-5 |

### Storage Budget (500GB Total)

| Allocation | Size | StorageClass | Subvolume |
|------------|------|--------------|-----------|
| Ollama Models (GPU) | 150Gi | longhorn-gpu-local | @models |
| Ollama Models (CPU) | 50Gi | longhorn-homelab | @models |
| GitLab (Gitaly+DB+Registry) | 100Gi | longhorn-homelab | @gitlab |
| Observability Stack | 50Gi | longhorn-homelab | @data |
| Application Data | 50Gi | longhorn-homelab | @data |
| Buffer/Snapshots | 100Gi | - | @snapshots |

---

## 2. Configuration Files

### 2.1 Storage: btrfs fstab Entry

```fstab
# /etc/fstab on homelab
UUID=<your-btrfs-uuid> /var/lib/longhorn btrfs subvol=@longhorn,noatime,compress=zstd:1,space_cache=v2,discard=async 0 0
```

### 2.2 Longhorn StorageClasses

```yaml
# longhorn-homelab (default)
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
# longhorn-gpu-local (GPU node only)
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-gpu-local
parameters:
  numberOfReplicas: "1"
  dataLocality: "strict-local"
  fsType: "ext4"
provisioner: driver.longhorn.io
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

### 2.3 Pre-commit Configuration

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
      - id: check-added-large-files
        args: [--maxkb=1024]
      - id: detect-private-key
      - id: check-merge-conflict

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

  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.8.0-1
    hooks:
      - id: shfmt
        args: [-i, "2", -ci]

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

### 2.4 yamllint Configuration

```yaml
# .yamllint
extends: default

rules:
  line-length:
    max: 150
    level: warning
  truthy:
    allowed-values: ['true', 'false', 'yes', 'no']
  comments:
    min-spaces-from-content: 1
  document-start: disable
  indentation:
    spaces: 2
    indent-sequences: consistent

ignore: |
  charts/*/templates/
  .git/
  node_modules/
```

### 2.5 Ruff Configuration (pyproject.toml)

```toml
# pyproject.toml
[project]
name = "self-hosted-ai"
requires-python = ">=3.11"

[tool.ruff]
target-version = "py311"
line-length = 100
exclude = [".venv", "venv", "__pycache__", ".git"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["self_hosted_ai"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

### 2.6 Kyverno Policies

```yaml
# policies/kyverno/security/baseline.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: pod-security-baseline
  annotations:
    policies.kyverno.io/title: Pod Security Baseline
    policies.kyverno.io/category: Security
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: require-run-as-non-root
      match:
        any:
          - resources:
              kinds: [Pod]
      exclude:
        any:
          - resources:
              namespaces: [kube-system, kyverno, gpu-workloads, longhorn-system]
      validate:
        message: "Containers must set securityContext.runAsNonRoot=true"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: true

    - name: disallow-privileged-containers
      match:
        any:
          - resources:
              kinds: [Pod]
      exclude:
        any:
          - resources:
              namespaces: [kube-system, kyverno, gpu-workloads, longhorn-system]
      validate:
        message: "Privileged containers are not allowed"
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
        message: "Using ':latest' tag is not allowed. Pin image versions."
        pattern:
          spec:
            containers:
              - image: "!*:latest"
            =(initContainers):
              - image: "!*:latest"

    - name: require-resource-limits
      match:
        any:
          - resources:
              kinds: [Pod]
      exclude:
        any:
          - resources:
              namespaces: [kube-system, kyverno]
      validate:
        message: "CPU and memory limits are required"
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    memory: "?*"
                    cpu: "?*"
---
# policies/kyverno/best-practices/require-labels.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: Audit
  background: true
  rules:
    - name: require-app-label
      match:
        any:
          - resources:
              kinds: [Deployment, StatefulSet, DaemonSet]
      validate:
        message: "The label 'app.kubernetes.io/name' is required"
        pattern:
          metadata:
            labels:
              app.kubernetes.io/name: "?*"
```

### 2.7 NetworkPolicy Templates

```yaml
# policies/network/default-deny.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
# policies/network/allow-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
# policies/network/allow-lan-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-lan-ingress
spec:
  podSelector:
    matchLabels:
      network.policy/lan-accessible: "true"
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 192.168.0.0/16
```

### 2.8 ArgoCD App-of-Apps Root

```yaml
# argocd/bootstrap/root-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/YOUR_ORG/gitops-homelab.git
    targetRevision: main
    path: argocd/applications
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### 2.9 CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/validate.yml
name: Platform Validation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install tools
        run: |
          pip install ruff yamllint
          curl -sL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz | tar xz
          sudo mv kubeconform /usr/local/bin/
      
      - name: Ruff check
        run: ruff check .
      
      - name: YAML lint
        run: yamllint -c .yamllint manifests/ charts/*/values*.yaml
      
      - name: Shell lint
        uses: ludeeus/action-shellcheck@master
        with:
          severity: warning

  validate:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Helm
        uses: azure/setup-helm@v4
      
      - name: Helm lint
        run: |
          for chart in charts/*/; do
            helm lint "$chart"
          done
      
      - name: Kubeconform validation
        run: |
          for chart in charts/*/; do
            helm template test "$chart" 2>/dev/null | kubeconform -strict -summary || true
          done
          find manifests/ -name '*.yaml' -exec kubeconform -strict {} +

  security:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Trivy config scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: config
          scan-ref: .
          severity: HIGH,CRITICAL
          exit-code: '1'

  policy:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Kyverno CLI
        run: |
          curl -sL https://github.com/kyverno/kyverno/releases/latest/download/kyverno-cli_latest_linux_amd64.tar.gz | tar xz
          sudo mv kyverno /usr/local/bin/
      
      - name: Policy validation
        run: |
          for chart in charts/*/; do
            helm template test "$chart" 2>/dev/null | kyverno apply policies/kyverno/ --resource /dev/stdin --table || true
          done
```

---

## 3. Sync Wave Ordering

| Wave | Resources | Examples |
|------|-----------|----------|
| -2 | Namespaces, CRDs | Custom namespaces, Longhorn CRDs |
| -1 | ConfigMaps, Secrets, RBAC | SealedSecrets, ServiceAccounts |
| 0 | Core infrastructure | Longhorn, Traefik, Kyverno |
| 1 | Databases, storage-dependent | PostgreSQL, Redis, Gitaly |
| 2 | Primary applications | GitLab, Ollama, LiteLLM |
| 3 | Auxiliary services | Open WebUI, n8n, SearXNG |
| 4 | CI/CD runners | ARC, GitLab Runner |
| 5 | Monitoring, observability | Prometheus, Grafana (if added) |

---

## 4. Version Pinning Reference

| Component | Version | Helm Chart | Notes |
|-----------|---------|------------|-------|
| k3s | 1.29.x | - | LTS track |
| ArgoCD | 2.13.x | argo/argo-cd 7.x | |
| Longhorn | 1.7.x | longhorn/longhorn | |
| Kyverno | 1.12.x | kyverno/kyverno | |
| SealedSecrets | 0.27.x | sealed-secrets/sealed-secrets | |
| GitLab CE | 17.x | gitlab/gitlab | Pin to specific minor |
| Traefik | 3.x | traefik/traefik | Bundled with k3s |
| ARC | 0.9.x | gha-runner-scale-set-controller | OCI registry |

---

## 5. Success Criteria Checklist

### Phase 1: Storage Foundation
- [ ] btrfs subvolume `@longhorn` created and mounted
- [ ] Compression verified: `btrfs property get /var/lib/longhorn compression`
- [ ] Longhorn installed: `kubectl -n longhorn-system get pods` all Running
- [ ] StorageClass `longhorn-homelab` is default: `kubectl get sc`
- [ ] StorageClass `longhorn-gpu-local` available
- [ ] Test PVC provisions successfully
- [ ] Recurring snapshot job configured

### Phase 2: GitOps Bootstrap
- [ ] ArgoCD accessible via port-forward or Ingress
- [ ] Admin password retrieved and changed
- [ ] SealedSecrets controller running
- [ ] Sealing keys backed up to secure location
- [ ] Root app-of-apps deployed and synced
- [ ] Multi-source Application pattern working
- [ ] Sync waves executing in order

### Phase 3: Security Policies
- [ ] Kyverno controller running: `kubectl -n kyverno get pods`
- [ ] Policies applied: `kubectl get clusterpolicy`
- [ ] Test: non-compliant pod rejected
- [ ] Test: compliant pod admitted
- [ ] PolicyExceptions working for system namespaces
- [ ] NetworkPolicies applied to ai-services namespace
- [ ] Test: DNS egress works, other egress blocked

### Phase 4: Core Services
- [ ] GitLab accessible at configured URL
- [ ] GitLab root password retrieved
- [ ] Container registry functional
- [ ] Ollama GPU pod running on akula-prime
- [ ] Ollama responds to API calls
- [ ] LiteLLM proxying to Ollama
- [ ] Open WebUI accessible and connected
- [ ] n8n accessible and functional
- [ ] SearXNG returning search results

### Phase 5: CI/CD Runners
- [ ] ARC controller running: `kubectl -n arc-systems get pods`
- [ ] GitHub App created with correct permissions
- [ ] Runner scale set registered: `gh api /orgs/ORG/actions/runners`
- [ ] Test workflow executes on self-hosted runner
- [ ] GitLab Runner registered to GitLab instance
- [ ] GitLab CI pipeline executes successfully

### Phase 6: Testing & Quality Gates
- [ ] pre-commit installed: `pre-commit --version`
- [ ] All hooks passing: `pre-commit run --all-files`
- [ ] CI pipeline passes on clean commit
- [ ] CI pipeline fails on intentional violation
- [ ] Kyverno policy reports accessible
- [ ] Trivy Operator scanning (if installed)

---

## 6. Troubleshooting Reference

### Storage Issues
```bash
# Longhorn volume stuck
kubectl -n longhorn-system logs -l app=longhorn-manager --tail=100
kubectl -n longhorn-system get volumes.longhorn.io -o wide

# btrfs health check
sudo btrfs device stats /var/lib/longhorn
sudo btrfs scrub start /var/lib/longhorn
```

### ArgoCD Sync Issues
```bash
# Check app status
argocd app get APP_NAME --show-operation

# Force sync with prune
argocd app sync APP_NAME --prune --force

# Check resource diff
argocd app diff APP_NAME
```

### Kyverno Policy Issues
```bash
# Check why pod was rejected
kubectl get events --field-selector reason=PolicyViolation -A

# View policy reports
kubectl get policyreport -A
kubectl get clusterpolicyreport

# Test policy locally
kyverno apply policies/kyverno/security/ --resource pod.yaml --table
```

### Network Policy Debugging
```bash
# Test connectivity from pod
kubectl exec -it POD -- wget -qO- http://service.namespace.svc:port

# Check if network policies are applied
kubectl get networkpolicy -n NAMESPACE

# Describe for details
kubectl describe networkpolicy POLICY -n NAMESPACE
```

### Runner Issues
```bash
# ARC runner logs
kubectl -n arc-runners logs -l app.kubernetes.io/component=runner --tail=50

# Check scale set
kubectl -n arc-runners get autoscalingrunnerset

# GitHub API check
gh api /orgs/ORG/actions/runners
gh api /orgs/ORG/actions/runner-groups
```

---

## 7. Maintenance Procedures

### Weekly
- [ ] Review Kyverno policy reports
- [ ] Check Longhorn volume health
- [ ] Verify btrfs scrub completed
- [ ] Review CI pipeline success rate

### Monthly
- [ ] Rotate GitHub App private key (if required)
- [ ] Update SealedSecrets key backup
- [ ] Review and update pinned versions
- [ ] Prune unused container images
- [ ] Review storage usage trends

### Quarterly
- [ ] Test disaster recovery procedure
- [ ] Review and update security policies
- [ ] Audit RBAC permissions
- [ ] Update k3s to latest patch version

---

## 8. References

| Resource | URL |
|----------|-----|
| k3s Docs | https://docs.k3s.io/ |
| ArgoCD Docs | https://argo-cd.readthedocs.io/ |
| Longhorn Docs | https://longhorn.io/docs/ |
| Kyverno Docs | https://kyverno.io/docs/ |
| SealedSecrets | https://sealed-secrets.netlify.app/ |
| GitLab Helm | https://docs.gitlab.com/charts/ |
| ARC Docs | https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller |
| kubeconform | https://github.com/yannh/kubeconform |
| Ruff | https://docs.astral.sh/ruff/ |
| Trivy | https://aquasecurity.github.io/trivy/ |
