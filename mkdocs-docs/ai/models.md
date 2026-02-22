---
title: Model Management
description: AI model inventory, syncing, and management
---

# Model Management

## Model Sources

| Source | Type | Auth |
|--------|------|------|
| Ollama Library | Public LLMs | None |
| HuggingFace Hub | Uncensored models, TTS, Audio | `HF_TOKEN` |
| ComfyUI | Image/video generation checkpoints | Direct URLs |

## Model Manifest

Models are declared in `config/models-manifest.yml`. This is the source of truth for which models should be available.

## Management Commands

```bash
# List models across all locations
uv run scripts/sync_models.py list

# List models on GPU worker
curl http://192.168.1.99:11434/api/tags | jq '.models[].name'

# Pull a model
curl -X POST http://192.168.1.99:11434/api/pull \
  -d '{"name":"qwen2.5-coder:14b"}'

# Push models to GPU worker
uv run scripts/sync_models.py push --all

# Compare models between locations
uv run scripts/sync_models.py diff
```

## Model Memory Management

```bash
# Check loaded models and memory usage
curl http://192.168.1.99:11434/api/ps | jq

# Unload unused models to free VRAM
curl -X POST http://192.168.1.99:11434/api/generate \
  -d '{"model":"unused-model","keep_alive":0}'
```

## Adding a New Model

1. Add the model to `config/models-manifest.yml`
2. Pull it to the appropriate Ollama instance
3. Add routing configuration in LiteLLM if needed (see [LiteLLM Gateway](litellm.md))
4. Test via Open WebUI or API
