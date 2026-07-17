# Self-Hosted AI Platform

<!-- FLEET-BADGES:BEGIN -->
[![CI](https://github.com/tzervas/self-hosted-ai/actions/workflows/fleet-ci.yml/badge.svg?branch=main)](https://github.com/tzervas/self-hosted-ai/actions/workflows/fleet-ci.yml?query=branch%3Amain)
[![Security](https://github.com/tzervas/self-hosted-ai/actions/workflows/fleet-security.yml/badge.svg?branch=main)](https://github.com/tzervas/self-hosted-ai/actions/workflows/fleet-security.yml?query=branch%3Amain)
<!-- FLEET-BADGES:END -->

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s-326CE5?logo=kubernetes&logoColor=white)](https://k3s.io/)
[![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-EF7B4D?logo=argo&logoColor=white)](https://argoproj.github.io/cd/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

A production-ready, self-hosted AI platform running on Kubernetes with GitOps deployment, unified LLM routing, workflow automation, and AI agent tool integration via Model Context Protocol (MCP).

> **Note:** This platform has been migrated from Docker Compose to Kubernetes (k3s) with Helm charts and ArgoCD GitOps deployment. Legacy Docker Compose configurations are preserved in the `archive/docker-compose-legacy` branch. Production deployments use the `argocd/` and `helm/` directories.

## ✨ Features

- **Multi-Model LLM Routing** - LiteLLM proxy for unified API across Ollama, OpenAI-compatible backends
- **Modern Web UI** - Open WebUI with chat, RAG, and multi-model support
- **Workflow Automation** - n8n for AI-powered automation workflows
- **GitOps Deployment** - ArgoCD for declarative, version-controlled infrastructure
- **MCP Integration** - AI agent tools via Model Context Protocol servers
- **Monitoring Stack** - Prometheus + Grafana for observability
- **Self-Signed TLS** - Internal CA for secure HTTPS without external dependencies
- **Distributed GPU Inference** - CPU cluster + dedicated GPU worker node

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Self-Hosted AI Platform                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Control Plane (k3s) + GPU                        │    │
│  │                    akula-prime: 192.168.1.99                        │    │
│  │                                                                     │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │    │
│  │  │   ArgoCD    │  │  Ollama GPU │  │        Traefik v3           │ │    │
│  │  │  (GitOps)   │  │ RTX 5080    │  │  (Ingress + Self-Signed CA) │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                        │                                     │
│                                        │ LAN (Flannel VXLAN)                 │
│                                        ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Worker Node (Primary Workloads)                   │    │
│  │                    homelab: 192.168.1.170                           │    │
│  │                                                                     │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │    │
│  │  │  Open WebUI │  │   LiteLLM   │  │     n8n     │  │  Grafana  │  │    │
│  │  │   :443      │  │   :4000     │  │   :5679     │  │  :3003    │  │    │
│  │  │  ai.domain  │  │ llm.domain  │  │ n8n.domain  │  │ grafana.  │  │    │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └───────────┘  │    │
│  │         │                │                                         │    │
│  │         └────────────────┼─────────────────────────────────┐       │    │
│  │                          │                                 │       │    │
│  │  ┌─────────────┐  ┌──────┴──────┐  ┌─────────────┐  ┌─────┴─────┐ │    │
│  │  │   Ollama    │  │  PostgreSQL │  │   SearXNG   │  │  MCPO     │ │    │
│  │  │   (CPU)     │  │  (n8n DB)   │  │  (Search)   │  │  (Tools)  │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │    │
│  │                                                                     │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │    │
│  │  │    Redis    │  │  Keycloak   │  │     Longhorn Storage        │ │    │
│  │  │   (Cache)   │  │   (SSO)     │  │    (NFS: /data/models)      │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Hardware

| Node | Role | Specs | IP |
|------|------|-------|----|
| **akula-prime** | Control Plane + GPU | Intel 14700K, 48GB DDR5, RTX 5080 (16GB) | 192.168.1.99 |
| **homelab** | Worker (Primary Workloads) | Dual E5-2660v4 (28c/56t), 120GB DDR4 | 192.168.1.170 |

## 🚀 Quick Start

### Prerequisites

- k3s cluster (v1.28+)
- kubectl configured
- Helm 3.x
- Python 3.12+ with [uv](https://docs.astral.sh/uv/)

### 1. Clone Repository

```bash
git clone https://github.com/tzervas/self-hosted-ai.git
cd self-hosted-ai
```

### 2. Install Python Tools

```bash
cd scripts
uv sync
source .venv/bin/activate
```

### 3. Bootstrap Cluster

```bash
# Deploy with ArgoCD (GitOps)
kubectl apply -k argocd/

# Or bootstrap services manually
shai-bootstrap all
```

### 4. Generate Credentials

```bash
# Generate secure credentials
shai-secrets generate

# Export to agent-readable format
shai-secrets export --format markdown

# View credentials
shai-secrets show
```

### 5. Validate Deployment

```bash
shai-validate all
```

## 📍 Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Open WebUI | `https://ai.vectorweight.com` | Chat interface |
| LiteLLM | `https://llm.vectorweight.com` | LLM API proxy |
| n8n | `https://n8n.vectorweight.com` | Workflow automation |
| Grafana | `https://grafana.vectorweight.com` | Monitoring dashboards |
| SearXNG | `https://search.vectorweight.com` | Privacy-respecting search |
| GitLab | `https://git.vectorweight.com` | Git repository |
| ArgoCD | `https://argocd.vectorweight.com` | GitOps dashboard |

> **Note:** Install the self-signed CA certificate in your browser for HTTPS access.

## 🛠️ CLI Tools

All operations use Python scripts managed with uv:

```bash
# Main CLI
shai --help

# Bootstrap services
shai-bootstrap all           # Full bootstrap
shai-bootstrap services      # Configure via APIs
shai-bootstrap models        # Pull AI models

# Validate cluster
shai-validate all            # All checks
shai-validate dns            # DNS resolution
shai-validate tls            # TLS certificates  
shai-validate services       # API health
shai-validate kubernetes     # K8s resources

# Secrets management
shai-secrets generate        # Generate all credentials
shai-secrets export          # Export to markdown
shai-secrets rotate          # Rotate all secrets
shai-secrets show            # Display credentials
```

## 🤖 MCP Servers

AI agents can access tools via Model Context Protocol:

| Server | Purpose | API Key Required |
|--------|---------|------------------|
| filesystem | Read/write workspace files | No |
| git | Repository operations | No |
| fetch | HTTP requests | No |
| memory | Knowledge graph storage | No |
| time | Time/timezone utilities | No |
| duckduckgo | Web search | No |
| sequential-thinking | Reasoning chains | No |
| gitlab | GitLab API operations | No (uses token) |
| postgres | Database queries | No (uses cluster DB) |
| kubernetes | K8s read-only access | No (uses ServiceAccount) |

Access via MCPO proxy at `http://mcp-servers.self-hosted-ai:8000/mcp`.

## 📁 Project Structure

```
.
├── argocd/                   # ArgoCD Applications
│   ├── applications/         # App-of-Apps definitions
│   ├── helm/                 # Helm value overrides
│   └── secrets/              # SealedSecrets
├── config/                   # Configuration files
│   ├── litellm-config.yml    # LiteLLM model routing
│   ├── models-manifest.yml   # Models to pull
│   └── n8n-workflows/        # n8n workflow exports
├── helm/                     # Helm charts
│   ├── server/               # Main stack umbrella chart
│   ├── mcp-servers/          # MCP tool servers
│   └── */                    # Individual service charts
├── scripts/                  # Python automation
│   ├── lib/                  # Shared libraries
│   ├── bootstrap.py          # Service configuration
│   ├── validate_cluster.py   # Health checks
│   └── secrets_manager.py    # Credential management
├── docs/                     # Documentation
├── ARCHITECTURE.md           # Design principles & ADRs
├── OPERATIONS.md             # Runbook & maintenance
└── CREDENTIALS.local.md      # Generated credentials (gitignored)
```

## 📚 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Design principles, ADRs, constitution
- [OPERATIONS.md](OPERATIONS.md) - Operations runbook, maintenance procedures
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

## 🔒 Security

- Self-signed internal CA (no external certificate dependencies)
- SealedSecrets for encrypted secrets in Git
- No external API keys required for core functionality
- RBAC-scoped MCP server access
- Credentials stored locally in `*.local.yaml` / `*.local.md` (gitignored)

### Installing the CA Certificate

```bash
# Export CA certificate
kubectl get secret vectorweight-root-ca -n cert-manager -o jsonpath='{.data.tls\.crt}' | base64 -d > ca.crt

# Linux (system-wide)
sudo cp ca.crt /usr/local/share/ca-certificates/vectorweight-ca.crt
sudo update-ca-certificates

# Or import into browser directly
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
