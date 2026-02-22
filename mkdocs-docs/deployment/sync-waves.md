---
title: Sync Waves
description: ArgoCD sync wave order and dependency management
---

# Sync Waves

ArgoCD deploys services in a specific order using sync waves. Lower wave numbers deploy first.

## Wave Order

```mermaid
graph TB
    W2["Wave -2: Foundation<br/>sealed-secrets"]
    W1["Wave -1: Infrastructure<br/>cert-manager, Longhorn, Linkerd CRDs, VPA"]
    W0["Wave 0: Platform<br/>Traefik, GPU operator, CoreDNS, resource-quotas"]
    W1a["Wave 1: Mesh & Policy<br/>Linkerd control plane, Kyverno"]
    W2a["Wave 2: Monitoring<br/>Prometheus, Alertmanager"]
    W4["Wave 4: Source Control<br/>GitLab"]
    W5["Wave 5: AI Backend<br/>Ollama, Ollama GPU, LiteLLM, PostgreSQL, Redis"]
    W6["Wave 6: AI Frontend<br/>Open WebUI, n8n, SearXNG, MCP servers, Docs"]
    W7["Wave 7: CI/CD<br/>ARC controller, runners (amd64, gpu, arm64)"]

    W2 --> W1 --> W0 --> W1a --> W2a --> W4 --> W5 --> W6 --> W7
```

## Detailed Wave Breakdown

### Wave -2: Foundation

| Service | Purpose |
|---------|---------|
| sealed-secrets | Encrypted secrets in Git -- must exist before any secrets |

### Wave -1: Infrastructure

| Service | Purpose |
|---------|---------|
| linkerd-crds | Service mesh CRDs |
| cert-manager | TLS certificate lifecycle |
| longhorn | Block storage |
| vpa | Resource recommendations |

### Wave 0: Platform

| Service | Purpose |
|---------|---------|
| traefik | Ingress controller |
| gpu-operator | GPU support |
| coredns-custom | DNS customization |
| resource-quotas | Namespace limits |
| cert-manager-issuers | TLS certificate issuers |

### Wave 1: Service Mesh & Policy

| Service | Purpose |
|---------|---------|
| linkerd-control-plane | mTLS and observability |
| linkerd-viz | Service mesh dashboard |
| kyverno | Pod security policies |

### Wave 2: Monitoring

| Service | Purpose |
|---------|---------|
| prometheus | Metrics collection |
| alertmanager | Alert routing |

### Wave 5: AI Backend

| Service | Purpose |
|---------|---------|
| ollama | CPU inference |
| ollama-gpu | GPU inference |
| litellm | OpenAI-compatible API gateway |
| postgresql | Database |
| redis | Cache/queues |
| keycloak | SSO identity provider |

### Wave 6: AI Frontend

| Service | Purpose |
|---------|---------|
| open-webui | Chat interface |
| n8n | Workflow automation |
| searxng | Web search |
| mcp-servers | AI agent tools |
| docs-site | Documentation |

### Wave 7: CI/CD

| Service | Purpose |
|---------|---------|
| arc-controller | GitHub Actions runner controller |
| arc-runners-amd64 | Standard runners |
| arc-runners-gpu | GPU-accelerated builds |
| arc-runners-arm64 | ARM64 multi-arch builds |
| gitlab-runners | GitLab CI runners |

## Service Dependency Chain

```
SealedSecrets Controller
    |
Traefik (ingress)
    |
cert-manager (TLS)
    |
PostgreSQL, Redis
    |
Keycloak (SSO)
    |
oauth2-proxy (auth middleware)
    |
Ollama (CPU/GPU), LiteLLM
    |
Open WebUI, n8n, SearXNG
```
