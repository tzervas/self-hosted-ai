---
title: Service Endpoints
description: All service URLs and access information
---

# Service Endpoints

## External Services (HTTPS)

| Service | URL | Purpose |
|---------|-----|---------|
| **Open WebUI** | [ai.vectorweight.com](https://ai.vectorweight.com) | AI chat interface |
| **LiteLLM** | [llm.vectorweight.com](https://llm.vectorweight.com) | OpenAI-compatible API proxy |
| **n8n** | [n8n.vectorweight.com](https://n8n.vectorweight.com) | Workflow automation |
| **Grafana** | [grafana.vectorweight.com](https://grafana.vectorweight.com) | Monitoring dashboards |
| **Prometheus** | [prometheus.vectorweight.com](https://prometheus.vectorweight.com) | Metrics |
| **OpenObserve** | [observe.vectorweight.com](https://observe.vectorweight.com) | Logs, metrics, traces |
| **SearXNG** | [search.vectorweight.com](https://search.vectorweight.com) | Privacy search |
| **GitLab** | [git.vectorweight.com](https://git.vectorweight.com) | Source control |
| **ArgoCD** | [argocd.vectorweight.com](https://argocd.vectorweight.com) | GitOps dashboard |
| **Traefik** | [traefik.vectorweight.com](https://traefik.vectorweight.com) | Ingress dashboard |
| **Longhorn** | [longhorn.vectorweight.com](https://longhorn.vectorweight.com) | Storage UI |
| **Docs** | [docs.vectorweight.com](https://docs.vectorweight.com) | This documentation |

!!! note
    All HTTPS endpoints require the self-signed CA certificate to be installed. See [TLS & Certificates](security/tls-certificates.md).

## Internal Services (ClusterIP)

| Service | Namespace | Port | Notes |
|---------|-----------|------|-------|
| PostgreSQL | self-hosted-ai | 5432 | LiteLLM database |
| Redis | self-hosted-ai | 6379 | Cache/queues |
| Ollama (CPU) | self-hosted-ai | 11434 | CPU inference |
| Ollama (GPU) | gpu-workloads | 11434 | GPU inference |
| Tempo | monitoring | 3100 | Trace storage and query |
| OTel Collector | monitoring | 4318 | OTLP/HTTP receiver |
| Alertmanager | monitoring | 9093 | Alert routing |
| MCP Servers | self-hosted-ai | 8000 | AI agent tools |

## GPU Worker (akula-prime)

The GPU worker at `192.168.1.99` runs GPU-accelerated services as Kubernetes pods in the `gpu-workloads` namespace:

| Service | Namespace | Port | Purpose |
|---------|-----------|------|---------|
| Ollama GPU | gpu-workloads | 11434 | GPU inference (RTX 5080) |
| ComfyUI | gpu-workloads | 8188 | Image generation |
| Audio Server | gpu-workloads | 8000 | TTS/Audio generation |
| Video Server | gpu-workloads | 8000 | Video generation |
