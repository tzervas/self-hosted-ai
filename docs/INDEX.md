# Self-Hosted AI Platform - Documentation Index

**Last Updated**: 2026-02-06
**Purpose**: Token-efficient navigation guide for Claude Code and AI agents

> **Quick Start**: Looking for something specific? Use Ctrl+F to search by keyword. Each section links to detailed docs with concise summaries optimized for context windows.

---

## 🗺️ Navigation Matrix

### By Persona

| You Are... | Start Here | Then Read |
|------------|-----------|-----------|
| **New Developer** | [README.md](../README.md) → [ARCHITECTURE.md](../ARCHITECTURE.md) → [CONTRIBUTING.md](../CONTRIBUTING.md) | [docs/DEPLOYMENT.md](DEPLOYMENT.md) |
| **Platform Operator** | [OPERATIONS.md](../OPERATIONS.md) → [ARCHITECTURE.md](../ARCHITECTURE.md) | [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) |
| **AI Agent** | This INDEX → [CLAUDE.md](../CLAUDE.md) → [ARCHITECTURE.md](../ARCHITECTURE.md) | Context-specific docs below |
| **Security Auditor** | [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-006 → [implementation-guide.md](../implementation-guide.md) Security section | Sealed secrets in `argocd/sealed-secrets/` |
| **Troubleshooter** | [OPERATIONS.md](../OPERATIONS.md) → [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) | Service-specific logs in `helm/*/` |

### By Task

| Task | Primary Docs | Supporting Files | CLI Tools |
|------|--------------|------------------|-----------|
| **Deploy New Service** | [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-002 (GitOps) | `argocd/applications/*.yaml`, `helm/*/` | `kubectl apply`, `argocd app sync` |
| **Configure SSO** | [GITLAB_ACCESS_INSTRUCTIONS.md](../GITLAB_ACCESS_INSTRUCTIONS.md) | `scripts/setup-keycloak-*.sh`, `argocd/sealed-secrets/*-oidc-secret.yaml` | `scripts/setup-keycloak-realm.sh` |
| **Add AI Model** | [config/models-manifest.yml](../config/models-manifest.yml) | `helm/ollama/values.yaml` | `scripts/sync_models.py` |
| **Create Workflow** | [workflows/README.md](../workflows/README.md) | `config/n8n-workflows/*.json` | n8n UI at `https://n8n.vectorweight.com` |
| **Debug Deployment** | [OPERATIONS.md](../OPERATIONS.md) Troubleshooting | [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) | `kubectl logs`, `argocd app get` |
| **Rotate Secrets** | [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-006 | `argocd/sealed-secrets/` | `scripts/secrets_manager.py rotate` |
| **Scale Resources** | [helm/resource-quotas/](../helm/resource-quotas/) | `helm/*/values.yaml` (resources sections) | `kubectl top`, `kubectl scale` |
| **Monitor Cluster** | [OPERATIONS.md](../OPERATIONS.md) | Grafana dashboards | `https://grafana.vectorweight.com` |

---

## 📚 Core Documentation (Token-Optimized Summaries)

### Constitution & Principles

#### [ARCHITECTURE.md](../ARCHITECTURE.md) (1,500 tokens)
**Mission**: Privacy-first, self-hosted AI infrastructure without external dependencies
**Key Sections**:
- **Core Principles** (lines 13-49): Privacy, Security, IaC, Ops Excellence, DevEx
- **ADR-001** (54-70): Kubernetes/k3s platform choice
- **ADR-002** (72-89): ArgoCD GitOps with App-of-Apps pattern, sync waves (-2 to 7)
- **ADR-003** (91-108): LiteLLM as unified API gateway
- **ADR-004** (110-127): Open WebUI for chat interface
- **ADR-005** (129-146): Model Context Protocol (MCP) integration
- **ADR-006** (148-165): SealedSecrets for GitOps-friendly secrets
- **ADR-007** (167-184): Python with uv for automation
- **Technology Stack** (186-210): Complete tech matrix
- **Security Model** (212-245): Defense in depth, RBAC, network policies

**Dependencies**: None (foundational)
**When to Read**: Before any architectural decision or major feature

#### [OPERATIONS.md](../OPERATIONS.md) (800 tokens)
**Purpose**: Daily ops runbook and service access
**Key Sections**:
- **Service Endpoints** (7-20): All HTTPS URLs with purposes
- **Internal Services** (22-30): ClusterIP services and ports
- **GPU Worker** (32-48): Standalone workstation at 192.168.1.99
- **Quick Commands** (77-): Cluster health, ArgoCD sync, logs
- **Troubleshooting** (later): Common issues and solutions

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md)
**When to Read**: First day on platform, debugging, ops tasks

### Getting Started

#### [README.md](../README.md) (600 tokens)
**Purpose**: Project overview and quick start
**Key Sections**:
- **Features** (12-21): Multi-model routing, Web UI, workflows, GitOps, MCP
- **Architecture Diagram** (23-66): Visual cluster topology
- **Hardware** (68-73): Node specs (akula-prime + homelab)
- **Quick Start** (75-127): Prerequisites → Bootstrap → Validate
- **Service Endpoints** (129-140): Production URLs
- **CLI Tools** (143-167): shai-* command reference
- **MCP Servers** (169-186): Available tool servers

**Dependencies**: None (entry point)
**When to Read**: First time exploring project

#### [CONTRIBUTING.md](../CONTRIBUTING.md) (500 tokens)
**Purpose**: Git workflow and contribution standards
**Key Sections**:
- **Branch Strategy** (7-22): main (stable) ← dev ← feature/* workflow
- **Commit Messages** (46-): Conventional Commits format
- **Pre-commit Hooks** (later): Automated validation
- **Testing** (later): Validation requirements

**Dependencies**: None
**When to Read**: Before contributing code

### Deployment & Operations

#### [docs/DEPLOYMENT.md](DEPLOYMENT.md) (1,200 tokens)
**Purpose**: Complete deployment procedures
**Key Sections**:
- **Architecture Overview** (5-30): Network topology diagram
- **Prerequisites** (32-42): K3s, ArgoCD, tools required
- **Fresh Deployment** (44-): Step-by-step bootstrap
- **Service Configuration** (later): Individual service setup
- **GPU Worker Setup** (later): Standalone Docker deployment

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md), [README.md](../README.md)
**When to Read**: Initial deployment, adding nodes

#### [implementation-guide.md](../implementation-guide.md) (3,000 tokens)
**Purpose**: Deep R&D implementation patterns and guardrails
**Key Sections**:
- **Storage Foundation** (10-56): btrfs + Longhorn architecture, NOT btrfs PVs
- **GitOps Architecture** (58-150): ArgoCD patterns, multi-source apps
- **Security Hardening** (later): Pod security, network policies
- **GPU Workload Patterns** (later): NVIDIA operator, taints/tolerations
- **Observability Stack** (later): Prometheus, Loki, Grafana setup
- **Backup/DR** (later): Velero, Longhorn snapshots

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md)
**When to Read**: Advanced implementation, infrastructure design decisions

#### [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) (1,000 tokens)
**Purpose**: Cluster validation results and health checks
**Key Sections**:
- **Validation Summary**: Pass/fail status per service
- **Service Health**: Endpoint tests, API checks
- **Known Issues**: Current limitations and workarounds
- **Recommendations**: Next steps and improvements

**Dependencies**: [OPERATIONS.md](../OPERATIONS.md)
**When to Read**: After deployment, debugging, health checks

### Security & Access

#### [GITLAB_ACCESS_INSTRUCTIONS.md](../GITLAB_ACCESS_INSTRUCTIONS.md) (700 tokens)
**Purpose**: GitLab deployment with SSO integration
**Key Sections**:
- **Keycloak SSO Setup**: Realm configuration, OIDC clients
- **GitLab OAuth**: Integration with Keycloak
- **Credential Retrieval**: Scripts to extract secrets
- **Access URLs**: GitLab, Keycloak endpoints

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-006
**When to Read**: Setting up GitLab, configuring SSO

### AI-Specific Documentation

#### [config/models-manifest.yml](../config/models-manifest.yml) (200 tokens)
**Purpose**: Declarative model inventory
**Format**: YAML list of models to pull with sizes and purposes

**Dependencies**: None
**When to Read**: Adding/removing models

#### [config/litellm-config.yml](../config/litellm-config.yml) (400 tokens)
**Purpose**: LiteLLM model routing configuration
**Key Sections**:
- Model definitions with Ollama backend URLs
- Routing rules and fallbacks
- Rate limiting per model

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-003
**When to Read**: Configuring model routing, adding backends

#### [workflows/README.md](../workflows/README.md) (300 tokens)
**Purpose**: n8n workflow documentation
**Key Sections**:
- Available workflows in `config/n8n-workflows/`
- Import/export procedures
- Workflow composition patterns

**Dependencies**: [README.md](../README.md)
**When to Read**: Creating/modifying workflows

### Specialized Reports

#### [docs/API_RATE_LIMITS_REPORT.md](API_RATE_LIMITS_REPORT.md) (2,000 tokens)
**Purpose**: Comprehensive API rate limit analysis across all services
**Generated**: Automated report
**When to Read**: Planning API usage, debugging rate limit errors

---

## 📁 Codebase Structure Map

### Directory Taxonomy

```
self-hosted-ai/
├── argocd/                        # GitOps Deployment Layer
│   ├── applications/              # ArgoCD Application manifests (sync wave metadata)
│   │   ├── *.yaml                 # Individual service apps with syncPolicy and wave
│   │   └── README.md              # (missing - should document sync wave strategy)
│   ├── helm/                      # Helm value overrides per app
│   │   ├── gitlab/                # GitLab-specific values
│   │   ├── prometheus/            # Monitoring stack values
│   │   └── dify/                  # Dify AI platform values
│   └── sealed-secrets/            # Encrypted secrets (safe for Git)
│       ├── *-oidc-secret.yaml     # OIDC client credentials
│       └── *-oauth-secret.yaml    # OAuth application secrets
│
├── helm/                          # Service Helm Charts
│   ├── server/                    # Umbrella chart (deprecated - use ArgoCD apps)
│   ├── ollama/                    # CPU Ollama inference
│   ├── ollama-gpu/                # (check if used - may be in gpu-worker/)
│   ├── open-webui/                # Chat interface
│   ├── litellm/                   # API gateway
│   ├── n8n/                       # Workflow automation
│   ├── postgresql/                # Database for LiteLLM
│   ├── redis/                     # Cache/queues
│   ├── searxng/                   # Privacy search
│   ├── mcp-servers/               # Model Context Protocol tools
│   ├── keycloak/                  # SSO identity provider
│   ├── oauth2-proxy/              # Forward-auth middleware
│   ├── cert-manager-issuers/      # TLS certificate issuers
│   ├── ingress-redirects/         # HTTP → HTTPS redirects
│   ├── resource-quotas/           # Namespace quotas and LimitRanges
│   ├── gpu-worker/                # GPU workload templates
│   │   ├── templates/
│   │   │   ├── audio-deployment.yaml
│   │   │   ├── tts-deployment.yaml
│   │   │   ├── video-deployment.yaml
│   │   │   └── shared-models-pvc.yaml
│   │   └── values.yaml
│   └── README.md                  # Helm chart overview
│
├── config/                        # Application Configurations
│   ├── litellm-config.yml         # Model routing rules
│   ├── models-manifest.yml        # Models to pull
│   ├── n8n-workflows/             # Exported n8n workflows (JSON)
│   │   ├── agentic-reasoning.json
│   │   ├── multi-agent-orchestrator.json
│   │   └── unified-multimodal-content.json
│   └── comfyui-workflows/         # ComfyUI workflow definitions
│
├── scripts/                       # Python Automation (uv managed)
│   ├── pyproject.toml             # Python dependencies
│   ├── bootstrap.py               # Initial cluster setup
│   ├── validate_cluster.py        # Health checks
│   ├── secrets_manager.py         # SealedSecret generation
│   ├── sync_models.py             # Ollama model management
│   ├── rag_index.py               # Documentation RAG indexer
│   ├── setup-keycloak-realm.sh    # Keycloak SSO automation
│   ├── setup-keycloak-secrets.sh  # OIDC secret sealing
│   ├── retrieve_gitlab_credentials.sh  # GitLab credential extraction
│   └── README.md                  # Script documentation
│
├── agents/                        # Python Agent Framework (NOT Claude sub-agents)
│   ├── core/                      # Base agent classes
│   │   ├── base.py                # BaseAgent, Tool, Task
│   │   └── workflow.py            # Multi-agent orchestration
│   ├── specialized/               # Domain-specific agents
│   │   ├── researcher.py
│   │   ├── developer.py
│   │   ├── code_reviewer.py
│   │   ├── testing.py
│   │   └── documentation.py
│   └── README.md                  # Agent framework guide
│
├── containers/                    # Custom Container Images
│   ├── audio-server/              # Bark audio generation
│   │   ├── Dockerfile
│   │   ├── server.py
│   │   └── requirements.txt
│   └── video-server/              # AnimateDiff video generation
│       ├── Dockerfile
│       ├── server.py
│       └── requirements.txt
│
├── policies/                      # Kubernetes Policy Enforcement
│   ├── kyverno/                   # Kyverno policies (if used)
│   └── network-policies/          # NetworkPolicy manifests (if used)
│
├── .claude/                       # Claude Code Configuration
│   ├── agents/                    # Claude sub-agents (AI-powered workflows)
│   │   ├── k8s-validator.md       # Manifest validation (Haiku)
│   │   ├── python-test-runner.md  # Pytest execution (Haiku)
│   │   └── argocd-sync-monitor.md # Deployment monitoring (Sonnet)
│   ├── settings.json              # Permissions, hooks, MCP servers
│   └── memory/                    # Agent memory persistence (auto)
│
├── docs/                          # Documentation
│   ├── INDEX.md                   # THIS FILE - Navigation guide
│   ├── DEPLOYMENT.md              # Deployment procedures
│   ├── VERIFICATION_REPORT.md     # Cluster health report
│   ├── API_RATE_LIMITS_REPORT.md  # Rate limit analysis
│   └── archive/                   # Historical docs
│       ├── CONTEXT_SUMMARY.md
│       ├── QUICK_REFERENCE.md
│       └── legacy-scripts/
│
├── ARCHITECTURE.md                # System design & ADRs
├── OPERATIONS.md                  # Operations runbook
├── CONTRIBUTING.md                # Git workflow & standards
├── CLAUDE.md                      # Claude Code project guidance
├── README.md                      # Project overview
├── GITLAB_ACCESS_INSTRUCTIONS.md  # GitLab + SSO setup
├── implementation-guide.md        # R&D implementation patterns
├── pyproject.toml                 # Root Python project (deprecated - use scripts/)
└── Taskfile.yaml                  # Task runner (validation, linting, security)
```

### File Count Summary

| Directory | Files | Purpose |
|-----------|-------|---------|
| `argocd/applications/` | ~30 | ArgoCD Application definitions (one per service) |
| `argocd/sealed-secrets/` | ~15 | Encrypted Kubernetes secrets (OIDC, OAuth, tokens) |
| `helm/*/` | ~20 charts | Helm charts for all services |
| `config/n8n-workflows/` | ~8 | AI workflow automation definitions |
| `scripts/` | ~15 | Python automation scripts |
| `agents/` | ~10 | Python agent framework classes |
| `containers/` | 2 | Custom Docker images (audio, video) |
| `.claude/agents/` | 3 | Claude Code sub-agents |
| `docs/` | ~10 | Documentation and reports |

---

## 🔍 Quick Reference by Topic

### ArgoCD Sync Waves (Deployment Order)

Defined in `argocd/applications/*.yaml` via `metadata.annotations.argocd.argoproj.io/sync-wave`:

| Wave | Services | Purpose |
|------|----------|---------|
| **-2** | sealed-secrets-controller | Foundation for secret decryption |
| **-1** | cert-manager, Longhorn, Linkerd CRDs | Infrastructure dependencies |
| **0** | Traefik, GPU operator, resource-quotas, cert-manager-issuers | Networking and policies |
| **1** | Linkerd control plane, Kyverno policies | Service mesh and governance |
| **2** | Prometheus, Grafana | Observability |
| **5** | Ollama (CPU/GPU), LiteLLM, PostgreSQL, Redis, Keycloak | AI backend services |
| **6** | Open WebUI, n8n, SearXNG | AI frontend and workflows |
| **7** | GitLab, Actions Runner Controller (ARC) | CI/CD and automation |

**File**: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-002

### Namespaces

| Namespace | Purpose | Key Services |
|-----------|---------|--------------|
| `argocd` | GitOps control plane | ArgoCD server, repo-server, dex |
| `cert-manager` | TLS certificate management | cert-manager, issuers, CA |
| `automation` | Workflow orchestration | n8n, workflow triggers |
| `self-hosted-ai` | Core AI services | Open WebUI, LiteLLM, Ollama (CPU), PostgreSQL, Redis, MCP servers |
| `gpu-workloads` | GPU-accelerated AI | Ollama (GPU), audio-server, video-server, TTS |
| `monitoring` | Observability | Prometheus, Grafana, Alertmanager |
| `sso` | Identity and access | Keycloak, oauth2-proxy |
| `ingress` | External access | Traefik |
| `longhorn-system` | Storage | Longhorn controller, CSI driver |
| `linkerd` | Service mesh | Linkerd control plane (if enabled) |
| `kyverno` | Policy enforcement | Kyverno (if enabled) |
| `arc-runners` | CI/CD runners | GitHub Actions Runner Controller |

### Service Dependencies (Implicit Order)

```
SealedSecrets Controller
    ↓
Traefik (ingress)
    ↓
cert-manager (TLS)
    ↓
PostgreSQL, Redis
    ↓
Keycloak (SSO)
    ↓
oauth2-proxy (auth middleware)
    ↓
Ollama (CPU/GPU), LiteLLM
    ↓
Open WebUI, n8n, SearXNG
```

**Why**: SealedSecrets must decrypt secrets → Traefik provides ingress → cert-manager issues TLS → Databases boot → SSO available → Auth middleware ready → AI backends start → AI frontends connect

### Secrets Management

**File Locations**: `argocd/sealed-secrets/*.yaml`
**Generation Script**: `scripts/setup-keycloak-secrets.sh`
**Decryption**: Automatic by sealed-secrets-controller (namespace-scoped keys)

**Available Secrets**:
- OIDC client credentials (n8n, searxng, litellm, dify, grafana, prometheus, traefik, longhorn)
- OAuth application secrets (GitLab, ArgoCD)
- Database credentials (PostgreSQL)
- API tokens (Keycloak admin, GitLab root)
- GHCR (GitHub Container Registry) pull secrets

**Rotation**: `scripts/secrets_manager.py rotate`

### MCP (Model Context Protocol) Servers

**Deployment**: `helm/mcp-servers/`
**Endpoint**: `http://mcp-servers.self-hosted-ai:8000/mcp`

| Server | Purpose | Authentication |
|--------|---------|----------------|
| filesystem | Read/write workspace files | None (RBAC-scoped) |
| git | Repository operations | None (uses pod ServiceAccount) |
| fetch | HTTP requests | None |
| memory | Knowledge graph storage | None (persistent volume) |
| duckduckgo | Web search | None |
| sequential-thinking | Reasoning chains | None |
| gitlab | GitLab API operations | Uses K8s secret token |
| postgres | Database queries | Uses cluster PostgreSQL |
| kubernetes | Read-only K8s access | Uses ServiceAccount |

**Configuration**: `helm/mcp-servers/values.yaml`

### Resource Quotas & Limits

**File**: `helm/resource-quotas/quotas.yaml`, `helm/resource-quotas/limit-ranges.yaml`

| Namespace | CPU Request/Limit | Memory Request/Limit | Storage |
|-----------|-------------------|----------------------|---------|
| `self-hosted-ai` | 4-16 cores | 8-32Gi | 100Gi |
| `gpu-workloads` | 2-8 cores | 4-32Gi | 50Gi |
| `monitoring` | 1-4 cores | 2-8Gi | 20Gi |
| `automation` | 1-2 cores | 1-4Gi | 10Gi |

**LimitRanges**: Default container requests (100m CPU, 128Mi memory) and limits (1 core, 1Gi memory)

### Network Topology

**Ingress**: Traefik on homelab node (192.168.1.170)
**DNS**: `*.vectorweight.com` → 192.168.1.170
**TLS**: Self-signed CA (cert-manager) with wildcard certificate

**External Access** (via HTTPS):
- `https://ai.vectorweight.com` → Open WebUI
- `https://llm.vectorweight.com` → LiteLLM
- `https://n8n.vectorweight.com` → n8n
- `https://argocd.vectorweight.com` → ArgoCD
- `https://grafana.vectorweight.com` → Grafana
- `https://search.vectorweight.com` → SearXNG
- `https://git.vectorweight.com` → GitLab

**Internal Access** (ClusterIP):
- `ollama.self-hosted-ai:11434` → Ollama CPU
- `ollama-gpu.gpu-workloads:11434` → Ollama GPU (forward to 192.168.1.99:11434)
- `postgresql.self-hosted-ai:5432` → PostgreSQL
- `redis.self-hosted-ai:6379` → Redis

**GPU Worker** (Standalone Docker, 192.168.1.99):
- `http://192.168.1.99:11434` → Ollama GPU
- `http://192.168.1.99:8188` → ComfyUI
- `http://192.168.1.99:9000` → Whisper STT

---

## 🤖 Claude Code Integration

### Memory System

This documentation index is referenced in:
- **User Memory**: `~/.claude/CLAUDE.md` (cross-project context)
- **Project Memory**: `.claude/CLAUDE.md` or `CLAUDE.md` (root) - team-shared
- **Local Memory**: `.claude/CLAUDE.local.md` (personal overrides, gitignored)

**Auto Memory**: `/home/kang/.claude/projects/-home-kang-Documents-projects-github-homelab-cluster-self-hosted-ai/memory/MEMORY.md`

### Sub-Agents (Execution)

Defined in `.claude/agents/`:

| Agent | Model | Tools | Use Case |
|-------|-------|-------|----------|
| **k8s-validator** | Haiku | Bash, Read, Grep | Fast manifest validation, dry-run checks |
| **python-test-runner** | Haiku | Bash, Read | Run pytest, report failures |
| **argocd-sync-monitor** | Sonnet | Bash, Read, Grep | Monitor ArgoCD sync, troubleshoot failures |

**Invocation**: Automatic via hooks in `.claude/settings.json`

### Skills (Guidance)

**Directory**: `.claude/skills/` (planned)
**Purpose**: Reusable workflow checklists (unlike sub-agents, skills run in main context)

Examples:
- `git-commit-workflow` - GPG-signed conventional commits
- `deploy-to-k8s` - ArgoCD sync procedure
- `testing-workflow` - Pre-commit validation

### Hooks (Automation)

Defined in `.claude/settings.json`:

**Pre-Tool Hooks**:
- Before `Bash(kubectl apply *)` → Run `k8s-validator` sub-agent
- Before `Bash(git push *)` → Run `task validate:all`

**Session Hooks**:
- `onSessionStart` → `~/.claude/hooks/setup-workspace.sh`
- `onSessionEnd` → Cleanup script

### Recommended Usage Patterns

**For Codebase Navigation**:
1. Read this INDEX.md first (fast context build)
2. Jump to specific docs using "By Task" matrix
3. Use Ctrl+F to search by keyword across all docs

**For Code Changes**:
1. Check [ARCHITECTURE.md](../ARCHITECTURE.md) for principles/ADRs
2. Review [CONTRIBUTING.md](../CONTRIBUTING.md) for workflow
3. Validate with `task validate:all` (or let hooks run it)

**For Deployment**:
1. Read [docs/DEPLOYMENT.md](DEPLOYMENT.md) for procedures
2. Check [OPERATIONS.md](../OPERATIONS.md) for endpoints
3. Monitor with `argocd-sync-monitor` sub-agent

**For Debugging**:
1. Check [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for known issues
2. Use [OPERATIONS.md](../OPERATIONS.md) troubleshooting commands
3. Review logs with `kubectl logs` or Grafana

---

## 🔄 Maintenance

### Keeping This Index Updated

**Automated Updates**:
- `scripts/rag_index.py` generates RAG embeddings for all docs
- Pre-commit hook validates doc links (planned)
- CI job regenerates this INDEX on doc changes (planned)

**Manual Updates**:
- When adding new docs: Add entry in appropriate section above
- When changing directory structure: Update "Codebase Structure Map"
- When adding service: Update "Namespaces" and "Service Dependencies"

**Validation**:
```bash
# Check for broken internal links
grep -oP '\[.*?\]\(\K[^)]+' docs/INDEX.md | while read link; do
  [ -f "$link" ] || [ -f "docs/$link" ] || echo "BROKEN: $link"
done

# Generate RAG index
uv run scripts/rag_index.py generate
```

### Token Budget Analysis

**Total Tokens** (approximate):
- Core Docs (ARCHITECTURE + OPERATIONS + README + CONTRIBUTING): ~3,400
- Deployment Docs (DEPLOYMENT + implementation-guide): ~4,200
- Specialized Docs (VERIFICATION_REPORT + API_RATE_LIMITS_REPORT): ~3,000
- **This INDEX**: ~3,000

**Total Documentation Corpus**: ~13,600 tokens (well within Claude's 200k context)

**Optimization Strategy**:
- This INDEX front-loads context (summaries + file locations)
- Agents can selectively read full docs based on task
- RAG index enables semantic search without loading all docs

---

## 📌 Quick Access Cheatsheet

**Most Referenced Files** (bookmark these):

1. [ARCHITECTURE.md](../ARCHITECTURE.md) - System design authority
2. [OPERATIONS.md](../OPERATIONS.md) - Daily ops runbook
3. [docs/DEPLOYMENT.md](DEPLOYMENT.md) - Deployment procedures
4. [README.md](../README.md) - Project entry point
5. [CONTRIBUTING.md](../CONTRIBUTING.md) - Git workflow
6. This INDEX - Navigation guide

**Most Used Commands**:
```bash
# Cluster health
kubectl get nodes && kubectl get pods -A | grep -v Running

# ArgoCD sync
argocd app list && argocd app sync <app-name>

# Validation
task validate:all

# Secrets
scripts/setup-keycloak-secrets.sh && kubectl get sealedsecrets -A

# Logs
kubectl logs -f deployment/<name> -n <namespace>

# Models
uv run scripts/sync_models.py list
```

**Most Used URLs**:
- ArgoCD: https://argocd.vectorweight.com
- Open WebUI: https://ai.vectorweight.com
- Grafana: https://grafana.vectorweight.com
- n8n: https://n8n.vectorweight.com

---

**End of Index** | [Report Issues](https://github.com/tzervas/self-hosted-ai/issues) | Last Updated: 2026-02-06
