---
title: Self-Hosted AI Platform
description: Secure, private, self-hosted AI infrastructure on Kubernetes
---

# Self-Hosted AI Platform

A production-ready, self-hosted AI platform running on **Kubernetes** with **GitOps** deployment, unified LLM routing, workflow automation, and AI agent tool integration via **Model Context Protocol (MCP)**.

!!! tip "Privacy First"
    All inference happens on local hardware. No external data transmission, no telemetry, no external API keys required for core functionality.

## Key Features

<div class="grid cards" markdown>

-   :material-brain:{ .lg .middle } **Multi-Model LLM Routing**

    ---

    LiteLLM proxy for unified OpenAI-compatible API across Ollama and other backends. Route between CPU and GPU inference automatically.

-   :material-chat:{ .lg .middle } **Modern Web UI**

    ---

    Open WebUI with chat, RAG, and multi-model support. Full-featured AI assistant accessible from any device.

-   :material-robot:{ .lg .middle } **Workflow Automation**

    ---

    n8n for AI-powered automation workflows. Connect AI models to real-world actions.

-   :material-git:{ .lg .middle } **GitOps Deployment**

    ---

    ArgoCD for declarative, version-controlled infrastructure. Every change tracked and reversible.

-   :material-tools:{ .lg .middle } **MCP Integration**

    ---

    AI agent tools via Model Context Protocol servers. 10+ tool servers for filesystem, git, search, and more.

-   :material-shield-check:{ .lg .middle } **Security by Design**

    ---

    SealedSecrets, internal CA, RBAC, network policies, rootless containers. Defense in depth throughout.

</div>

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Self-Hosted AI Platform                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              Control Plane (k3s) + GPU                            │  │
│  │              akula-prime: 192.168.1.99                            │  │
│  │                                                                   │  │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────────────────────────┐ │  │
│  │  │  ArgoCD  │  │Ollama GPU │  │       Traefik v3               │ │  │
│  │  │ (GitOps) │  │ RTX 5080  │  │  (Ingress + Self-Signed CA)    │ │  │
│  │  └──────────┘  └───────────┘  └────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                                    │ LAN (Flannel VXLAN)                │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │              Worker Node (Primary Workloads)                      │  │
│  │              homelab: 192.168.1.170                               │  │
│  │                                                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │Open WebUI│ │ LiteLLM  │ │   n8n    │ │ Grafana  │            │  │
│  │  │  :443    │ │  :4000   │ │  :5679   │ │  :3003   │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │  │
│  │                                                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │  │
│  │  │  Ollama  │ │PostgreSQL│ │ SearXNG  │ │   MCPO   │            │  │
│  │  │  (CPU)   │ │          │ │ (Search) │ │ (Tools)  │            │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │  │
│  │                                                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────────────┐           │  │
│  │  │  Redis   │ │ Keycloak │ │   Longhorn Storage     │           │  │
│  │  │ (Cache)  │ │  (SSO)   │ │  (NFS: /data/models)   │           │  │
│  │  └──────────┘ └──────────┘ └────────────────────────┘           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Hardware

| Node | Role | Specs | IP |
|------|------|-------|----|
| **akula-prime** | Control Plane + GPU | Intel 14700K, 48GB DDR5, RTX 5080 (16GB) | 192.168.1.99 |
| **homelab** | Worker (Primary Workloads) | Dual E5-2660v4 (28c/56t), 120GB DDR4 | 192.168.1.170 |

## Quick Links

| Resource | Link |
|----------|------|
| [Getting Started](getting-started.md) | Prerequisites and bootstrap |
| [Service Endpoints](endpoints.md) | All service URLs |
| [Architecture Decisions](architecture/adrs.md) | ADRs and design rationale |
| [Operations Runbook](operations/index.md) | Daily ops and troubleshooting |
| [Contributing](development/contributing.md) | How to contribute |
