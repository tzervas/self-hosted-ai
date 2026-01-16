# Self-Hosted AI Platform - Architecture & Constitution

This document defines the guiding principles, architectural decisions, and constraints that govern the development and operation of the Self-Hosted AI Platform.

---

## Mission Statement

To provide a **secure, private, and fully self-hosted AI infrastructure** that enables advanced AI-assisted development workflows without reliance on external services or data exposure.

---

## Core Principles

### 1. Privacy First

- **No external data transmission**: All AI inference happens on local hardware
- **No telemetry**: Services configured to disable analytics and tracking
- **Self-contained**: Full functionality without internet (except model downloads)
- **Data sovereignty**: All data remains on owned infrastructure

### 2. Security by Design

- **Zero plaintext secrets**: All credentials managed via SealedSecrets
- **Defense in depth**: Network policies, RBAC, TLS everywhere
- **Least privilege**: Services run with minimal required permissions
- **Audit trail**: Comprehensive logging for security events

### 3. Infrastructure as Code

- **GitOps**: All state defined in Git, reconciled by ArgoCD
- **Reproducible**: Any environment can be recreated from source
- **Version controlled**: All changes tracked and reversible
- **Declarative**: Desired state, not imperative scripts

### 4. Operational Excellence

- **Observable**: Metrics, logs, and traces for all services
- **Automated**: Routine tasks scripted in Python with uv
- **Documented**: Architecture decisions recorded
- **Resilient**: Graceful degradation, automatic recovery

### 5. Developer Experience

- **Local-first**: Fast iteration without network dependencies
- **Consistent**: Same tools and patterns everywhere
- **Extensible**: Easy to add new services and capabilities
- **AI-augmented**: Tools designed for AI agent collaboration

---

## Architectural Decisions

### ADR-001: Kubernetes as Platform

**Context**: Need a container orchestration platform for multi-service deployment.

**Decision**: Use k3s (lightweight Kubernetes) for single-node deployment with ability to scale.

**Rationale**:
- Industry standard with vast ecosystem
- GitOps-native with ArgoCD
- Resource efficient (k3s)
- Portable workloads

**Consequences**:
- Learning curve for operators
- Some overhead for simple deployments
- Excellent scaling path

---

### ADR-002: ArgoCD for GitOps

**Context**: Need a deployment mechanism that enforces IaC principles.

**Decision**: Use ArgoCD with App-of-Apps pattern for all deployments.

**Rationale**:
- Declarative, Git-driven deployments
- Automatic drift detection
- Visual dashboard for state
- Sync waves for dependency ordering

**Consequences**:
- All changes must go through Git
- Additional component to maintain
- Learning curve for ArgoCD concepts

---

### ADR-003: LiteLLM as API Gateway

**Context**: Need unified API access to multiple LLM backends with rate limiting and routing.

**Decision**: Use LiteLLM proxy as the primary AI API gateway.

**Rationale**:
- OpenAI-compatible API
- Model routing and fallback
- Rate limiting and cost tracking
- Single endpoint for all models

**Consequences**:
- Additional latency hop
- Dependency on LiteLLM stability
- Centralized logging and control

---

### ADR-004: SealedSecrets for Credential Management

**Context**: Need to store secrets in Git without exposing values.

**Decision**: Use Bitnami SealedSecrets for all Kubernetes secrets.

**Rationale**:
- Secrets encrypted at rest in Git
- Cluster-specific decryption
- GitOps-compatible workflow
- No external secret store dependency

**Consequences**:
- Must backup sealing key
- Secrets tied to specific cluster
- Additional tooling (kubeseal)

---

### ADR-005: Python + uv for Automation

**Context**: Need reliable, maintainable automation scripts.

**Decision**: Replace shell scripts with Python 3.12+ managed by uv.

**Rationale**:
- Type safety with mypy
- Better error handling
- Async operations for performance
- Rich CLI interfaces
- Dependency management

**Consequences**:
- Python required on operator machines
- Higher initial development effort
- Better long-term maintainability

---

### ADR-006: MCP for Tool Integration

**Context**: Need standardized way to expose tools to AI agents.

**Decision**: Use Model Context Protocol (MCP) for tool discovery and execution.

**Rationale**:
- Emerging standard (Anthropic)
- Language-agnostic
- Supports multiple transports
- Growing ecosystem

**Consequences**:
- Early adoption risks
- May need protocol upgrades
- Limited tooling currently

---

### ADR-007: Traefik for Ingress

**Context**: Need HTTP/HTTPS routing with TLS termination.

**Decision**: Use Traefik v3 as the ingress controller.

**Rationale**:
- Native Kubernetes integration
- Automatic TLS with cert-manager
- Middleware support
- Dashboard for visibility

**Consequences**:
- Traefik-specific CRDs
- Configuration complexity
- Resource overhead

---

### ADR-008: Internal CA for TLS

**Context**: Need TLS everywhere but external CAs require DNS validation.

**Decision**: Use self-signed root CA with cert-manager for internal certificates.

**Rationale**:
- No external dependencies
- Instant certificate issuance
- Full control over trust chain
- Works in air-gapped environments

**Consequences**:
- Must install CA on clients
- Not valid for external users
- Certificate management overhead

---

### ADR-009: ARC for GitHub Actions CI/CD

**Context**: Need self-hosted CI/CD runners for builds, tests, and deployments.

**Decision**: Use Actions Runner Controller (ARC) with scale-to-zero runners.

**Rationale**:
- GitHub Actions compatibility
- Scale-to-zero reduces idle resource usage
- Native Kubernetes integration
- Support for specialized runner types

**Runner Types**:
- **amd64**: Standard builds on homelab k3s cluster
- **gpu**: ML/AI workloads accessing GPU over LAN (HTTP to akula-prime:11434)
- **arm64**: ARM builds via QEMU binfmt emulation on amd64 host

**Consequences**:
- Requires ARC controller in cluster
- Cold start latency for scale-to-zero
- ARM64 builds slower due to emulation

---

### ADR-010: GPU Over LAN Architecture

**Context**: GPU workstation (akula-prime) is a separate machine, not a Kubernetes node.

**Decision**: Access GPU inference via HTTP/REST over LAN rather than k8s scheduling.

**Rationale**:
- akula-prime (192.168.1.99) is a standalone workstation with RTX 5080
- Not practical to join as k8s node (desktop OS, different use patterns)
- Ollama provides HTTP API at port 11434
- ComfyUI provides HTTP API at port 8188

**Implementation**:
- GPU-requiring pods use `OLLAMA_GPU_HOST=192.168.1.99:11434` environment variable
- No `nvidia.com/gpu` resource requests in k8s
- Network policy allows egress to 192.168.1.0/24

**Consequences**:
- GPU workloads require network connectivity to akula-prime
- No k8s-level GPU scheduling or resource management
- Simple and effective for homelab scale

---

### ADR-011: Linkerd for Service Mesh (v0.3.0+)

**Context**: Need service-to-service mTLS and observability without Istio overhead.

**Decision**: Deploy Linkerd v2025.1.2 for automatic mTLS and traffic visualization.

**Rationale**:
- Lightweight control plane (~200MB vs ~1GB for Istio)
- Automatic sidecar injection via admission webhooks
- Low latency overhead (~1ms per request)
- Integrates with existing Prometheus monitoring
- Simplified configuration compared to Istio

**Consequences**:
- Automatic mTLS between all injected pods
- Sidecar memory overhead per pod (~20-50MB)
- Certificate rotation managed automatically
- Adds complexity to troubleshooting (proxy logs)

**Scope**: Injected into ai-services, self-hosted-ai, and gpu-workloads namespaces.

---

### ADR-012: Horizontal + Vertical Scaling (v0.3.0+)

**Context**: Need to scale services based on demand while optimizing resource utilization.

**Decision**: Implement HPA for scaling replicas and VPA for resource optimization.

**Rationale**:
- HPA scales services 1→3 replicas at 70% CPU/memory utilization
- VPA recommends optimal resource requests (mode: "Off" for safety)
- ResourceQuotas prevent runaway consumption
- Zero-idle runners (scale-to-zero) for CI/CD cost savings

**Consequences**:
- Requires metrics-server (Kubernetes standard)
- May cause brief latency spikes during scale-up
- VPA recommendations improve over time
- Requires regular monitoring of quota usage

**Tuning Targets**:
- LiteLLM: 1-3 replicas, 70% CPU threshold
- Open WebUI: 1-3 replicas, 70% memory threshold
- Agent Server: 1-5 replicas, aggressive scaling for burst workloads
- ARC Runners: 0-4 replicas, scale-to-zero when idle
- GitLab Runners: 0-10 replicas, Kubernetes executor with isolation

---

## Technology Stack

### Core Platform

| Component | Technology | Purpose |
|-----------|------------|---------|
| Container Runtime | containerd | Container execution |
| Orchestration | k3s (Kubernetes) | Workload scheduling |
| GitOps | ArgoCD | Declarative deployments |
| Ingress | Traefik v3 | HTTP routing, TLS |
| Certificates | cert-manager | TLS certificate lifecycle |
| Secrets | SealedSecrets | Encrypted secrets in Git |
| Storage | Longhorn | Distributed block storage |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Service Mesh | Linkerd v2025.1.2 | mTLS and observability |
| Autoscaling | HPA + VPA | Resource scaling and optimization |

### AI Services

| Component | Technology | Purpose |
|-----------|------------|---------|
| Inference (GPU) | Ollama | LLM inference with GPU |
| Inference (CPU) | Ollama | LLM inference fallback |
| API Gateway | LiteLLM | OpenAI-compatible proxy |
| Chat Interface | Open WebUI | User-facing AI chat |
| Search | SearXNG | Privacy-focused web search |
| Automation | n8n | Workflow orchestration |
| Embeddings | LiteLLM + Ollama | Vector embeddings |

### Model Management

| Source | Type | Purpose | Auth |
|--------|------|---------|------|
| Ollama Library | LLMs | Public censored models | None |
| HuggingFace Hub | LLMs, TTS, Audio | Uncensored models | HF_TOKEN (sealed secret) |
| HuggingFace Hub | Vision, LoRA | Fine-tuning and vision | HF_TOKEN |
| ComfyUI | Checkpoints, VAE | Image/video generation | GitHub/HF direct URLs |

### Development & CI/CD

| Component | Technology | Purpose |
|-----------|------------|---------|
| Source Control | GitLab (self-hosted) | Code repository + mirrors |
| GitHub Mirroring | CronJob + Python | Sync github.com/tzervas and org repos |
| CI/CD (GitHub) | GitHub Actions (ARC) | Automated builds and tests |
| CI/CD (GitLab) | GitLab Runner | GitLab CI pipelines |
| Runner Controller | ghcr.io/actions/arc | ARC runner orchestration |
| Runners (GitHub) | ARC scale sets | 3 sets: amd64, gpu, arm64 + org |
| Runners (GitLab) | Kubernetes executor | Isolated gitlab-runners namespace |
| Scripts | Python 3.12+ / uv | Automation and model syncing |
| Agent Framework | Python ADK | AI agent implementation |

### Infrastructure Topology

| Node | IP Address | Role | Hardware | Kubernetes |
|------|------------|------|----------|-----------|
| homelab | 192.168.1.170 | k3s cluster (single node) | AMD64 server (28c/56t, 120GB RAM) | Control plane + workloads |
| akula-prime | 192.168.1.99 | GPU workstation (over LAN) | RTX 5080 16GB VRAM, 48GB RAM | None (external service) |

---

## Security Model

### Network Security

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │  Traefik  │  TLS Termination
                    │  Ingress  │  Rate Limiting
                    └─────┬─────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐     ┌─────▼─────┐    ┌─────▼─────┐
    │Open WebUI│     │  LiteLLM  │    │    n8n    │
    │(auth)    │     │(api-key)  │    │  (auth)   │
    └────┬────┘     └─────┬─────┘    └───────────┘
         │                │
         └────────┬───────┘
                  │
           ┌──────▼──────┐
           │   Ollama    │  No direct external access
           │  (internal) │
           └─────────────┘
```

### Authentication Layers

1. **Ingress Level**: Traefik basic auth for admin endpoints
2. **Service Level**: Per-service authentication (API keys, passwords)
3. **Kubernetes Level**: RBAC for cluster operations
4. **Secret Level**: SealedSecrets encryption

### Credential Lifecycle

1. **Generation**: `uv run shai-secrets generate`
2. **Storage**: SealedSecrets in Git, documentation in local file
3. **Rotation**: `uv run shai-secrets rotate --all` (monthly)
4. **Access**: `ADMIN_CREDENTIALS.local.md` (gitignored)

---

## Deployment Patterns

### Sync Wave Order

```yaml
# Wave -2: Foundation
sealed-secrets     # Must exist before any secrets

# Wave -1: Infrastructure  
cert-manager       # TLS certificates
longhorn           # Storage

# Wave 0: Platform
traefik            # Ingress
gpu-operator       # GPU support
coredns-custom     # DNS

# Wave 2: Policies
kyverno            # Policy enforcement
prometheus         # Monitoring

# Wave 4: Applications
gitlab             # Source control
dify               # AI platform

# Wave 5: AI Backend
ollama             # Inference
ollama-gpu         # GPU inference
litellm            # API gateway

# Wave 6: AI Frontend
open-webui         # Chat interface
n8n                # Automation
searxng            # Search

# Wave 7: CI/CD Runners
arc-controller     # ARC controller
arc-runners-amd64  # Standard runners
arc-runners-gpu    # GPU-access runners
arc-runners-arm64  # QEMU-emulated ARM runners
```

### Namespace Organization

| Namespace | Purpose |
|-----------|---------|
| `argocd` | GitOps controller |
| `arc-systems` | ARC controller |
| `arc-runners` | GitHub Actions runners |
| `cert-manager` | Certificate management |
| `kube-system` | System components |
| `self-hosted-ai` | Core AI services |
| `gpu-workloads` | GPU-bound workloads |
| `automation` | Workflow services |
| `monitoring` | Observability stack |
| `gitlab` | Source control |

---

---

## Resource Management (v0.3.0+)

### Namespace Quotas

All namespaces have ResourceQuotas to prevent runaway resource consumption:

| Namespace | CPU Requests | CPU Limits | Memory Requests | Memory Limits | Purpose |
|-----------|--------------|-----------|-----------------|---------------|---------|
| ai-services | 8 | 24 | 48Gi | 64Gi | Primary AI workloads |
| gpu-workloads | 2 | 16 | 16Gi | 32Gi | GPU-related services |
| arc-runners | 8 | 20 | 16Gi | 40Gi | GitHub Actions runners (burst) |
| gitlab-runners | 8 | 16 | 16Gi | 32Gi | GitLab runners |
| monitoring | 4 | 8 | 8Gi | 16Gi | Prometheus, Grafana, Loki |
| linkerd | 2 | 4 | 2Gi | 4Gi | Service mesh |

### LimitRanges

Default resource limits ensure pod placement safety:

| Resource | Default Request | Default Limit | Min | Max |
|----------|-----------------|---------------|-----|-----|
| CPU | 100m | 1 | 10m | 16 |
| Memory | 256Mi | 2Gi | 32Mi | 32Gi |

### Autoscaling Policies

**HPA Configuration** (for scale-up services):
- Target CPU utilization: 70%
- Target memory utilization: 80%
- Min replicas: 1
- Max replicas: 3 (LiteLLM, Open WebUI) or 5 (Agent Server)
- Scale-down stabilization: 5 minutes (prevent flapping)
- Scale-up: 15 seconds (rapid response to load)

**VPA Configuration** (for resource optimization):
- Mode: "Off" (recommendations only, no automatic updates)
- Min allowed: 100m CPU / 256Mi memory per container
- Max allowed: 4 CPU / 8Gi memory per container
- Run VPA in "Auto" mode only after validating recommendations

### Storage Allocation Budget

Total: ~500Gi across Longhorn PVs

| Service | Size | Type |
|---------|------|------|
| Ollama GPU models | 150Gi | Persistent |
| Ollama CPU models | 50Gi | Persistent |
| ComfyUI outputs | 50Gi | Persistent |
| Automatic1111 | 100Gi | Persistent |
| Prometheus metrics | 50Gi | Persistent |
| Grafana dashboards | 5Gi | Persistent |
| Open WebUI data | 10Gi | Persistent |
| PostgreSQL (GitLab) | 50Gi | Persistent |
| Buffer/Snapshots | 35Gi | Reserved |

---

## Deployment Patterns

### Sync Wave Order (v0.3.0+)

```yaml
# Wave -2: Foundation
sealed-secrets     # Encrypted secrets in Git

# Wave -1: Infrastructure
linkerd-crds       # Service mesh CRDs
cert-manager       # TLS certificates
longhorn           # Block storage
vpa                # Resource recommendations

# Wave 0: Platform
traefik            # Ingress controller
gpu-operator       # GPU support
coredns-custom     # DNS customization
resource-quotas    # Namespace limits

# Wave 1: Service Mesh & Policy
linkerd-control-plane    # mTLS and observability
linkerd-viz              # Service mesh dashboard
kyverno                  # Pod security policies

# Wave 2: Monitoring
prometheus               # Metrics collection
alertmanager            # Alert routing

# Wave 4: Source Control
gitlab                  # Git server + container registry

# Wave 5: AI Inference Backend
ollama                  # CPU inference
ollama-gpu             # GPU inference
litellm                # OpenAI-compatible API gateway

# Wave 6: User-Facing AI Applications
open-webui             # Chat interface
n8n                    # Workflow automation
searxng                # Web search
mcp-servers            # AI agent tools

# Wave 7: CI/CD Infrastructure
arc-controller         # GitHub Actions runner controller
arc-runners-amd64      # Linux x86_64 runners
arc-runners-gpu        # GPU-accelerated builds
arc-runners-arm64      # ARM64 multi-arch builds
arc-runners-org        # Organization-level runners
gitlab-runners         # GitLab CI runners
```

### Deployment Verification Checklist

After deploying v0.3.0 changes:

1. **Linkerd Service Mesh**
   - [ ] Control plane pods ready in `linkerd` namespace
   - [ ] Viz dashboard available at `linkerd.vectorweight.com`
   - [ ] Proxy injection working (check pod logs for sidecar)
   - [ ] mTLS certificates issued by cert-manager
   - [ ] Verify: `kubectl logs -n ai-services <pod> -c linkerd-proxy`

2. **Autoscaling**
   - [ ] HPA controllers active: `kubectl get hpa -A`
   - [ ] VPA recommender running: `kubectl logs -n kube-system <vpa-recommender>`
   - [ ] ResourceQuotas enforced: `kubectl get resourcequota -A`
   - [ ] Test HPA by monitoring: `kubectl get hpa -A -w`

3. **Repository Mirroring**
   - [ ] GitLab mirror-sync job created: `kubectl get cronjob -n gitlab`
   - [ ] Manual trigger: `kubectl create job --from=cronjob/gitlab-mirror-sync manual-sync -n gitlab`
   - [ ] Check GitLab WebUI for mirrored repos under github-tzervas/ and github-vector-weight-technologies/

4. **CI/CD Runners**
   - [ ] ARC controller ready: `kubectl get pods -n arc-systems`
   - [ ] Runner scale sets configured: `kubectl get autoscalingrunnerset -n arc-runners`
   - [ ] GitLab runners registered: `kubectl logs -n gitlab-runners <runner-pod>`
   - [ ] Test with workflow: Push to GitHub and check runner activation

5. **Models**
   - [ ] Ollama models available: `ollama list` on GPU worker
   - [ ] HuggingFace token secret created: `kubectl get secret huggingface-token -n ai-services`
   - [ ] Download test model: `uv run scripts/sync_models.py download-hf coqui/XTTS-v2`

6. **Test Workflows**
   - [ ] Service mesh verification: `kubectl apply -f workflows/service_mesh_verification.yaml`
   - [ ] CI runner validation: `kubectl apply -f workflows/ci_runner_validation.yaml`
   - [ ] Monitor: `kubectl get workflows -A -w`

## Future Considerations

### Planned Enhancements

- [x] Service mesh (Linkerd) - v0.3.0
- [x] Autoscaling (HPA/VPA) - v0.3.0
- [x] Repository mirroring - v0.3.0
- [x] Uncensored models integration - v0.3.0
- [ ] Multi-node cluster support
- [ ] External secret store (Vault)
- [ ] Advanced RBAC per service
- [ ] Automated security scanning
- [ ] PVC resize automation

### Technology Watch

- **MCP Evolution**: Monitor protocol updates and tooling
- **Ollama**: Track new model support and quantization
- **k3s**: Evaluate upgrade path and new releases
- **ArgoCD**: Evaluate ApplicationSets for multi-env support
- **Linkerd**: Monitor for stability updates and new features

---

## Governance

### Change Process

1. Propose change in GitHub Issue
2. Discuss architectural impact
3. Update this document if ADR required
4. Implement via feature branch
5. Review and merge to main
6. ArgoCD syncs automatically

### Documentation Requirements

- All services must have README in their helm/ directory
- API changes must update OPERATIONS.md
- Security changes must update this document
- Breaking changes must update CONTRIBUTING.md
- New ADRs must follow numbering sequence

---

*This document is the authoritative source for architectural decisions. All development should align with these principles.*

