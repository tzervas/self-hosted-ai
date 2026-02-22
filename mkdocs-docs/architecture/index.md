---
title: System Design
description: Architecture overview, core principles, and design philosophy
---

# System Design

## Mission Statement

To provide a **secure, private, and fully self-hosted AI infrastructure** that enables advanced AI-assisted development workflows without reliance on external services or data exposure.

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

## Infrastructure Topology

| Node | IP Address | Role | Hardware | Kubernetes |
|------|------------|------|----------|-----------|
| homelab | 192.168.1.170 | k3s cluster (single node) | AMD64 server (28c/56t, 120GB RAM) | Control plane + workloads |
| akula-prime | 192.168.1.99 | GPU workstation (over LAN) | RTX 5080 16GB VRAM, 48GB RAM | None (external service) |

## Security Model

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
    │Open WebUI│    │  LiteLLM  │    │    n8n    │
    │(auth)    │    │(api-key)  │    │  (auth)   │
    └────┬────┘    └─────┬─────┘    └───────────┘
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

For detailed architecture decisions, see [ADRs](adrs.md). For technology details, see [Technology Stack](tech-stack.md).
