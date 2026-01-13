# Self-Hosted AI Stack - Complete Usage Guide

**Version:** 2.0.0 | **Last Updated:** January 11, 2026

---

## Table of Contents

1. [Chat & Conversation](#chat--conversation)
2. [Web Search Integration](#web-search-integration)
3. [Image Generation](#image-generation)
4. [Video Generation](#video-generation)
5. [Audio Transcription](#audio-transcription)
6. [Document Processing](#document-processing)
7. [Research Workflows](#research-workflows)
8. [Model Management](#model-management)
9. [GPU Resource Management](#gpu-resource-management)
10. [Monitoring & Observability](#monitoring--observability)

---

## Chat & Conversation

### Basic Chat

1. Navigate to **Open WebUI** at http://192.168.1.170:3000
2. Create an account (first signup becomes admin)
3. Select a model from the dropdown
4. Start chatting!

### Model Selection

**CPU Models (Fast, lower quality):**
- `llama3.2:3b` - Quick responses
- `mistral:7b` - Good for coding

**GPU Models (Higher quality):**
- `llama3.2:latest` - Balanced
- `llama3.2:70b` - Best quality (requires 48GB+ VRAM)
- `codellama:34b` - Code generation

### Advanced Features

**System Prompts:**
Click the gear icon to set custom system prompts:
```
You are a senior software engineer specializing in Python and Rust.
Always explain your reasoning step by step.
```

**Context Length:**
- Default: 4096 tokens
- Increase for longer conversations: Settings → Models → Context Length

**Multi-Model Chat:**
Use `@model` to switch mid-conversation:
```
@llama3.2:70b Analyze this code...
@codellama:34b Now refactor it...
```

---

## Web Search Integration

### Using SearXNG in Chat

Enable web search for up-to-date information:

1. In Open WebUI, click the **globe icon** before sending
2. Or use the command: `/search your query here`

### Direct SearXNG Access

Access SearXNG directly at http://192.168.1.170:8080

**Search Shortcuts:**
- `!gh term` - Search GitHub
- `!so term` - Search Stack Overflow
- `!wp term` - Search Wikipedia
- `!hf term` - Search HuggingFace
- `!ax term` - Search arXiv

### API Usage

```python
import httpx

response = httpx.get(
    "http://192.168.1.170:8080/search",
    params={
        "q": "latest llama model",
        "format": "json",
        "engines": "google,duckduckgo,github"
    }
)
results = response.json()
```

---

## Image Generation

### Using ComfyUI (Node-Based)

**Best for:** Complex workflows, pipelines, fine control

1. Access at http://192.168.1.99:8188
2. Load a workflow from the sidebar
3. Modify prompts and settings
4. Click "Queue Prompt"

**Available Workflows:**
| Workflow | Description | VRAM |
|----------|-------------|------|
| txt2img-sdxl | High-quality text to image | 8GB |
| txt2img-flux-schnell | Fast FLUX generation | 12GB |
| img2img-sdxl | Transform existing images | 8GB |
| upscale-2x | Upscale with Real-ESRGAN | 4GB |
| pipeline-full-agentic | Full gen→refine→upscale | 14GB |

### Using A1111 WebUI (User-Friendly)

**Best for:** Quick generation, beginners, extensions

1. Access at http://192.168.1.99:7860
2. Enter your prompt
3. Adjust settings (steps, CFG, sampler)
4. Click "Generate"

**Recommended Settings:**
```
Steps: 25-35
CFG Scale: 7-9
Sampler: DPM++ 2M Karras
Size: 1024x1024 (SDXL) / 512x768 (SD 1.5)
```

### Via Open WebUI

Generate images directly in chat:

1. Click the **image icon** or type `/image`
2. Describe what you want
3. Select engine (ComfyUI/A1111/Auto)

**Example prompts:**
```
/image A futuristic cityscape at sunset, cyberpunk style, neon lights
/image Portrait of a wise wizard, detailed, fantasy art, 4k
```

---

## Video Generation

### Text-to-Video with WAN

1. Open ComfyUI at http://192.168.1.99:8188
2. Load `text2video-wan.json` workflow
3. Enter prompt in the positive text box
4. Set frame count (24 = 1 second)
5. Queue and wait (~2-5 minutes)

**Tips:**
- Start with simple prompts
- Use motion keywords: "walking", "flying", "flowing"
- Keep videos short (1-3 seconds)

### Image-to-Video with SVD

1. Load `text2video-svd.json`
2. Upload a source image
3. The model will animate it

---

## Audio Transcription

### Via API

```python
import httpx

with open("audio.mp3", "rb") as f:
    response = httpx.post(
        "http://192.168.1.99:9000/asr",
        files={"audio_file": f},
        params={"output": "json"}
    )
    
transcription = response.json()
print(transcription["text"])
```

### In Workflows

Use the `audio2img.json` workflow to:
1. Transcribe audio
2. Generate image from transcription

---

## Document Processing

### Automatic Ingestion

Drop files into watch directories:
- `/data/ingest/` - Auto-processed
- `/data/documents/` - Auto-processed

**Supported formats:**
- Documents: PDF, DOCX, TXT, MD, HTML
- Code: PY, JS, TS, JSON, YAML
- Images: PNG, JPG (with OCR)
- Audio: MP3, WAV (with transcription)

### Manual Ingestion

```bash
curl -X POST http://192.168.1.170:8200/ingest \
  -H "Content-Type: application/json" \
  -d '{"filepath": "/data/documents/report.pdf", "collection": "reports"}'
```

### Upload via API

```python
import httpx

with open("document.pdf", "rb") as f:
    response = httpx.post(
        "http://192.168.1.170:8200/ingest/upload",
        files={"file": f},
        data={"collection": "my-docs"}
    )
```

---

## Research Workflows

### Automated Research

Trigger via API:

```bash
curl -X POST http://192.168.1.170:8300/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Latest developments in AI safety",
    "depth": "comprehensive",
    "generate_visuals": true
  }'
```

### Research in Chat

Use the `/research` command:
```
/research quantum computing applications in drug discovery
```

This will:
1. Expand your query into multiple searches
2. Search across academic and general sources
3. Synthesize findings
4. Generate a comprehensive report

---

## Model Management

### Pull New Models

**Via CLI (on respective node):**
```bash
# GPU worker (for large models)
docker exec ollama-gpu-worker ollama pull llama3.2:70b

# Server (for CPU models)
docker exec ollama-cpu-server ollama pull mistral:7b
```

**Via Open WebUI:**
Settings → Models → Pull a model

### Sync Local Models

From your development machine:
```bash
# Sync all models to GPU worker
./scripts/sync-models.sh sync

# Sync specific type
./scripts/sync-models.sh sync checkpoints

# Check what would sync
./scripts/sync-models.sh --dry-run sync
```

### Model Locations

| Type | Path on GPU Worker |
|------|-------------------|
| Ollama | /data/ollama-gpu/ |
| ComfyUI Checkpoints | /data/comfyui/models/checkpoints/ |
| ComfyUI LoRAs | /data/comfyui/models/loras/ |
| ComfyUI VAE | /data/comfyui/models/vae/ |
| A1111 | /data/models/ |
| Whisper | /data/whisper/ |

---

## GPU Resource Management

### How It Works

The GPU Manager automatically:
- Allocates full GPU when only one service is active
- Splits resources fairly when multiple services run
- Prioritizes based on task type (inference > generation)

### Check Status

```bash
curl http://192.168.1.99:8100/status
```

Response:
```json
{
  "gpus": [{
    "index": 0,
    "name": "NVIDIA RTX 4090",
    "total_memory_mb": 24576,
    "used_memory_mb": 8192,
    "free_memory_mb": 16384,
    "utilization_percent": 45
  }],
  "allocations": {...}
}
```

### Manual Allocation (Advanced)

```python
import httpx

# Request GPU allocation
response = httpx.post(
    "http://192.168.1.99:8100/allocate",
    json={
        "service": "comfyui",
        "priority": "high",
        "estimated_vram_mb": 10000,
        "estimated_duration_s": 60
    }
)
allocation = response.json()

# ... do work ...

# Release allocation
httpx.post(
    "http://192.168.1.99:8100/release",
    json={"allocation_id": allocation["allocation_id"]}
)
```

---

## Monitoring & Observability

### Grafana Dashboards

Access at http://192.168.1.170:3001

**Pre-configured dashboards:**
- System Overview
- GPU Metrics
- Request Latency
- Model Performance

### Prometheus Metrics

Access at http://192.168.1.170:9090

**Key metrics:**
- `ollama_requests_total` - Request count
- `gpu_memory_used_mb` - GPU memory usage
- `comfyui_queue_length` - Generation queue
- `ingest_documents_processed` - Documents processed

### Health Checks

All services expose `/health` endpoints:
```bash
# Quick health check script
for svc in "192.168.1.170:3000" "192.168.1.170:8080" "192.168.1.99:11434" "192.168.1.99:8188"; do
  echo -n "$svc: "
  curl -s -o /dev/null -w "%{http_code}" "http://$svc/health" || echo "FAIL"
  echo
done
```

---

## Tips & Best Practices

### Performance

1. **Keep models loaded**: Set `OLLAMA_KEEP_ALIVE=30m` to avoid reload delays
2. **Use appropriate models**: Don't use 70B for simple tasks
3. **Batch operations**: Queue multiple images at once

### Quality

1. **Good prompts**: Be specific, descriptive
2. **Negative prompts**: Exclude unwanted elements
3. **Iterative refinement**: Start simple, add detail

### Cost/Resources

1. **Monitor GPU usage**: Watch Grafana for bottlenecks
2. **Schedule heavy tasks**: Run batch jobs during low-usage periods
3. **Clean up outputs**: Periodically clean generated images/videos

---

*For more detailed guides, see the [Workflow Guides](WORKFLOW_GUIDES.md) and [How to Build](HOW_TO_BUILD.md).*
