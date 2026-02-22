---
title: Resource Management
description: Namespace quotas, limit ranges, and autoscaling configuration
---

# Resource Management

## Namespace Quotas

All namespaces have ResourceQuotas to prevent runaway resource consumption:

| Namespace | CPU Requests | CPU Limits | Memory Requests | Memory Limits | Purpose |
|-----------|--------------|-----------|-----------------|---------------|---------|
| ai-services | 8 | 24 | 48Gi | 64Gi | Primary AI workloads |
| gpu-workloads | 2 | 16 | 16Gi | 32Gi | GPU-related services |
| arc-runners | 8 | 20 | 16Gi | 40Gi | GitHub Actions runners (burst) |
| gitlab-runners | 8 | 16 | 16Gi | 32Gi | GitLab runners |
| monitoring | 4 | 8 | 8Gi | 16Gi | Prometheus, Grafana, Loki |
| linkerd | 2 | 4 | 2Gi | 4Gi | Service mesh |

## LimitRanges

Default resource limits ensure pod placement safety:

| Resource | Default Request | Default Limit | Min | Max |
|----------|-----------------|---------------|-----|-----|
| CPU | 100m | 1 | 10m | 16 |
| Memory | 256Mi | 2Gi | 32Mi | 32Gi |

## Autoscaling

### HPA (Horizontal Pod Autoscaler)

| Setting | Value |
|---------|-------|
| Target CPU utilization | 70% |
| Target memory utilization | 80% |
| Min replicas | 1 |
| Max replicas | 3 (LiteLLM, Open WebUI) or 5 (Agent Server) |
| Scale-down stabilization | 5 minutes |
| Scale-up | 15 seconds |

### VPA (Vertical Pod Autoscaler)

| Setting | Value |
|---------|-------|
| Mode | Off (recommendations only) |
| Min allowed | 100m CPU / 256Mi memory |
| Max allowed | 4 CPU / 8Gi memory |

## Storage Budget

Total: ~500Gi across Longhorn PVs

| Service | Size | Type |
|---------|------|------|
| Ollama GPU models | 150Gi | Persistent |
| Ollama CPU models | 50Gi | Persistent |
| ComfyUI outputs | 50Gi | Persistent |
| Prometheus metrics | 50Gi | Persistent |
| PostgreSQL (GitLab) | 50Gi | Persistent |
| Open WebUI data | 10Gi | Persistent |
| Grafana dashboards | 5Gi | Persistent |
| Buffer/Snapshots | 35Gi | Reserved |
