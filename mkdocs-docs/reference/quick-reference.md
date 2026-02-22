---
title: Quick Reference
description: Cheat sheet for common operations
---

# Quick Reference

## Most Used Commands

```bash
# Cluster health
kubectl get nodes && kubectl get pods -A | grep -v Running

# ArgoCD sync
argocd app list && argocd app sync <app-name>

# Validation
task validate:all

# Secrets
scripts/setup-keycloak-secrets.sh && kubectl get sealedsecrets -A

# Logs
kubectl logs -f deployment/<name> -n <namespace>

# Models
uv run scripts/sync_models.py list
```

## Service URLs

| Service | URL |
|---------|-----|
| Open WebUI | `https://ai.vectorweight.com` |
| LiteLLM | `https://llm.vectorweight.com` |
| n8n | `https://n8n.vectorweight.com` |
| Grafana | `https://grafana.vectorweight.com` |
| ArgoCD | `https://argocd.vectorweight.com` |
| SearXNG | `https://search.vectorweight.com` |
| GitLab | `https://git.vectorweight.com` |
| Docs | `https://docs.vectorweight.com` |

## Namespace Quick Lookup

| Short | Namespace | What Lives Here |
|-------|-----------|----------------|
| AI | `self-hosted-ai` | WebUI, LiteLLM, Ollama, PG, Redis |
| GPU | `gpu-workloads` | Ollama GPU, ComfyUI, Audio, Video |
| Mon | `monitoring` | Prometheus, Grafana, Tempo |
| SSO | `sso` | Keycloak, oauth2-proxy |
| Auto | `automation` | n8n |
| CD | `argocd` | ArgoCD server |

## Sync Wave Quick Reference

| Wave | Services |
|------|----------|
| -2 | SealedSecrets |
| -1 | cert-manager, Longhorn |
| 0 | Traefik, resource-quotas |
| 5 | Ollama, LiteLLM, databases |
| 6 | Open WebUI, n8n, SearXNG |
| 7 | GitLab, ARC runners |

## Troubleshooting Quick Fixes

| Problem | Fix |
|---------|-----|
| Pod stuck | `kubectl delete pod <name> -n <ns>` |
| Service down | `kubectl rollout restart deployment/<name> -n <ns>` |
| ArgoCD out of sync | `argocd app sync <app-name>` |
| Certificate expired | `kubectl delete certificate <name> -n cert-manager` |
| DNS not resolving | `kubectl rollout restart deployment/coredns -n kube-system` |
| GPU models not loading | `kubectl rollout restart deployment/ollama-gpu -n gpu-workloads` |
