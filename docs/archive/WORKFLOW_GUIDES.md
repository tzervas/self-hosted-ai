# Self-Hosted AI Stack - Workflow Guides

**Version:** 2.0.0 | **Last Updated:** January 11, 2026

---

## Table of Contents

1. [Text-to-Image Workflows](#text-to-image-workflows)
2. [Image-to-Image Workflows](#image-to-image-workflows)
3. [Upscaling Workflows](#upscaling-workflows)
4. [Video Generation Workflows](#video-generation-workflows)
5. [Audio Processing Workflows](#audio-processing-workflows)
6. [Multimodal Pipelines](#multimodal-pipelines)
7. [Research Workflows](#research-workflows)
8. [Custom Workflow Creation](#custom-workflow-creation)

---

## Text-to-Image Workflows

### SDXL (Recommended)

**File:** `txt2img-sdxl.json`  
**VRAM:** 8GB minimum  
**Quality:** High  
**Speed:** ~30 seconds

**How to use:**
1. Open ComfyUI: http://192.168.1.99:8188
2. Click "Load" → select `txt2img-sdxl.json`
3. Find the "Positive Prompt" node
4. Enter your prompt:
   ```
   A majestic snow-capped mountain at sunrise, dramatic clouds, 
   golden hour lighting, professional landscape photography, 8k
   ```
5. Find the "Negative Prompt" node, keep or modify:
   ```
   blurry, low quality, distorted, watermark, text, ugly, deformed
   ```
6. Click "Queue Prompt"

**Best practices:**
- Include style keywords: "digital art", "oil painting", "photograph"
- Specify quality: "8k", "detailed", "professional"
- Add lighting: "golden hour", "dramatic lighting", "soft light"

---

### FLUX.1 Schnell (Fast High-Quality)

**File:** `txt2img-flux-schnell.json`  
**VRAM:** 12GB minimum  
**Quality:** Very High  
**Speed:** ~20 seconds

**Advantages:**
- Better text rendering
- More coherent compositions
- Faster than SDXL at higher quality

**Example prompt:**
```
A cyberpunk hacker in a neon-lit room surrounded by holographic displays,
detailed face, cinematic lighting, movie poster quality
```

---

### SD 1.5 (Low VRAM)

**File:** `txt2img-sd15.json`  
**VRAM:** 4GB minimum  
**Quality:** Good  
**Speed:** ~15 seconds

**When to use:**
- Limited VRAM
- Quick drafts
- High volume generation

---

## Image-to-Image Workflows

### SDXL img2img

**File:** `img2img-sdxl.json`  
**VRAM:** 8GB

**How to use:**
1. Load the workflow
2. Upload your source image to the "LoadImage" node
3. Set denoising strength (0.3-0.7 recommended):
   - 0.3: Minor changes, keep structure
   - 0.5: Balanced changes
   - 0.7: Major changes, loose structure
4. Enter prompt describing desired output

**Use cases:**
- Style transfer
- Adding/modifying elements
- Improving composition

---

### Image Analysis & Variation

**File:** `img2img-caption.json`  
**VRAM:** 12GB

**What it does:**
1. Analyzes input image with BLIP
2. Generates detailed caption
3. Uses caption to create variation

**Great for:**
- Understanding what's in an image
- Creating similar images
- Inspiration generation

---

### Inpainting

**File:** `inpaint-sdxl.json`  
**VRAM:** 10GB

**How to use:**
1. Upload your image
2. Create a mask (white = areas to regenerate)
3. Prompt describes what should fill masked areas

**Tips:**
- Feather mask edges for smoother blending
- Use context in prompt: "a cat sitting on the couch" not just "cat"

---

## Upscaling Workflows

### 2x Upscale (Real-ESRGAN)

**File:** `upscale-2x.json`  
**VRAM:** 4GB  
**Speed:** ~5 seconds

**Best for:**
- Doubling resolution
- General enhancement
- Photos and illustrations

---

### 4x Upscale

**File:** `upscale-4x.json`  
**VRAM:** 6GB  
**Speed:** ~10 seconds

**Best for:**
- Large prints
- Recovering low-res images
- Maximum detail

---

### Pipeline: Generate + Upscale

**File:** `pipeline-generate-upscale.json`  
**VRAM:** 10GB

**What it does:**
1. Generates image at 1024x1024
2. Automatically upscales to 2048x2048

**Perfect for:**
- High-res outputs
- Print-ready images

---

## Video Generation Workflows

### Text-to-Video (WAN 1.3B)

**File:** `text2video-wan.json`  
**VRAM:** 12GB  
**Duration:** 1-3 seconds  
**Generation time:** 2-5 minutes

**How to use:**
1. Load workflow
2. Enter motion-focused prompt:
   ```
   A butterfly flying through a field of flowers, smooth motion,
   natural lighting, cinematic, 4k
   ```
3. Set frame count (24 frames = 1 second)
4. Queue and wait

**Motion keywords:**
- walking, running, flying, floating
- rotating, spinning, orbiting
- flowing, waving, rippling
- zooming, panning, tracking

---

### Stable Video Diffusion (Image-to-Video)

**File:** `text2video-svd.json`  
**VRAM:** 16GB  
**Duration:** 2-4 seconds

**How to use:**
1. Upload a source image
2. The model animates it with natural motion
3. Works best with images that have clear subjects

**Tips:**
- Use high-quality source images
- Subjects with clear motion potential work best
- Landscape/background images create subtle parallax effects

---

## Audio Processing Workflows

### Audio Transcription

**Endpoint:** http://192.168.1.99:9000/asr

**Via cURL:**
```bash
curl -X POST "http://192.168.1.99:9000/asr" \
  -F "audio_file=@recording.mp3" \
  -F "output=json"
```

**Via Python:**
```python
import httpx

with open("audio.mp3", "rb") as f:
    response = httpx.post(
        "http://192.168.1.99:9000/asr",
        files={"audio_file": f},
        params={"output": "json", "task": "transcribe"}
    )

result = response.json()
print(result["text"])
```

**Options:**
- `task`: "transcribe" or "translate" (to English)
- `language`: ISO code or "auto"
- `output`: "json", "txt", "srt", "vtt"

---

### Audio-to-Image

**File:** `audio2img.json`  
**VRAM:** 10GB

**What it does:**
1. Transcribes audio with Whisper
2. Converts transcription to image prompt
3. Generates image from the content

**Use cases:**
- Podcast episode covers
- Music visualization
- Meeting summary visuals

---

## Multimodal Pipelines

### Full Pipeline (Audio → Image → Video)

**File:** `full-multimodal-pipeline.json`  
**VRAM:** 16GB  
**Time:** 3-5 minutes

**The complete flow:**
```
Audio Input
    ↓
Whisper Transcription
    ↓
LLM Prompt Enhancement
    ↓
SDXL Image Generation
    ↓
Real-ESRGAN Upscaling
    ↓
WAN Video Generation
    ↓
Final Video Output
```

**Perfect for:**
- Content repurposing
- Automated video creation
- Multi-format output from single input

---

### Full Agentic Pipeline (Image)

**File:** `pipeline-full-agentic.json`  
**VRAM:** 14GB

**Steps:**
1. Generate with SDXL base
2. Refine with SDXL refiner
3. Upscale with Real-ESRGAN

**Best for:**
- Maximum quality images
- Print and publication
- Professional output

---

## Research Workflows

### Automated Research

**Trigger via API:**
```bash
curl -X POST http://192.168.1.170:8300/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "quantum computing in cryptography",
    "depth": "comprehensive",
    "sources": ["academic", "technical", "news"],
    "generate_report": true,
    "generate_visuals": true
  }'
```

**Depth options:**
- `quick`: 5-10 sources, brief summary
- `standard`: 15-20 sources, detailed analysis
- `comprehensive`: 30+ sources, full report with citations

**Output:**
- Markdown report
- PDF (optional)
- Visual summary (optional)
- Source citations

---

### In-Chat Research

```
/research [topic]
```

**Examples:**
```
/research latest advancements in fusion energy
/research comparison of transformer architectures 2024-2026
/research ethical considerations in AI development
```

---

## Custom Workflow Creation

### Building Your Own Workflow

1. **Start simple:**
   - Begin with an existing workflow
   - Modify one node at a time
   - Test after each change

2. **Common node patterns:**
   ```
   Checkpoint Loader → CLIP Encoder → Sampler → VAE Decode → Save
   ```

3. **Adding steps:**
   - Connect output of one stage to input of next
   - Use "Reroute" nodes for cleaner layouts

### Example: Custom Style Workflow

```json
{
  "nodes": [
    {"type": "CheckpointLoader", "id": 1},
    {"type": "LoRALoader", "id": 2},      // Add LoRA for style
    {"type": "CLIPTextEncode", "id": 3},
    {"type": "KSampler", "id": 4},
    {"type": "VAEDecode", "id": 5},
    {"type": "SaveImage", "id": 6}
  ],
  "links": [
    [1, 2],  // Checkpoint → LoRA
    [2, 3],  // LoRA → CLIP
    // ... etc
  ]
}
```

### Sharing Workflows

Save your workflows to `/data/comfyui/workflows/` and they'll appear in the Open WebUI image generation options.

---

## Performance Tips by Workflow Type

| Workflow Type | Optimization Tips |
|---------------|-------------------|
| txt2img | Lower steps (20-30), use turbo/schnell variants |
| img2img | Keep denoising <0.7, resize input to target size |
| Upscaling | Process in batches, use fp16 |
| Video | Reduce frame count, use lower resolution then upscale |
| Multimodal | Queue during low-usage, use GPU manager priorities |

---

## Troubleshooting Workflows

**"Out of memory":**
- Reduce image size
- Use lower-VRAM workflow variant
- Close other GPU services temporarily

**"Black image output":**
- Check VAE is connected
- Verify checkpoint loaded correctly
- Try different seed

**"Workflow not loading":**
- Check JSON syntax
- Verify all required custom nodes installed
- Check ComfyUI logs

---

*For building custom workflows and extensions, see [How to Build](HOW_TO_BUILD.md).*
