---
title: Workflows
description: n8n workflow automation with AI
---

# Workflows

## Overview

n8n provides visual workflow automation with AI integration, running in the `automation` namespace.

**Access**: [n8n.vectorweight.com](https://n8n.vectorweight.com)

## Available Workflows

Pre-built workflows are stored in `config/n8n-workflows/`:

| Workflow | Purpose |
|----------|---------|
| `agentic-reasoning.json` | Multi-step AI reasoning chains |
| `multi-agent-orchestrator.json` | Coordinate multiple AI agents |
| `unified-multimodal-content.json` | Process text, image, and audio content |

## Import/Export

### Import a Workflow

1. Open n8n UI
2. Go to Workflows > Import
3. Select JSON file from `config/n8n-workflows/`

### Export a Workflow

1. Open the workflow in n8n
2. Click the three-dot menu > Download
3. Save to `config/n8n-workflows/`
4. Commit to Git

## Webhook Triggers

```bash
# Trigger a workflow via webhook
curl -X POST https://n8n.vectorweight.com/webhook/ai-pipeline \
  -H "Content-Type: application/json" \
  -d '{"input": "Process this"}'
```
