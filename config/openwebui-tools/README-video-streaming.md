# Video Generation Streaming Guide

## Overview

The video generation tool now supports **progressive streaming** and **real-time previews**, eliminating blind waiting during long video generation jobs.

## Key Features

### 1. Non-Blocking Generation

Videos generate in the background. The tool returns immediately with job details, allowing users to continue chatting while generation runs.

**Before** (v2.1.0):
```
User: Generate a video of a sunset
[waits 3-5 minutes with no feedback]
Tool: Video generated!
```

**After** (v2.2.0):
```
User: Generate a video of a sunset
Tool: ✅ Video generation started!
      Estimated time: 66 seconds
      Monitor progress at: http://comfyui:8188/
      Prompt ID: abc123
[user can continue chatting]
User: Check video generation status for abc123
Tool: Video generation completed!
      Frames: 33
      Preview URLs: [list of frame URLs]
```

### 2. Progressive Preview Streaming

ComfyUI generates **latent-space previews** during sampling, updated every few steps. Users can monitor progress visually:

**Configuration** (`helm/gpu-worker/values.yaml`):
```yaml
env:
  - name: COMMANDLINE_ARGS
    value: "--lowvram --preview-method latent2rgb --enable-cors-header *"
  - name: COMFYUI_PREVIEW_METHOD
    value: "latent2rgb"  # Fast previews (faster than full decode)
  - name: COMFYUI_PREVIEW_QUALITY
    value: "75"  # JPEG quality (lower = faster streaming)
```

**Preview Methods**:
| Method | Speed | Quality | Use Case |
|--------|-------|---------|----------|
| `none` | N/A | N/A | No previews (fastest generation) |
| `latent2rgb` | **Fast** | Medium | **Recommended** - Real-time streaming |
| `auto` | Medium | High | Balanced (auto-selects based on model) |
| `full` | Slow | Highest | High-quality previews (slows generation) |

### 3. Frame-by-Frame Access

All generated frames are accessible via direct URLs:

```python
# Example output from check_generation_status()
Frames generated: 33

Preview URLs:
  - OpenWebUI_video_00001_.png (output): http://comfyui:8188/view?filename=OpenWebUI_video_00001_.png
  - OpenWebUI_video_00002_.png (output): http://comfyui:8188/view?filename=OpenWebUI_video_00002_.png
  ...
  - OpenWebUI_video_00033_.png (output): http://comfyui:8188/view?filename=OpenWebUI_video_00033_.png
```

Users can:
- View individual frames in browser
- Download frames for manual editing
- Create custom video sequences

### 4. Status Monitoring

The `check_generation_status(prompt_id)` method provides:
- Queue position (if waiting)
- Generation progress (if running)
- Preview URLs (when completed)
- Error details (if failed)

**Usage**:
```python
# In Open WebUI chat
User: Check video generation status for abc123

Tool: Video is currently generating (prompt_id: abc123).
      Check again in a moment for previews.

# OR if completed:
Tool: Video generation completed!
      Frames: 33
      Preview URLs: [list of all frames]
```

---

## Technical Implementation

### Architecture

```
Open WebUI
    ↓ (generate_video call)
ComfyUI API (/prompt)
    ↓ (submit workflow, return prompt_id immediately)
Background Generation
    ↓ (generates latent previews every N steps)
WebSocket Updates (optional - future)
    ↓
Status Polling (/history/<prompt_id>)
    ↓ (check_generation_status call)
Frame URLs (/view?filename=...)
```

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prompt` | POST | Submit video generation workflow |
| `/queue` | GET | Check queue status (running/pending jobs) |
| `/history/<prompt_id>` | GET | Get completed job outputs |
| `/view?filename=<file>` | GET | Access generated frame images |

### Memory-Efficient Encoding

**Configuration Optimizations**:
1. **Latent Preview Method**: Previews generated in latent space (lower resolution, faster)
2. **JPEG Quality 75**: Reduced file size for faster network transfer
3. **VRAM Management**: `--lowvram` offloads models to RAM between frames
4. **Chunked Processing**: Frames generated sequentially to avoid OOM

**Video Parameters**:
- Max frames clamped to 81 (safety limit for 16GB VRAM)
- Max resolution 720x480 (prevents excessive memory usage)
- Max steps clamped to 40 (prevents extremely long generation)

---

## Usage Examples

### Example 1: Generate Video with Progress Monitoring

```python
# User asks:
"Create a video of a cat playing piano"

# Tool response:
✅ Video generation started with Wan 2.1!

**Job Details:**
  - Prompt: 'a cat playing piano, photorealistic, high quality'
  - Frames: 33, Resolution: 480x320
  - Steps: 20, Seed: 1234567890
  - Prompt ID: abc123

**Monitor Progress:**
  1. ComfyUI generates preview frames during generation
  2. View live progress at: http://comfyui:8188/
  3. Estimated time: 66 seconds

**Check Status:**
  Ask me to 'check video generation status for abc123'

# User continues chatting...

# After 1 minute:
"Check video generation status for abc123"

# Tool response:
Video generation completed!
Status: success
Frames generated: 33

Preview URLs:
  - OpenWebUI_video_00001_.png: http://comfyui:8188/view?filename=OpenWebUI_video_00001_.png
  - OpenWebUI_video_00002_.png: http://comfyui:8188/view?filename=OpenWebUI_video_00002_.png
  ...
```

### Example 2: Queue Management

```python
# Scenario: Multiple videos queued

"Generate a sunset video"
→ Video queued at position 2

"Check status for abc123"
→ Video is queued at position 1 (prompt_id: abc123). Waiting to start...

# Wait for queue to advance

"Check status for abc123"
→ Video is currently generating. Check again in a moment.

# Wait for completion

"Check status for abc123"
→ Video generation completed! [frames listed]
```

---

## Performance Characteristics

### Generation Times (Wan 2.1 1.3B, RTX 5080 16GB)

| Frames | Resolution | Steps | Time | VRAM |
|--------|------------|-------|------|------|
| 33 | 480x320 | 20 | ~60s | ~8GB |
| 49 | 480x320 | 20 | ~90s | ~10GB |
| 81 | 480x320 | 20 | ~150s | ~14GB |
| 33 | 720x480 | 30 | ~120s | ~12GB |

### Preview Update Rate

- **Latent previews**: Updated every 1-2 steps (~3-5 seconds)
- **Full previews**: Updated every 5 steps (~15-20 seconds)
- **No previews**: 0 overhead (fastest generation)

### Network Transfer

| Preview Method | File Size (per preview) | Bandwidth (33 frames) |
|----------------|-------------------------|------------------------|
| latent2rgb (JPEG 75) | ~50KB | ~1.6MB |
| auto (PNG) | ~500KB | ~16MB |
| full (PNG) | ~1MB | ~33MB |

---

## Future Enhancements

### Planned (Not Yet Implemented)

1. **WebSocket Streaming**:
   - Real-time progress updates via websocket connection
   - Eliminates polling overhead
   - Requires async Open WebUI tool support

2. **Video Assembly**:
   - Automatic MP4 encoding via VHS_VideoCombine node
   - FFmpeg integration for codec selection
   - Direct video URL return (instead of frame list)

3. **Adaptive Quality**:
   - Auto-adjust preview quality based on network speed
   - Progressive enhancement (low-res → high-res)

4. **Batch Generation**:
   - Generate multiple videos in parallel
   - Queue management UI

---

## Troubleshooting

### Previews Not Showing

**Issue**: "Video generation completed but no preview URLs"

**Diagnosis**:
```bash
# Check ComfyUI logs
kubectl logs -n gpu-workloads deployment/comfyui -f

# Check output directory permissions
kubectl exec -n gpu-workloads deployment/comfyui -- ls -la /output
```

**Fix**:
- Ensure `--preview-method latent2rgb` is set (check deployment env vars)
- Verify output directory is writable
- Check ComfyUI version supports preview method

### Slow Preview Generation

**Issue**: Previews update very slowly (> 30 seconds between updates)

**Diagnosis**:
- Check if using `--preview-method full` (too slow)
- Verify VRAM not exhausted (`nvidia-smi` on GPU worker)

**Fix**:
```yaml
# helm/gpu-worker/values.yaml
env:
  - name: COMMANDLINE_ARGS
    value: "--lowvram --preview-method latent2rgb"  # Use latent2rgb, not full
  - name: COMFYUI_PREVIEW_QUALITY
    value: "60"  # Lower quality = faster (50-75 recommended)
```

### Cross-Origin Errors

**Issue**: "CORS error when accessing preview URLs from Open WebUI"

**Fix**:
```yaml
# helm/gpu-worker/values.yaml
env:
  - name: COMMANDLINE_ARGS
    value: "--enable-cors-header *"  # Allow all origins (or specify Open WebUI URL)
```

---

## Configuration Reference

### ComfyUI Environment Variables

```yaml
# helm/gpu-worker/values.yaml
comfyui:
  env:
    # Core arguments
    - name: COMMANDLINE_ARGS
      value: "--lowvram --preview-method latent2rgb --enable-cors-header *"

    # Preview configuration
    - name: COMFYUI_PREVIEW_METHOD
      value: "latent2rgb"  # Options: none, latent2rgb, auto, full

    - name: COMFYUI_PREVIEW_QUALITY
      value: "75"  # JPEG quality: 50-100 (lower = faster, smaller files)

    # Memory optimization
    - name: PYTORCH_CUDA_ALLOC_CONF
      value: "max_split_size_mb:512"  # Prevent fragmentation
```

### Tool Configuration

```python
# config/openwebui-tools/video_generation.py
class Valves(BaseModel):
    comfyui_base_url: str = "http://comfyui:8188"
    timeout: int = 300  # Max wait time for status checks
```

---

## Deployment

1. **Update Helm values**:
   ```bash
   # Edit helm/gpu-worker/values.yaml
   # Set comfyui.enabled: true
   # Configure preview streaming env vars
   ```

2. **Update Open WebUI tool**:
   ```bash
   # Copy config/openwebui-tools/video_generation.py
   # to Open WebUI's tools directory (or upload via UI)
   ```

3. **Apply changes**:
   ```bash
   kubectl apply -f argocd/applications/comfyui.yaml
   argocd app sync comfyui
   ```

4. **Verify**:
   ```bash
   # Check ComfyUI pod
   kubectl get pods -n gpu-workloads -l app=comfyui

   # Test preview endpoint
   curl http://comfyui.gpu-workloads:8188/
   ```

---

**Version**: 2.2.0 (Progressive Streaming Support)
**Last Updated**: 2026-02-20
