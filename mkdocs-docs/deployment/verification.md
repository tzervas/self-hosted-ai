---
title: Deployment Verification
description: Post-deployment verification checklist and health checks
---

# Deployment Verification

## Quick Health Check

```bash
# Overall cluster health
kubectl get nodes
kubectl get pods -A | grep -v Running

# ArgoCD sync status
argocd app list

# Certificate status
kubectl get certificates -n cert-manager
```

## Verification Checklist

### Infrastructure

- [ ] All nodes are `Ready`: `kubectl get nodes`
- [ ] SealedSecrets controller running: `kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets`
- [ ] cert-manager issuing certificates: `kubectl get certificates -A`
- [ ] Traefik ingress active: `kubectl get pods -n traefik`

### AI Services

- [ ] Ollama CPU responding: `kubectl exec -n ai-services deployment/ollama -- curl localhost:11434/api/tags`
- [ ] LiteLLM healthy: `curl -k https://llm.vectorweight.com/health`
- [ ] Open WebUI accessible: `curl -k https://ai.vectorweight.com/health`

### Monitoring

- [ ] Prometheus scraping targets: `curl -k https://prometheus.vectorweight.com/api/v1/targets`
- [ ] Grafana dashboards loading: `curl -k https://grafana.vectorweight.com/api/health`

### GPU Worker

- [ ] GPU workloads running: `kubectl get pods -n gpu-workloads`
- [ ] GPU resources available: `kubectl get node akula-prime -o json | jq '.status.allocatable'`

## Automated Validation

```bash
# Full validation suite
task validate:all

# Or individual checks
task validate:helm
task validate:manifests
task validate:policies

# Security scans
task security:trivy
task security:secrets
```

## Common Post-Deploy Issues

See [Troubleshooting](../operations/troubleshooting.md) for common issues and their solutions.
