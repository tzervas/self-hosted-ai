---
title: Namespace Reference
description: Kubernetes namespace organization and purposes
---

# Namespace Reference

## Active Namespaces

| Namespace | Purpose | Key Services |
|-----------|---------|--------------|
| `argocd` | GitOps control plane | ArgoCD server, repo-server, dex |
| `cert-manager` | TLS certificate management | cert-manager, issuers, CA |
| `automation` | Workflow orchestration | n8n, workflow triggers |
| `self-hosted-ai` | Core AI services | Open WebUI, LiteLLM, Ollama CPU, PostgreSQL, Redis, MCP servers |
| `gpu-workloads` | GPU-accelerated AI | Ollama GPU, audio-server, video-server, TTS |
| `monitoring` | Observability | Prometheus, Grafana, Tempo, OTel Collector |
| `sso` | Identity and access | Keycloak, oauth2-proxy |
| `ingress` | External access | Traefik |
| `longhorn-system` | Storage | Longhorn controller, CSI driver |
| `linkerd` | Service mesh | Linkerd control plane |
| `kyverno` | Policy enforcement | Kyverno |
| `arc-systems` | Runner controller | ARC controller |
| `arc-runners` | CI/CD runners | GitHub Actions Runner pods |
| `gitlab` | Source control | GitLab, GitLab runners |

## Service Dependencies

```mermaid
graph TB
    SS[SealedSecrets<br/>kube-system] --> CM[cert-manager]
    CM --> Traefik[Traefik<br/>ingress]
    Traefik --> PG[PostgreSQL<br/>self-hosted-ai]
    Traefik --> Redis[Redis<br/>self-hosted-ai]
    PG --> KC[Keycloak<br/>sso]
    KC --> OAuth[oauth2-proxy<br/>sso]
    OAuth --> Services[AI Services<br/>self-hosted-ai]
    PG --> LiteLLM[LiteLLM<br/>self-hosted-ai]
    LiteLLM --> Ollama[Ollama<br/>self-hosted-ai]
    LiteLLM --> OllamaGPU[Ollama GPU<br/>gpu-workloads]
    Services --> WebUI[Open WebUI]
    Services --> N8N[n8n<br/>automation]
```

## Resource Quotas

Each namespace has ResourceQuotas configured. See [Resource Management](../architecture/resources.md) for details.
