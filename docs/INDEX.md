# Self-Hosted AI Platform - Documentation Index

**Last Updated**: 2026-02-21
**Purpose**: Token-efficient navigation guide for Claude Code and AI agents
**Index Token Count**: ~3,000 tokens (vs ~13,600 for full corpus = 78% reduction)

> **🚨 Emergency Fast-Path**: Production down? Jump to [Critical Issues](#-emergency-procedures) section below.

> **Quick Start**: Looking for something specific? Use Ctrl+F to search by keyword OR search by trigger words (deploy, debug, sso, gpu, model, workflow). Each section links to detailed docs with concise summaries optimized for context windows.

---

## 🚨 Emergency Procedures (Fast-Path)

**Production Service Down?**
1. Check [OPERATIONS.md](../OPERATIONS.md) lines 77-150 (troubleshooting commands)
2. Run: `kubectl get pods -A | grep -v Running`
3. Check ArgoCD: `argocd app list`
4. View logs: `kubectl logs -f deployment/<name> -n <namespace>`

**Deployment Failing?**
1. Check [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for known issues
2. Run: `task validate:all`
3. Review sync waves: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-002

**Security Incident?**
1. [ARCHITECTURE.md](../ARCHITECTURE.md) lines 212-245 (security model)
2. Check sealed secrets: `kubectl get sealedsecrets -A`
3. Review policies: `helm/resource-quotas/`, `policies/`

**Trigger Words for Fast Search**: critical, emergency, down, failing, error, crash, stuck, broken

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
| **Install CA Certificate** | [docs/CERTIFICATE_TRUST_GUIDE.md](CERTIFICATE_TRUST_GUIDE.md) | [docs/CERTIFICATE_QUICK_REFERENCE.md](CERTIFICATE_QUICK_REFERENCE.md) | `scripts/install-ca-certificate.sh all` |
| **Fix TLS Validation** | [docs/SECURITY_TLS_VALIDATION_AUDIT.md](SECURITY_TLS_VALIDATION_AUDIT.md) | `scripts/fix-tls-validation.py` | `uv run scripts/fix-tls-validation.py fix` |
| **Add AI Model** | [config/models-manifest.yml](../config/models-manifest.yml) | `helm/ollama/values.yaml` | `scripts/sync_models.py` |
| **Create Workflow** | [workflows/README.md](../workflows/README.md) | `config/n8n-workflows/*.json` | n8n UI at `https://n8n.vectorweight.com` |
| **Debug Deployment** | [OPERATIONS.md](../OPERATIONS.md) Troubleshooting | [docs/VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) | `kubectl logs`, `argocd app get` |
| **Query Traces** | [OPERATIONS.md](../OPERATIONS.md) Distributed Tracing | Grafana Explore → Tempo datasource | TraceQL queries, trace correlation |
| **Rotate Secrets** | [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-006 | `argocd/sealed-secrets/` | `scripts/secrets_manager.py rotate` |
| **Scale Resources** | [helm/resource-quotas/](../helm/resource-quotas/) | `helm/*/values.yaml` (resources sections) | `kubectl top`, `kubectl scale` |
| **Monitor Cluster** | [OPERATIONS.md](../OPERATIONS.md) | Grafana dashboards | `https://grafana.vectorweight.com` |

---

## 📚 Core Documentation (Token-Optimized Summaries)

### Constitution & Principles

#### [ARCHITECTURE.md](../ARCHITECTURE.md) (3,833 tokens)
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

#### [OPERATIONS.md](../OPERATIONS.md) (1,528 tokens)
**Purpose**: Daily ops runbook and service access
**Key Sections**:
- **Service Endpoints** (7-20): All HTTPS URLs with purposes
- **Internal Services** (22-30): ClusterIP services and ports
- **GPU Worker** (32-56): Standalone workstation at 192.168.1.99, rootless Podman runtime
- **Quick Commands** (85-): Cluster health, ArgoCD sync, logs
- **Distributed Tracing** (258-371): Tempo, OpenObserve, OTel Collector, TraceQL queries, trace-to-logs correlation
- **Security** (374-444): Pod Security Standards (PSS baseline), NetworkPolicy, rootless Podman security model
- **Troubleshooting** (168-): Common issues and solutions

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md)
**When to Read**: First day on platform, debugging, ops tasks, tracing analysis, security review

### Getting Started

#### [README.md](../README.md) (449 tokens)
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

#### [CONTRIBUTING.md](../CONTRIBUTING.md) (1,808 tokens)
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

#### [GITLAB_ACCESS_INSTRUCTIONS.md](../GITLAB_ACCESS_INSTRUCTIONS.md) (919 tokens)
**Purpose**: GitLab deployment with SSO integration
**Key Sections**:
- **Keycloak SSO Setup**: Realm configuration, OIDC clients
- **GitLab OAuth**: Integration with Keycloak
- **Credential Retrieval**: Scripts to extract secrets
- **Access URLs**: GitLab, Keycloak endpoints

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-006
**When to Read**: Setting up GitLab, configuring SSO

#### [docs/CERTIFICATE_TRUST_GUIDE.md](CERTIFICATE_TRUST_GUIDE.md) (~3,200 tokens)
**Purpose**: Complete guide for CA certificate installation and TLS validation
**Key Sections**:
- **Automated Installation**: `install-ca-certificate.sh` for all platforms
- **Service Configuration**: Fix oauth2-proxy and Grafana TLS validation
- **Browser Setup**: Firefox, Chrome certificate import
- **Verification**: Testing and troubleshooting TLS trust
- **Certificate Rotation**: Maintenance procedures

**Dependencies**: [docs/SECURITY_TLS_VALIDATION_AUDIT.md](SECURITY_TLS_VALIDATION_AUDIT.md)
**When to Read**: Setting up workstations, fixing TLS errors, certificate rotation
**Quick Reference**: [docs/CERTIFICATE_QUICK_REFERENCE.md](CERTIFICATE_QUICK_REFERENCE.md) (printable cheat sheet)

#### [docs/SECURITY_TLS_VALIDATION_AUDIT.md](SECURITY_TLS_VALIDATION_AUDIT.md) (~2,800 tokens)
**Purpose**: Security audit findings for CWE-295 vulnerabilities
**Severity**: HIGH (MITM attack vectors from disabled TLS validation)
**Key Sections**:
- **Vulnerability Summary**: 3 services with insecureSkipVerify (ArgoCD fixed, 2 remain)
- **Attack Scenarios**: Detailed MITM attack paths
- **Remediation Plan**: Automated fixes via `fix-tls-validation.py`
- **Compliance**: CIS, NIST, PCI-DSS, SOC 2 implications

**Dependencies**: None (foundational security)
**When to Read**: Security review, compliance audit, before deploying authentication changes
**Automation**: `uv run scripts/fix-tls-validation.py fix`

#### [docs/SECURITY_ARGOCD_TLS_FIX.md](SECURITY_ARGOCD_TLS_FIX.md) (~1,800 tokens)
**Purpose**: Detailed ArgoCD TLS validation fix documentation
**Status**: ✅ FIXED (replaced `insecureSkipVerify: true` with `rootCA`)
**Key Sections**:
- **Vulnerability**: CWE-295, MITM attack vector
- **Fix Implementation**: Helm template helper for CA trust
- **Verification**: Testing procedures
- **Migration Guide**: Steps for other services

**Dependencies**: [docs/SECURITY_TLS_VALIDATION_AUDIT.md](SECURITY_TLS_VALIDATION_AUDIT.md)
**When to Read**: Understanding ArgoCD security fix, applying to other services

#### [docs/CERTIFICATE_QUICK_REFERENCE.md](CERTIFICATE_QUICK_REFERENCE.md) (~600 tokens)
**Purpose**: Quick reference cheat sheet for certificate operations
**Format**: Command tables, one-liners, emergency procedures
**Key Sections**:
- **Common Commands**: Installation, verification, troubleshooting
- **Status Dashboard**: Check TLS validation across services
- **Security Checklist**: Pre/post deployment validation
- **Emergency Procedures**: Certificate expiry, MITM detection

**Dependencies**: [docs/CERTIFICATE_TRUST_GUIDE.md](CERTIFICATE_TRUST_GUIDE.md)
**When to Read**: Quick lookups, printable reference

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


### Documentation System Docs

#### [DEPLOYMENT.md](DEPLOYMENT.md) (1,259 tokens)
**Purpose**: Complete deployment procedures for k3s cluster
**Key Sections**:
- Architecture Overview (lines 5-30): Network topology
- Prerequisites (lines 32-42): K8s, ArgoCD, tools
- Fresh Deployment (lines 44-): Bootstrap steps
- GPU Worker Setup: Standalone Docker deployment

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md)
**When to Read**: Initial deployment, adding nodes, troubleshooting deploy

#### [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) (1,552 tokens)
**Purpose**: Cluster validation results and known issues
**Key Sections**:
- Enhancements Made (lines 12-74): Recent changes
- Verification Results (lines 76-): Service health, model tests
- Known Issues: Current limitations

**Dependencies**: [OPERATIONS.md](../OPERATIONS.md)
**When to Read**: After deployment, debugging, health checks

#### [API_RATE_LIMITS_REPORT.md](API_RATE_LIMITS_REPORT.md) (4,971 tokens)
**Purpose**: Comprehensive API rate limit analysis across all services
**Key Sections**:
- Service-by-service rate limit documentation
- Request/response patterns
- Optimization strategies

**Dependencies**: None
**When to Read**: Planning API usage, debugging rate limit errors

#### [CLAUDE_OPTIMIZATION_GUIDE.md](CLAUDE_OPTIMIZATION_GUIDE.md) (2,614 tokens)
**Purpose**: Claude Code-specific implementation guide
**Key Sections**:
- Implementation steps (~2 hours)
- ROI analysis (81% token savings)
- Templates (INDEX.md, MEMORY.md)
- Validation scripts

**Dependencies**: This INDEX.md
**When to Read**: Replicating optimization in other Claude projects

#### [UNIVERSAL_AGENT_DOC_OPTIMIZATION.md](UNIVERSAL_AGENT_DOC_OPTIMIZATION.md) (6,280 tokens)
**Purpose**: Framework-agnostic doc optimization for ANY AI agent system
**Key Sections**:
- Universal principles (hierarchical indexing, lazy evaluation)
- Platform integrations (Claude, GPT, Gemini, LangChain, AutoGen, CrewAI)
- Pseudocode implementations
- Migration guide

**Dependencies**: Conceptual foundation for this INDEX
**When to Read**: Applying optimization to non-Claude agent systems

#### [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) (4,420 tokens)
**Purpose**: 12-week phased development plan
**Key Sections**:
- Current State Assessment: What's done, what's broken
- Phase 1-6 (lines 50-): Detailed tasks per phase
- Git Workflow Enforcement: Branch protection rules
- Success Metrics: Per-phase targets

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md), [OPERATIONS.md](../OPERATIONS.md)
**When to Read**: Planning work, understanding priorities, tracking progress

#### [DOCUMENTATION_SYSTEM_REVIEW.md](DOCUMENTATION_SYSTEM_REVIEW.md) (2,018 tokens)
**Purpose**: Production-readiness assessment of doc system
**Key Sections**:
- System Health (lines 10-40): Token accuracy, automation
- Validation Results (lines 50-): Coverage, link integrity
- Recommendations (lines 200-): Action plans

**Dependencies**: All doc system files
**When to Read**: Assessing doc system quality, planning improvements

---

## 🤖 Claude Code Integration Docs

### Claude Agents (Sub-Agents)

#### [.claude/agents/k8s-validator.md](../.claude/agents/k8s-validator.md) (182 tokens)
**Purpose**: Fast Kubernetes manifest validator (Haiku model)
**Tools**: Bash, Read, Grep
**Use Case**: Validate manifests, dry-run checks before `kubectl apply`
**Invocation**: Automatic via hooks in `.claude/settings.json`

#### [.claude/agents/python-test-runner.md](../.claude/agents/python-test-runner.md) (163 tokens)
**Purpose**: Fast Python test runner (Haiku model)
**Tools**: Bash, Read
**Use Case**: Run pytest, report failures before `git push`
**Invocation**: Automatic via pre-push hooks

#### [.claude/agents/argocd-sync-monitor.md](../.claude/agents/argocd-sync-monitor.md) (276 tokens)
**Purpose**: ArgoCD deployment monitor (Sonnet model)
**Tools**: Bash, Read, Grep
**Use Case**: Monitor ArgoCD sync, troubleshoot deployment issues
**Invocation**: Manual or automatic after ArgoCD sync

---

## 📦 Component Documentation

### Python Agents Framework

#### [agents/README.md](../agents/README.md) (347 tokens)
**Purpose**: Python agent framework overview
**Key Sections**:
- Core agents (base classes, task, workflow)
- Specialized agents (research, dev, review, testing, docs)

**Dependencies**: None
**When to Read**: Understanding Python agents, extending framework

### Automation Scripts

#### [scripts/README.md](../scripts/README.md) (1,206 tokens)
**Purpose**: Python automation scripts documentation
**Key Sections**:
- Bootstrap scripts (cluster setup)
- Validation scripts (health checks)
- Secret management (SealedSecrets generation)
- Model sync (Ollama model management)

**Dependencies**: None
**When to Read**: Running automation, understanding scripts

### Workflow Automation

#### [workflows/README.md](../workflows/README.md) (175 tokens)
**Purpose**: n8n workflow documentation
**Key Sections**:
- Available workflows in `config/n8n-workflows/`
- Import/export procedures

**Dependencies**: None
**When to Read**: Creating/modifying n8n workflows

### Helm Charts

#### [helm/README.md](../helm/README.md) (458 tokens)
**Purpose**: Helm charts overview
**Key Sections**:
- Chart structure
- Value overrides
- ArgoCD integration

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-002
**When to Read**: Modifying Helm charts, adding services

### MCP Servers

#### [helm/mcp-servers/README.md](../helm/mcp-servers/README.md) (776 tokens)
**Purpose**: Model Context Protocol servers documentation
**Key Sections**:
- Available MCP servers (filesystem, git, fetch, memory, etc.)
- Configuration
- MCPO proxy setup

**Dependencies**: [ARCHITECTURE.md](../ARCHITECTURE.md) ADR-005
**When to Read**: Configuring MCP tools, adding new servers

### Licenses

#### [third-party-licenses/README.md](../third-party-licenses/README.md) (135 tokens)
**Purpose**: Third-party license information
**Key Sections**: License files for dependencies

**Dependencies**: None
**When to Read**: Compliance, attributions

---

## 🧪 Demo & Research

#### [AI_USE_TECH_DEMO/README.md](../AI_USE_TECH_DEMO/README.md) (~300 tokens est.)
**Purpose**: AI use case demonstration project
**When to Read**: Understanding demo capabilities

#### [AI_USE_TECH_DEMO/docs/DEMO_GUIDE.md](../AI_USE_TECH_DEMO/docs/DEMO_GUIDE.md) (~500 tokens est.)
**Purpose**: Demo walkthrough guide
**When to Read**: Running demos

#### [AI_USE_TECH_DEMO/prelim-research.md](../AI_USE_TECH_DEMO/prelim-research.md) (~200 tokens est.)
**Purpose**: Preliminary research notes
**When to Read**: Historical context

---

## 📚 Archive (Historical Reference)

These docs are archived but kept for historical reference. Not actively maintained.

**Location**: `docs/archive/`

| Document | Purpose | Note |
|----------|---------|------|
| CONTEXT_SUMMARY.md | Historical context | Superseded by ARCHITECTURE.md |
| CLUSTER_DEPLOYMENT_READINESS.md | Old deployment guide | See DEPLOYMENT.md |
| CONTEXT_GATHERING_COMPLETE.md | Old context notes | Historical |
| QUICK_REFERENCE.md | Old quick ref | See INDEX.md |
| QUICKSTART.md | Old quickstart | See DEPLOYMENT.md |
| PRODUCTION_FEATURES.md | Old features list | See README.md |
| DEPLOYMENT.md (archived) | Old deployment | See docs/DEPLOYMENT.md |
| implementation-guide.md (archived) | Old guide | See implementation-guide.md (root) |
| legacy-scripts/README.md | Old scripts | See scripts/README.md |
| self-hosted-ai-*.md | Old context docs | Historical |
| UPGRADE_SUMMARY.md | Migration notes | Docker→K8s migration complete |

**When to Read**: Never (unless researching history)



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
- `https://grafana.vectorweight.com` → Grafana (unified observability UI)
- `https://prometheus.vectorweight.com` → Prometheus
- `https://observe.vectorweight.com` → OpenObserve (logs, metrics, traces)
- `https://search.vectorweight.com` → SearXNG
- `https://git.vectorweight.com` → GitLab

**Internal Access** (ClusterIP):
- `ollama.self-hosted-ai:11434` → Ollama CPU
- `ollama-gpu.gpu-workloads:11434` → Ollama GPU (forward to 192.168.1.99:11434)
- `postgresql.self-hosted-ai:5432` → PostgreSQL
- `redis.self-hosted-ai:6379` → Redis
- `tempo.monitoring:3100` → Tempo (trace storage and query)
- `otel-collector-opentelemetry-collector.monitoring:4318` → OTel Collector (OTLP/HTTP receiver)

**GPU Worker** (Standalone Podman, 192.168.1.99):
- `http://192.168.1.99:11434` → Ollama GPU
- `http://192.168.1.99:8188` → ComfyUI
- `http://192.168.1.99:9000` → Whisper STT
- **Container Runtime**: Rootless Podman (migrated from Docker, PSS baseline hardening)

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
