# Image & Video Generation Guide

Complete guide to utilizing the self-hosted AI cluster's image and video generation capabilities.

---

## Overview

The platform provides **GPU-accelerated** image and video generation through ComfyUI, accessible via multiple interfaces:

| Interface | Use Case | Complexity |
|-----------|----------|------------|
| **Open WebUI Tools** | Natural language requests via chat | ⭐ Easy |
| **ComfyUI Web UI** | Advanced workflows, custom pipelines | ⭐⭐⭐ Advanced |
| **n8n Workflows** | Automated batch processing | ⭐⭐ Intermediate |
| **Direct API** | Programmatic integration | ⭐⭐⭐ Advanced |

**Hardware**: NVIDIA RTX 5080 (16GB VRAM) on GPU worker (192.168.1.99)

---

## Quick Start: Using Open WebUI (Easiest)

### 1. Access Open WebUI

Navigate to: **https://ai.vectorweight.com**

### 2. Enable Generation Tools

**Option A: Upload Tools (Recommended)**
1. Go to Settings → Tools
2. Click "Upload Tool"
3. Upload these files from `config/openwebui-tools/`:
   - `image_generation.py` (for images)
   - `video_generation.py` (for videos)

**Option B: Use Existing Installation**
If tools are already installed, they'll appear in the Tools section.

### 3. Generate Content via Chat

**Image Generation**:
```
You: Create an image of a sunset over mountains

AI: [Calls image_generation tool]
    Image generated successfully!
    Prompt: 'sunset over mountains, photorealistic, high quality'
    Size: 1024x1024, Steps: 25, Seed: 1234567890
    Image: OpenWebUI_12345.png
```

**Video Generation**:
```
You: Generate a video of a cat playing piano

AI: [Calls video_generation tool]
    ✅ Video generation started with Wan 2.1!
    Estimated time: 66 seconds
    Monitor progress at: http://comfyui:8188/
    Prompt ID: abc123

    [After 1 minute]

You: Check video generation status for abc123

AI: Video generation completed!
    Frames: 33
    Preview URLs: [list of frame URLs]
```

### 4. Advanced Parameters

You can specify detailed parameters:

**Images**:
```
Create a 2048x1024 portrait of a cyberpunk city at night,
25 sampling steps, seed 42
```

**Videos**:
```
Generate a 49-frame video of ocean waves at 720x480,
30 steps, seed 999
```

---

## Method 2: ComfyUI Web Interface (Advanced)

### Access ComfyUI

**Direct Access** (from GPU worker):
- URL: http://192.168.1.99:8188/
- Or via Kubernetes: http://comfyui.gpu-workloads:8188/

### Available Workflows

ComfyUI workflows are pre-loaded from `config/comfyui-workflows/`:

#### Image Generation Workflows

| Workflow | Model | Purpose | Speed |
|----------|-------|---------|-------|
| `txt2img-sdxl.json` | SDXL Base 1.0 | High-quality images | Medium |
| `txt2img-flux-schnell.json` | FLUX Schnell | Fast generation | Fast |
| `txt2img-sd15.json` | SD 1.5 | Lightweight | Fast |
| `txt2img-sdxl-turbo.json` | SDXL Turbo | Ultra-fast | Very Fast |
| `img2img-sdxl.json` | SDXL | Transform existing images | Medium |
| `inpaint-sdxl.json` | SDXL | Edit parts of images | Medium |
| `upscale-2x.json` | RealESRGAN | 2x upscaling | Fast |
| `upscale-4x.json` | RealESRGAN | 4x upscaling | Medium |

#### Video Generation Workflows

| Workflow | Model | Purpose | Speed |
|----------|-------|---------|-------|
| `wan21-t2v-1.3b.json` | Wan 2.1 (1.3B) | Text to video | Slow (~60s for 33 frames) |
| `text2video-svd.json` | Stable Video Diffusion | High-quality video | Very Slow |
| `video-with-audio.json` | Wan 2.1 + Audio | Video + sound effects | Very Slow |

#### Multimodal Workflows

| Workflow | Purpose | Models Used |
|----------|---------|-------------|
| `full-multimodal-pipeline.json` | Image → caption → variations | SDXL + CLIP |
| `audio2img.json` | Audio → image visualization | AudioLDM2 + SDXL |
| `img2img-caption.json` | Image analysis + transformation | CLIP + SDXL |
| `text2audio-music.json` | Text → music generation | MusicGen |
| `text2audio-sfx.json` | Text → sound effects | AudioLDM2 |
| `text2audio-tts.json` | Text → speech | XTTS-v2 |

### Using Workflows

1. **Load workflow**: File → Load → Select workflow JSON
2. **Configure parameters**:
   - Positive prompt (what you want)
   - Negative prompt (what to avoid)
   - Image size, steps, seed
3. **Queue Prompt**: Click "Queue Prompt" button
4. **Monitor**: Watch live preview in sidebar
5. **View Output**: Results appear in "View History"

---

## Method 3: n8n Workflow Automation (Batch Processing)

### Access n8n

Navigate to: **https://n8n.vectorweight.com**

### Pre-Built Workflows

Available in `config/n8n-workflows/`:

| Workflow | Purpose |
|----------|---------|
| `comfyui-image-generation.json` | Batch image generation from prompt list |
| `video-generation.json` | Automated video creation pipeline |
| `unified-multimodal-content.json` | Generate image + caption + variations |
| `agentic-reasoning.json` | AI-driven creative exploration |

### Example: Batch Image Generation

1. Import `comfyui-image-generation.json` workflow
2. Configure input:
   ```json
   {
     "prompts": [
       "sunset over mountains",
       "cyberpunk city at night",
       "forest path in autumn"
     ],
     "width": 1024,
     "height": 1024,
     "steps": 25
   }
   ```
3. Execute workflow
4. Outputs saved to `/data/comfyui/output/`

---

## Method 4: Direct API Usage (Programmatic)

### ComfyUI API Endpoints

**Base URL**: http://192.168.1.99:8188/ (or http://comfyui.gpu-workloads:8188/)

#### Submit Workflow

```bash
curl -X POST http://192.168.1.99:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {
      "3": {
        "inputs": {
          "seed": 42,
          "steps": 25,
          "cfg": 7.5,
          "sampler_name": "euler_ancestral",
          "scheduler": "normal",
          "denoise": 1,
          "model": ["4", 0],
          "positive": ["6", 0],
          "negative": ["7", 0],
          "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
      },
      "4": {
        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        "class_type": "CheckpointLoaderSimple"
      },
      "5": {
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        "class_type": "EmptyLatentImage"
      },
      "6": {
        "inputs": {"text": "sunset over mountains", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode"
      },
      "7": {
        "inputs": {"text": "blurry, low quality", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode"
      },
      "8": {
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        "class_type": "VAEDecode"
      },
      "9": {
        "inputs": {"filename_prefix": "API_output", "images": ["8", 0]},
        "class_type": "SaveImage"
      }
    },
    "client_id": "api-client-001"
  }'
```

**Response**:
```json
{
  "prompt_id": "abc-123-def",
  "number": 1,
  "node_errors": {}
}
```

#### Check Generation Status

```bash
curl http://192.168.1.99:8188/history/abc-123-def
```

#### Get Queue Status

```bash
curl http://192.168.1.99:8188/queue
```

#### View Generated Image

```bash
curl http://192.168.1.99:8188/view?filename=API_output_00001_.png
```

---

## Available Models

### Image Generation Models

| Model | Size | Resolution | Speed | Quality |
|-------|------|------------|-------|---------|
| **SDXL Base 1.0** | 6.5GB | Up to 2048x2048 | Medium | Excellent |
| **SD 1.5** | 4GB | Up to 1024x1024 | Fast | Good |
| **FLUX Schnell** | 8GB | Up to 1024x1024 | Very Fast | Good |
| **SDXL Turbo** | 6.5GB | Up to 1024x1024 | Ultra Fast | Good |

### Video Generation Models

| Model | Size | Max Frames | Resolution | Speed |
|-------|------|------------|------------|-------|
| **Wan 2.1 (1.3B)** | 3.2GB | 81 | 720x480 | ~60s for 33 frames |
| **Stable Video Diffusion** | 8GB | 25 | 1024x576 | ~120s for 25 frames |

### Audio Models

| Model | Size | Purpose |
|-------|------|---------|
| **XTTS-v2** | 2GB | Text-to-speech |
| **AudioLDM2** | 4GB | Sound effects |
| **MusicGen** | 3GB | Music generation |

### Upscaling Models

| Model | Upscale Factor | Speed |
|-------|----------------|-------|
| **RealESRGAN x4** | 4x | Medium |
| **RealESRGAN x2** | 2x | Fast |

---

## Configuration & Optimization

### Current GPU Settings

**ComfyUI Configuration** (`helm/gpu-worker/values.yaml`):

```yaml
comfyui:
  enabled: false  # Currently disabled (GPU shared with Ollama)
  env:
    - name: COMMANDLINE_ARGS
      value: "--lowvram --preview-method latent2rgb --enable-cors-header *"
    - name: COMFYUI_PREVIEW_QUALITY
      value: "75"  # JPEG quality for preview streaming
  resources:
    requests:
      nvidia.com/gpu: 1
      memory: "4Gi"
    limits:
      nvidia.com/gpu: 1
      memory: "16Gi"
```

**VRAM Budget** (RTX 5080 16GB):
- Image generation (SDXL): ~8GB
- Video generation (Wan 2.1): ~12GB
- Max simultaneous: 1 image OR 1 video

### Enabling ComfyUI

**Option 1: Via ArgoCD** (Recommended)
```bash
# Edit ArgoCD application
kubectl edit application comfyui -n argocd

# Set comfyui.enabled: true
# Or use Helm values override
```

**Option 2: Manual Helm**
```bash
helm upgrade --install comfyui helm/gpu-worker \
  --set comfyui.enabled=true \
  -n gpu-workloads
```

**Option 3: GPU Time-Slicing** (Future)
Enable multiple services to share GPU:
```yaml
# GPU time-slicing configuration
# Allows Ollama + ComfyUI to coexist
# Requires nvidia-device-plugin configuration
```

### Performance Tuning

**Fast Generation (lower quality)**:
```yaml
steps: 15-20
sampler: "euler_ancestral"  # Fast
cfg_scale: 7.0
```

**High Quality (slower)**:
```yaml
steps: 30-50
sampler: "dpm_2_ancestral"  # Slow but high quality
cfg_scale: 7.5-9.0
```

**Video Optimization**:
```yaml
frames: 33  # Default (66s)
frames: 49  # Longer (90s)
frames: 81  # Max (150s)
resolution: 480x320  # Fastest
resolution: 720x480  # Balanced
```

---

## Troubleshooting

### ComfyUI Not Accessible

**Issue**: "ComfyUI is not reachable"

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n gpu-workloads -l app=comfyui

# Check logs
kubectl logs -n gpu-workloads deployment/comfyui -f
```

**Fix**:
```bash
# Enable ComfyUI in ArgoCD app
kubectl edit application comfyui -n argocd
# Set: comfyui.enabled: true

# Or restart deployment
kubectl rollout restart deployment/comfyui -n gpu-workloads
```

### Out of VRAM

**Issue**: "CUDA out of memory"

**Diagnosis**:
```bash
# Check GPU usage
ssh akula-prime nvidia-smi
```

**Fix**:
- Reduce image resolution (2048 → 1024)
- Reduce video frames (81 → 33)
- Use `--lowvram` flag (already enabled)
- Stop Ollama during generation (temporary)

### Slow Generation

**Issue**: Generation takes too long

**Optimization**:
1. **Use faster models**: SDXL Turbo instead of SDXL Base
2. **Reduce steps**: 25 → 15 (image), 20 → 10 (video)
3. **Lower resolution**: 1024x1024 → 512x512
4. **Check GPU utilization**: Ensure GPU not shared with Ollama

### Preview Streaming Not Working

**Issue**: No live previews during generation

**Diagnosis**:
```bash
# Check ComfyUI args
kubectl get deployment comfyui -n gpu-workloads -o yaml | grep COMMANDLINE_ARGS
```

**Fix**:
Ensure `--preview-method latent2rgb` is set in env vars.

### Image/Video Quality Issues

**Issue**: Blurry or distorted output

**Fix**:
1. **Improve prompt**: Be more specific and detailed
2. **Adjust negative prompt**: Add "blurry, distorted, low quality"
3. **Increase steps**: 25 → 30-40
4. **Increase CFG scale**: 7.0 → 7.5-9.0
5. **Use refiner model**: SDXL Refiner for higher quality
6. **Upscale**: Use RealESRGAN 4x for final output

---

## Best Practices

### Writing Effective Prompts

**Good Image Prompt**:
```
A serene mountain landscape at sunset, golden hour lighting,
photorealistic, high detail, 8k quality, wide angle lens
```

**Bad Image Prompt**:
```
mountain
```

**Good Video Prompt**:
```
Ocean waves gently rolling onto a sandy beach, slow motion,
cinematic lighting, smooth camera movement, high quality
```

**Bad Video Prompt**:
```
waves
```

### Negative Prompts

**Always include**:
```
blurry, low quality, distorted, ugly, deformed, artifacts,
watermark, text, signature
```

**For specific issues**:
- Anatomy issues: "extra limbs, missing fingers, bad hands"
- Composition: "cropped, out of frame, bad framing"
- Style: "cartoon, anime" (if you want photorealism)

### Resource Management

**When GPU is Shared**:
1. Schedule heavy generation during off-peak hours
2. Use CPU Ollama for chat while generating
3. Monitor VRAM with `nvidia-smi`

**Batch Processing**:
1. Use n8n workflows for multiple images/videos
2. Queue jobs during low-usage periods
3. Use lower resolution for previews, upscale final outputs

---

## Examples Gallery

### Image Generation Examples

**Photorealistic Portrait**:
```yaml
prompt: "Professional headshot of a businesswoman, studio lighting,
         sharp focus, bokeh background, 85mm lens, photorealistic"
negative: "blurry, low quality, distorted, cartoon"
model: sd_xl_base_1.0.safetensors
resolution: 1024x1024
steps: 30
cfg: 7.5
```

**Artistic Landscape**:
```yaml
prompt: "Vibrant sunset over mountain peaks, dramatic clouds,
         oil painting style, impressionist, vivid colors"
negative: "photo, photorealistic, modern"
model: sd_xl_base_1.0.safetensors
resolution: 1536x1024
steps: 25
cfg: 8.0
```

### Video Generation Examples

**Nature Scene**:
```yaml
prompt: "Time-lapse of clouds moving over a mountain valley,
         golden hour, smooth motion, cinematic"
negative: "jerky, low quality, artifacts, blurry"
model: wan2.1_t2v_1.3B_bf16.safetensors
frames: 49
resolution: 720x480
steps: 20
```

**Action Scene**:
```yaml
prompt: "Rocket launching into space, dramatic lighting,
         smoke and fire, slow motion, epic cinematic"
negative: "static, boring, low quality"
model: wan2.1_t2v_1.3B_bf16.safetensors
frames: 33
resolution: 480x320
steps: 25
```

---

## Integration with Other Services

### LiteLLM Integration

Generate images via LiteLLM API (future):
```python
import requests

response = requests.post(
    "https://llm.vectorweight.com/v1/images/generations",
    headers={"Authorization": f"Bearer {LITELLM_KEY}"},
    json={
        "model": "sdxl",
        "prompt": "sunset over mountains",
        "n": 1,
        "size": "1024x1024"
    }
)
```

### Open WebUI Functions

Create custom functions that combine chat + generation:
```python
# Example: Generate image based on conversation
def generate_contextual_image(chat_history):
    # Analyze conversation
    # Extract visual concepts
    # Generate image
    # Return inline in chat
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│ User Interface Layer                            │
├─────────────────────────────────────────────────┤
│ • Open WebUI (chat + tools)                    │
│ • ComfyUI Web UI (workflows)                   │
│ • n8n (automation)                             │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│ API Layer                                       │
├─────────────────────────────────────────────────┤
│ • ComfyUI REST API (http://comfyui:8188)       │
│ • WebSocket (live previews)                    │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│ Compute Layer (GPU Worker)                     │
├─────────────────────────────────────────────────┤
│ • NVIDIA RTX 5080 (16GB VRAM)                  │
│ • ComfyUI nodes (sampling, VAE, etc.)          │
│ • Model storage (NFS: /data/comfyui/models)    │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│ Storage Layer                                   │
├─────────────────────────────────────────────────┤
│ • Models: /data/comfyui/models/ (50GB)         │
│ • Outputs: /data/comfyui/output/ (100GB)       │
│ • Workflows: config/comfyui-workflows/         │
└─────────────────────────────────────────────────┘
```

---

## Resources

**Documentation**:
- ComfyUI Official: https://github.com/comfyanonymous/ComfyUI
- SDXL Guide: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- Wan 2.1: https://huggingface.co/Lightricks/Wan2.1

**Tools**:
- `config/openwebui-tools/image_generation.py` - Image tool
- `config/openwebui-tools/video_generation.py` - Video tool (v2.2.0 with streaming)
- `config/comfyui-workflows/` - Pre-built workflows
- `config/n8n-workflows/` - Automation workflows

**Monitoring**:
- ComfyUI UI: http://192.168.1.99:8188/
- Grafana Dashboard: https://grafana.vectorweight.com
- GPU Metrics: `ssh akula-prime nvidia-smi`

---

**Last Updated**: 2026-02-20
**Version**: 1.0.0
