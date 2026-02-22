---
title: API Rate Limits
description: Rate limit configuration across all services
---

# API Rate Limits

For the full analysis, see `docs/API_RATE_LIMITS_REPORT.md` in the repository.

## LiteLLM

LiteLLM enforces rate limits per model and per API key:

- Configurable via `config/litellm-config.yml`
- Tracked in the LiteLLM dashboard

## Traefik

Traefik enforces rate limiting at the ingress level via middleware:

- Per-IP rate limiting
- Configurable per IngressRoute

## SearXNG

SearXNG rate limiting is disabled at the application level (handled by NetworkPolicy + oauth2-proxy instead).

## Monitoring Rate Limits

```bash
# Check LiteLLM rate limit logs
kubectl logs deployment/litellm -n self-hosted-ai | grep rate

# Check Traefik rate limit middleware
kubectl get middleware -A
```
