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

### Development

| Component | Technology | Purpose |
|-----------|------------|---------|
| Source Control | GitLab (self-hosted) | Code repository |
| CI/CD | GitHub Actions (ARC) | Automated builds |
| ARC Controller | ghcr.io/actions/arc | Runner orchestration |
| Scripts | Python 3.12+ / uv | Automation |
| Agent Framework | Python ADK | AI agent implementation |

### Infrastructure Topology

| Node | IP Address | Role | Hardware |
|------|------------|------|----------|
| homelab | 192.168.1.170 | k3s cluster (single node) | AMD64 server |
| akula-prime | 192.168.1.99 | GPU workstation (over LAN) | RTX 5080, not k8s node |

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

## Future Considerations

### Planned Enhancements

- [ ] Multi-node cluster support
- [ ] External secret store (Vault)
- [ ] Service mesh (Linkerd)
- [ ] Advanced RBAC per service
- [ ] Automated security scanning

### Technology Watch

- **MCP Evolution**: Monitor protocol updates
- **Ollama**: Track new model support
- **k3s**: Evaluate upgrade path to full k8s
- **ArgoCD**: Evaluate ApplicationSets

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

---

*This document is the authoritative source for architectural decisions. All development should align with these principles.*
