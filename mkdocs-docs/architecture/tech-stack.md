---
title: Technology Stack
description: Complete technology matrix for the platform
---

# Technology Stack

## Core Platform

| Component | Technology | Purpose |
|-----------|------------|---------|
| Container Runtime | containerd | Container execution |
| Orchestration | k3s (Kubernetes) | Workload scheduling |
| GitOps | ArgoCD | Declarative deployments |
| Ingress | Traefik v3 | HTTP routing, TLS |
| Certificates | cert-manager | TLS certificate lifecycle |
| Secrets | SealedSecrets | Encrypted secrets in Git |
| Storage | Longhorn | Distributed block storage |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Tracing | Tempo + OTel Collector | Distributed tracing |
| Logs | OpenObserve + Loki | Log aggregation |
| Service Mesh | Linkerd v2025.1.2 | mTLS and observability |
| Autoscaling | HPA + VPA | Resource scaling and optimization |

## AI Services

| Component | Technology | Purpose |
|-----------|------------|---------|
| Inference (GPU) | Ollama | LLM inference with GPU |
| Inference (CPU) | Ollama | LLM inference fallback |
| API Gateway | LiteLLM | OpenAI-compatible proxy |
| Chat Interface | Open WebUI | User-facing AI chat |
| Search | SearXNG | Privacy-focused web search |
| Automation | n8n | Workflow orchestration |
| Embeddings | LiteLLM + Ollama | Vector embeddings |

## Model Management

| Source | Type | Purpose | Auth |
|--------|------|---------|------|
| Ollama Library | LLMs | Public models | None |
| HuggingFace Hub | LLMs, TTS, Audio | Uncensored models | HF_TOKEN |
| HuggingFace Hub | Vision, LoRA | Fine-tuning and vision | HF_TOKEN |
| ComfyUI | Checkpoints, VAE | Image/video generation | Direct URLs |

## Development & CI/CD

| Component | Technology | Purpose |
|-----------|------------|---------|
| Source Control | GitLab (self-hosted) | Code repository + mirrors |
| CI/CD (GitHub) | GitHub Actions (ARC) | Automated builds and tests |
| CI/CD (GitLab) | GitLab Runner | GitLab CI pipelines |
| Scripts | Python 3.12+ / uv | Automation and model syncing |
| Agent Framework | Python ADK | AI agent implementation |
