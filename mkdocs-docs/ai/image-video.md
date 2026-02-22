---
title: Image & Video Generation
description: GPU-accelerated image and video generation services
---

# Image & Video Generation

## Services

All generation services run on the GPU worker (akula-prime) in the `gpu-workloads` namespace:

| Service | Purpose | Port |
|---------|---------|------|
| ComfyUI | Image generation (Stable Diffusion) | 8188 |
| Audio Server | TTS and audio generation (Bark) | 8000 |
| Video Server | Video generation (AnimateDiff) | 8000 |

## ComfyUI

ComfyUI provides a node-based interface for Stable Diffusion workflows.

**Workflows**: Pre-built workflows in `config/comfyui-workflows/`

**Model Storage**: Models stored in NFS-backed `shared-models-nfs` PVC (500Gi)

## Audio Generation

Custom audio server using Bark for text-to-speech:

- **Container**: `containers/audio-server/`
- **API**: REST endpoint for TTS generation

## Video Generation

Custom video server using AnimateDiff:

- **Container**: `containers/video-server/`
- **API**: REST endpoint for video generation

## GPU Resources

The RTX 5080 (16GB VRAM) is shared across these services. Monitor GPU usage:

```bash
# Check GPU workloads
kubectl get pods -n gpu-workloads

# Check GPU memory usage
kubectl exec -n gpu-workloads deployment/ollama-gpu -- nvidia-smi
```
