---
title: LiteLLM Gateway
description: OpenAI-compatible API gateway configuration
---

# LiteLLM Gateway

## Overview

LiteLLM provides an OpenAI-compatible API that routes requests to multiple Ollama backends. It handles model routing, rate limiting, and cost tracking.

**Endpoint**: [llm.vectorweight.com](https://llm.vectorweight.com)

## Configuration

Model routing is configured in `config/litellm-config.yml`:

- Model definitions with Ollama backend URLs
- Routing rules and fallbacks
- Rate limiting per model

## API Usage

### Chat Completion

```bash
curl -X POST https://llm.vectorweight.com/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:14b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### List Models

```bash
curl https://llm.vectorweight.com/v1/models \
  -H "Authorization: Bearer $LITELLM_KEY"
```

### Embeddings

```bash
curl -X POST https://llm.vectorweight.com/v1/embeddings \
  -H "Authorization: Bearer $LITELLM_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text",
    "input": "Hello world"
  }'
```

## Helm Chart

Configuration: `helm/litellm/values.yaml`

Key settings:

- `config.litellm_config`: Model routing configuration
- `resources`: CPU/memory limits
- `service.port`: 4000 (default)
