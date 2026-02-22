---
title: GPU Worker Setup
description: GPU workstation configuration and management
---

# GPU Worker Setup

The GPU worker (akula-prime, 192.168.1.99) is the k3s control-plane node with GPU resources.

## Hardware

- **CPU**: Intel 14700K
- **RAM**: 48GB DDR5
- **GPU**: NVIDIA RTX 5080 (16GB VRAM)
- **Role**: Kubernetes control-plane + GPU workload execution
- **Container Runtime**: containerd 2.1.5-k3s1

## GPU Workloads

GPU workloads run in the `gpu-workloads` namespace with nvidia-gpu-operator managing device plugins.

| Service | Port | Purpose |
|---------|------|---------|
| Ollama GPU | 11434 | GPU inference (RTX 5080) |
| ComfyUI | 8188 | Image generation |
| Audio Server | 8000 | TTS/Audio generation |
| Video Server | 8000 | Video generation |

## Model Storage

Models are stored on NFS-backed shared storage:

- **PVC**: `shared-models-nfs` (500Gi)
- **NFS Server**: homelab (192.168.1.170)
- **Mount Path**: `/data/models`

## Management Commands

```bash
# Check GPU workloads
kubectl get pods -n gpu-workloads

# Check GPU availability
kubectl get node akula-prime -o json | \
  jq '.status.allocatable | with_entries(select(.key | contains("nvidia")))'

# Test Ollama GPU service
kubectl exec -n ai-services deployment/ollama -- \
  curl http://ollama-gpu.gpu-workloads:11434/api/tags

# GPU operator status
kubectl get pods -n gpu-operator

# Restart ollama-gpu if needed
kubectl rollout restart deployment/ollama-gpu -n gpu-workloads
```
