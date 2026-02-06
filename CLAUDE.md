# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Constitution

This is a **Self-Hosted AI Platform** providing secure, private AI infrastructure without reliance on external services.

> **Migration Note:** This platform has been converted from Docker Compose v2 to Kubernetes (k3s) with Helm charts and ArgoCD GitOps deployment. Legacy Docker Compose files are preserved in the `archive/docker-compose-legacy` branch. Production uses `argocd/` and `helm/`.

The guiding principles are defined in ARCHITECTURE.md:

1. **Privacy First**: All inference local, no telemetry, self-contained operation
2. **Security by Design**: Zero plaintext secrets (SealedSecrets), defense in depth, least privilege
3. **Infrastructure as Code**: GitOps via ArgoCD, all state in Git, declarative configuration
4. **Operational Excellence**: Observable, automated, documented, resilient
5. **Developer Experience**: Local-first, consistent tooling, AI-augmented workflows

## Build and Development Commands

### Task Runner (Taskfile.yaml)

```bash
# Setup development environment
task setup:dev

# Linting and formatting
task lint                    # Run all pre-commit hooks
task lint:fix                # Run with auto-fix

# Validation
task validate:helm           # Lint all Helm charts
task validate:manifests      # Validate K8s manifests with kubeconform
task validate:policies       # Validate Kyverno policies
task validate:all            # Run all validation

# Security scanning
task security:trivy          # Trivy config scan
task security:secrets        # Detect secrets in codebase
```

### Python (uv package manager)

```bash
# Install dependencies
uv sync

# Run scripts
uv run scripts/sync_models.py list
uv run scripts/secrets_manager.py generate
uv run scripts/backup.py create --all

# Run tests
uv run pytest tests/
uv run pytest tests/test_core_base.py -v    # Single test file
uv run pytest -k "test_function_name"        # Single test
```

### Rust Agents (rust-agents/)

```bash
cd rust-agents
cargo build --release
cargo test
cargo clippy -- -D warnings
cargo fmt --check
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit install --hook-type commit-msg
pre-commit run --all-files
```

## Architecture Overview

### Deployment Modes

**Kubernetes (production - primary)**:
- ArgoCD GitOps with App-of-Apps pattern in `argocd/`
- Helm charts in `helm/` directory
- Sync waves control deployment order (-2 to 7)
- Two-node k3s cluster: akula-prime (control plane + GPU) + homelab (worker)

**Docker Compose (archived)**:
Legacy Docker Compose configurations preserved in `archive/docker-compose-legacy` branch for reference.

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Open WebUI | Chat interface | helm/open-webui/, workstation/, server/ |
| LiteLLM | OpenAI-compatible API gateway | helm/litellm/ |
| Ollama | LLM inference (CPU/GPU) | helm/ollama/, gpu-worker/ |
| SearXNG | Privacy-focused search | helm/searxng/ |
| n8n | Workflow automation | helm/n8n/ |
| Agent Server | FastAPI agent orchestration | agent-server/ |
| Python Agents | Specialized AI agents | agents/ |
| Rust Agents | High-performance agent runtime | rust-agents/ |

### Network Topology

- **akula-prime** (192.168.1.99): k3s control plane + GPU worker (RTX 5080 16GB), runs ArgoCD, Traefik, GPU Ollama
- **homelab** (192.168.1.170): k3s worker node, runs all primary workloads (Open WebUI, LiteLLM, n8n, PostgreSQL, Redis, etc.)

Models are stored on homelab NFS share (`/data/models`) and mounted by GPU worker via NFS PV/PVC (`shared-models`).

## Git Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only |
| `dev` | Integration branch, merges to main via manual PR |
| `feature/*` | New features → dev |
| `fix/*` | Bug fixes → dev |

**Commit format**: Conventional Commits enforced by pre-commit hook.
```
feat(scope): description
fix(scope): description
docs: description
```

## Code Standards

### Python

- Python 3.11+ required
- Ruff for linting/formatting (line length: 100)
- Type hints encouraged, mypy for checking
- Tests with pytest, coverage reports to `htmlcov/`

### Shell Scripts

- `#!/usr/bin/env bash` with `set -euo pipefail`
- 2-space indentation (shfmt enforced)
- Quote all variables: `"$var"`

### Kubernetes/Helm

- No `version` attribute in docker-compose (deprecated)
- Helm charts in `helm/<service>/` with Chart.yaml and values.yaml
- ArgoCD applications in `argocd/applications/`

## Secret Management

All secrets use SealedSecrets (encrypted in Git, decrypted by cluster):

```bash
# Generate secrets
uv run scripts/secrets_manager.py generate

# Seal a secret
kubectl create secret generic name key=value --dry-run=client -o yaml | kubeseal -o yaml
```

Local credential documentation goes in `ADMIN_CREDENTIALS.local.md` (gitignored).

## ArgoCD Sync Waves

Infrastructure deploys in waves (see ARCHITECTURE.md ADR-002):
- Wave -2: SealedSecrets (foundation)
- Wave -1: cert-manager, Longhorn, Linkerd CRDs
- Wave 0: Traefik, GPU operator, resource quotas
- Wave 1: Service mesh, Kyverno policies
- Wave 2: Prometheus monitoring
- Wave 5: AI backend (Ollama, LiteLLM)
- Wave 6: AI frontend (Open WebUI, n8n)
- Wave 7: CI/CD runners (ARC, GitLab)

## Testing

```bash
# Python agents
uv run pytest tests/ -v --cov=agents --cov-report=html

# Helm chart linting
task validate:helm

# Full validation suite
task validate:all

# Security checks
task security:trivy
```

## File Organization

```
self-hosted-ai/
├── agents/                  # Python agent framework
│   ├── core/               # Base classes, task, workflow
│   └── specialized/        # Research, dev, review, testing, docs agents
├── agent-server/           # FastAPI server for agent orchestration
├── rust-agents/            # Rust high-performance agent runtime
├── argocd/                 # ArgoCD applications and helm configs
│   └── applications/       # Individual app manifests
├── helm/                   # Helm charts for K8s services
├── scripts/                # Automation scripts (shell + Python via uv)
├── policies/               # Kyverno and network policies
├── workflows/              # n8n workflow definitions
├── config/                 # Configuration files (LiteLLM, models, etc.)
├── docs/                   # Documentation and archives
└── tests/                  # pytest test suite
```

---

## Sub-Agents & Parallel Execution

This project uses specialized sub-agents with right-sized models for optimal performance.

### Available Sub-Agents

| Agent | Model | Speed | Use Case |
|-------|-------|-------|----------|
| **k8s-validator** | Haiku | Fast | Validate manifests, dry-run checks |
| **python-test-runner** | Haiku | Fast | Run pytest, report failures only |
| **argocd-sync-monitor** | Sonnet | Complex | Monitor ArgoCD, troubleshoot sync issues |

### Model Selection Strategy

- **Haiku**: Validation, testing, simple checks (70% cost reduction)
- **Sonnet**: Deployment monitoring, complex analysis, troubleshooting
- **Opus**: (reserve for) Architecture design, major refactoring

### Parallel Execution Patterns

#### Pattern 1: Validation Pipeline (Non-Blocking)

Before applying K8s changes:

```
Run k8s-validator and python-test-runner in parallel
```

Spawns 2 Haiku sub-agents concurrently:
- **k8s-validator**: Validates all manifests, Helm charts
- **python-test-runner**: Runs pytest suite

Both report back when done. **2-3x faster** than sequential.

#### Pattern 2: Deploy + Monitor

```
Apply ArgoCD changes, then monitor with argocd-sync-monitor while validating in background
```

Workflow:
1. Apply manifests
2. **argocd-sync-monitor** (Sonnet) watches deployment
3. **k8s-validator** (Haiku) validates in background
4. Both report status

#### Pattern 3: Multi-App Deployment

For multiple services:

```
Deploy ollama, litellm, and open-webui apps in parallel using separate deployment monitors
```

Spawns 3 argocd-sync-monitor instances, each watching one app. Results aggregated.

### Automatic Sub-Agent Invocation

Sub-agents are invoked automatically via hooks:

**Before `kubectl apply`**:
→ `k8s-validator` runs dry-run validation (configured in `.claude/settings.json`)

**Before `git push`**:
→ `task validate:all` + `python-test-runner` run automatically

**After ArgoCD sync**:
→ `argocd-sync-monitor` tracks deployment health

### Background vs Foreground

**Foreground** (blocks main conversation):
- Interactive deployments requiring user decisions
- Complex troubleshooting needing your input
- ArgoCD sync failures requiring manual intervention

**Background** (non-blocking):
- Validation (manifests, Helm, policies)
- Test runs (pytest, integration tests)
- Health monitoring (post-deployment checks)
- Metrics collection

Request background execution:
```
Validate all Helm charts in the background while I work on the Python agents
```

Or press **Ctrl+B** to background a running sub-agent.

### Example: Parallel Pre-Deploy Workflow

```
I'm ready to deploy these Helm chart changes. Validate everything first.
```

Claude spawns:
1. `k8s-validator` (Haiku, background) - Validates manifests
2. `python-test-runner` (Haiku, background) - Runs agent tests

Both run concurrently, report back:
```
✅ K8s Validation: Pass (12 charts, 45 manifests)
✅ Python Tests: Pass (127/127 tests)
🚀 Safe to deploy!
```

Then proceeds with deployment.

### Cost & Performance Optimization

**Using Haiku for validation/testing:**
- **70% cost reduction** vs Sonnet
- **3-5x faster response** for simple checks
- **Parallel execution** - multiple Haiku agents cost less than 1 Sonnet

**Using Sonnet for monitoring:**
- **Complex analysis** of sync failures
- **Troubleshooting** deployment issues
- **Log analysis** for root cause investigation

### Integration with Python Agents

This project also has **Python agents** (`agents/specialized/`). These are different from Claude Code sub-agents:

| Type | Language | Use Case |
|------|----------|----------|
| **Claude Sub-Agents** | AI-powered workflows | Development, testing, deployment |
| **Python Agents** | Python classes | Runtime task execution, API orchestration |

They complement each other:
- **Sub-agents** help you develop and deploy
- **Python agents** execute tasks in production

### Automation Summary

```
┌─────────────────────────────────────────────────────┐
│  kubectl apply -f helm/                             │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │  Pre-apply Hook  │
        │  (settings.json) │
        └────────┬─────────┘
                 │
     ┌───────────┴────────────┐
     │                        │
┌────▼─────────┐  ┌──────────▼─────┐
│ K8s          │  │ Helm           │
│ Validator    │  │ Validator      │
│ (Haiku)      │  │ (Haiku)        │
└────┬─────────┘  └──────┬─────────┘
     │                   │
     └──────────┬────────┘
                │
        ┌───────▼────────┐
        │  ✅ Both Pass  │
        │  → Apply       │
        └───────┬────────┘
                │
        ┌───────▼──────────┐
        │  ArgoCD Sync     │
        │  Monitor         │
        │  (Sonnet)        │
        └──────────────────┘
```

---

## Advanced Patterns

### Parallel Multi-Service Deployment

Deploy entire stack with parallel monitoring:

```
Deploy the AI stack (ollama, litellm, open-webui, searxng) and monitor each service in parallel
```

Spawns 4 argocd-sync-monitor instances, each watching one service. All report health simultaneously.

### Progressive Validation

Layer validation from fast to thorough:

```
1. Quick YAML lint (Haiku, 5 sec)
2. Helm validation (Haiku, 10 sec)
3. Full integration tests (Sonnet, 60 sec)
```

Each layer runs only if previous passes. Fail fast for maximum efficiency.

### Continuous Monitoring

Leave a sub-agent running in background:

```
Monitor the ollama deployment continuously and alert if pods crash
```

`argocd-sync-monitor` stays active, watches for failures, interrupts if issues detected.

---

## Skills Integration

While sub-agents handle execution, skills provide guidance. Example:

**Skill**: `k8s-deployment` (workflow checklist)
**Sub-Agent**: `argocd-sync-monitor` (executes and monitors)

Use skill for "how to deploy", use sub-agent for "do the deployment".

---

## Complete Workflow Example

**Goal**: Deploy new LiteLLM configuration

**Step 1: Modify Configuration**
```
Edit helm/litellm/values.yaml with new model configuration
```

**Step 2: Validate in Parallel**
```
Validate the Helm chart and run Python tests in parallel
```

→ Spawns `k8s-validator` + `python-test-runner` (both Haiku, background)

**Step 3: Deploy**
```
Deploy litellm with monitoring
```

→ Applies change, spawns `argocd-sync-monitor` (Sonnet)

**Step 4: Verify**
```
✅ Validation: Pass
✅ Tests: Pass
✅ Deployment: Healthy
🎉 LiteLLM updated successfully!
```

**Total time**: ~2 minutes (vs 5-7 minutes sequential)
**Cost**: 60% reduction using Haiku for validation/tests

---

Everything automated, parallelized, and right-sized for speed and cost.
