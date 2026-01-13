# Self-Hosted AI Stack - Getting Started Guide

**Version:** 2.0.0 | **Last Updated:** January 11, 2026

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- **Server Node** (192.168.1.170): Linux with Docker & Docker Compose
- **GPU Worker Node** (192.168.1.99): Linux with NVIDIA GPU, CUDA, nvidia-container-toolkit

### 1. Clone Repository
```bash
# On both nodes
git clone https://github.com/tzervas/self-hosted-ai.git
cd self-hosted-ai
git checkout main
```

### 2. Configure Environment

**Server Node:**
```bash
cd server
cp .env.example .env
# Edit .env with your settings:
# - WEBUI_SECRET_KEY (generate with: openssl rand -hex 32)
# - GPU_WORKER_HOST=192.168.1.99
```

**GPU Worker Node:**
```bash
cd gpu-worker
cp .env.example .env
# Edit .env:
# - DATA_PATH=/data (or your preferred path)
```

### 3. Deploy

**Server Node:**
```bash
cd server
docker compose --profile basic up -d
```

**GPU Worker Node:**
```bash
cd gpu-worker
docker compose up -d
```

### 4. Access Services

| Service | URL | Description |
|---------|-----|-------------|
| **Open WebUI** | http://192.168.1.170:3000 | Main AI chat interface |
| **SearXNG** | http://192.168.1.170:8080 | Search engine |
| **ComfyUI** | http://192.168.1.99:8188 | Node-based image generation |
| **A1111 WebUI** | http://192.168.1.99:7860 | Stable Diffusion interface |
| **Grafana** | http://192.168.1.170:3001 | Monitoring dashboard |

---

## 📋 Full Deployment Profiles

### Server Profiles

| Profile | Services | Use Case |
|---------|----------|----------|
| `basic` | Open WebUI, Ollama CPU, Redis, SearXNG | Standard chat + search |
| `full` | + Ingest Service | + Document processing |
| `monitoring` | + Prometheus, Grafana, Node Exporter | + Observability |

```bash
# Deploy with profile
docker compose --profile monitoring up -d
```

### GPU Worker Services

All services start by default:
- Ollama GPU (inference)
- ComfyUI (image/video generation)
- Automatic1111 (Stable Diffusion)
- Whisper (audio transcription)
- GPU Manager (resource allocation)

---

## 🔑 Default Credentials

| Service | Username | Password | Notes |
|---------|----------|----------|-------|
| Open WebUI | Create on first visit | Your choice | Admin is first signup |
| Grafana | admin | admin | Change on first login |
| ComfyUI | - | - | No auth by default |
| A1111 | - | - | No auth by default |

---

## 🌐 Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     LAN (192.168.1.0/24)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │  Server Node        │    │  GPU Worker Node            │ │
│  │  192.168.1.170      │    │  192.168.1.99               │ │
│  │                     │    │                             │ │
│  │  ├─ Open WebUI:3000 │◄──►│  ├─ Ollama GPU:11434       │ │
│  │  ├─ Ollama CPU:11434│    │  ├─ ComfyUI:8188           │ │
│  │  ├─ SearXNG:8080    │    │  ├─ A1111:7860             │ │
│  │  ├─ Redis:6379      │    │  ├─ Whisper:9000           │ │
│  │  ├─ Grafana:3001    │    │  └─ GPU Manager:8100       │ │
│  │  └─ Prometheus:9090 │    │                             │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Sync Your Models

If you have local models to sync:

```bash
# From your development machine
./scripts/sync-models.sh list      # View local models
./scripts/sync-models.sh sync      # Sync all to GPU worker
./scripts/sync-models.sh status    # Check sync status
```

---

## ✅ Verify Installation

```bash
# Server health checks
curl http://192.168.1.170:3000/health        # Open WebUI
curl http://192.168.1.170:11434/api/tags     # Ollama CPU
curl http://192.168.1.170:8080/healthz       # SearXNG

# GPU worker health checks
curl http://192.168.1.99:11434/api/tags      # Ollama GPU
curl http://192.168.1.99:8188/system_stats   # ComfyUI
curl http://192.168.1.99:7860/sdapi/v1/sd-models  # A1111
curl http://192.168.1.99:9000/health         # Whisper
```

---

## 🆘 Troubleshooting

### Common Issues

**1. GPU not detected:**
```bash
nvidia-smi                         # Verify NVIDIA driver
docker run --gpus all nvidia/cuda:12.1.0-base nvidia-smi
```

**2. Services not starting:**
```bash
docker compose logs -f <service>   # Check logs
docker compose ps                  # Check status
```

**3. Connection refused:**
- Ensure firewall allows ports (3000, 8080, 8188, 7860, 11434, 9000)
- Check `GPU_WORKER_HOST` in server `.env`

---

## 📚 Next Steps

1. **[Usage Guide](USAGE_GUIDE.md)** - Detailed feature walkthrough
2. **[Workflow Guides](WORKFLOW_GUIDES.md)** - Image, video, audio workflows
3. **[How to Build](HOW_TO_BUILD.md)** - Custom workflows and extensions
4. **[API Reference](API_REFERENCE.md)** - API documentation

---

*Need help? Open an issue on GitHub or check the documentation.*
