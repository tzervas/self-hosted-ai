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
