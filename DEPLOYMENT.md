# Deployment Status - January 11, 2026

## ✅ Server Stack (192.168.1.170) - DEPLOYED

### Services Running
- **Open WebUI v0.7.2**: ✓ Running on http://192.168.1.170:3001
- **Ollama CPU 0.13.5**: ✓ Running on http://192.168.1.170:11434
- **Redis 8.4.0-alpine**: ✓ Running on port 6379

### Deployment Details
```bash
Location: /home/kang/Documents/projects/github/self-hosted-ai/server
Command: COMPOSE_PROFILES="basic" docker compose up -d
Status: All services healthy and responding
```

### Configuration
- Profile: `basic` (Open WebUI + Ollama CPU + Redis)
- Environment: server/.env configured
- Data Path: /data (bind mounts)
- Ports:
  - 3001: Open WebUI web interface
  - 11434: Ollama CPU API
  - 6379: Redis

### Verified Endpoints
```bash
✓ curl http://localhost:11434/api/version
✓ curl http://localhost:3001/
✓ docker exec redis-server redis-cli ping
```

## ⚠️ GPU Worker (192.168.1.99) - REQUIRES MANUAL DEPLOYMENT

The GPU worker **cannot** be deployed from this local machine because:
1. No NVIDIA GPU drivers available locally
2. ComfyUI image requires CUDA runtime
3. Ollama GPU requires nvidia-container-toolkit

### GPU Worker Deployment Steps

**On 192.168.1.99 (akula-prime):**

```bash
# 1. Clone/pull latest code
cd /path/to/self-hosted-ai
git checkout dev
git pull origin dev

# 2. Verify .env configuration
cd gpu-worker
cat .env  # Ensure DATA_PATH and ports are correct

# 3. Deploy GPU worker stack
docker compose up -d

# 4. Verify deployment
docker compose ps
curl http://localhost:11434/api/tags  # Ollama GPU
curl http://localhost:8188/system_stats  # ComfyUI

# 5. Check GPU usage
nvidia-smi
```

### GPU Worker Services
- **Ollama GPU 0.13.5**: Port 11434 (GPU-accelerated inference)
- **ComfyUI v2**: Port 8188 (CUDA 12.1.1, image generation)

### ComfyUI Setup (First Time)
After deployment, initialize ComfyUI workflows:

```bash
# On GPU worker
./scripts/comfyui-setup.sh init     # Copy workflow files
./scripts/comfyui-setup.sh models   # Download base models
./scripts/comfyui-setup.sh status   # Verify setup
```

## Multi-Agent Framework

The Python agent framework and Rust runtime are now available for development:

```bash
# Setup development environment
./scripts/setup-dev.sh

# Activate Python environment
cd agents
source venv/bin/activate

# Run tests
pytest tests/ -v

# Build Rust runtime (optional)
cd ../rust-agents
cargo build --release
```

## Network Topology

```
┌─────────────────────────────────────────────┐
│ Client Browser                               │
│ http://192.168.1.170:3001                   │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Server (192.168.1.170)                      │
├─────────────────────────────────────────────┤
│ • Open WebUI v0.7.2                         │
│ • Ollama CPU 0.13.5                         │
│ • Redis 8.4.0                               │
└──────────────────┬──────────────────────────┘
                   │ (Ollama API calls)
┌──────────────────▼──────────────────────────┐
│ GPU Worker (192.168.1.99)                   │
├─────────────────────────────────────────────┤
│ • Ollama GPU 0.13.5 (RTX 5080)             │
│ • ComfyUI v2 (Image Generation)            │
└─────────────────────────────────────────────┘
```

## Next Steps

### Immediate
1. [ ] Deploy GPU worker on 192.168.1.99
2. [ ] Initialize ComfyUI workflows
3. [ ] Test image generation from Open WebUI

### Optional
1. [ ] Load models using bootstrap.sh
2. [ ] Enable monitoring profile (Prometheus + Grafana)
3. [ ] Configure custom ComfyUI workflows

## Useful Commands

### Server Management
```bash
./scripts/deploy-server.sh status          # Check status
./scripts/deploy-server.sh logs            # View logs
./scripts/deploy-server.sh stop            # Stop stack
./scripts/deploy-server.sh deploy          # Redeploy
```

### GPU Worker Management
```bash
./scripts/deploy-gpu-worker.sh status      # Check status
./scripts/deploy-gpu-worker.sh logs        # View logs
./scripts/deploy-gpu-worker.sh comfyui     # ComfyUI status
```

### Model Management
```bash
./scripts/bootstrap.sh pull-models         # Sync models from manifest
./scripts/deploy-server.sh pull-model llama3.1:8b cpu
./scripts/deploy-gpu-worker.sh pull-model codellama:13b
```

## Troubleshooting

### Server Stack Issues
```bash
# View logs
docker compose -f server/docker-compose.yml logs -f

# Restart a specific service
docker compose -f server/docker-compose.yml restart open-webui

# Check container health
docker inspect open-webui-server | jq '.[0].State.Health'
```

### GPU Worker Issues
```bash
# Check GPU availability
nvidia-smi

# Verify NVIDIA container runtime
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi

# Check ComfyUI logs
docker logs comfyui-worker -f
```

## Git Status

Current branch: `dev`  
Latest commit: `2babe2c feat(rust): Add Python FFI bindings with PyO3`

All changes committed and pushed to GitHub.

---

**Deployment Date**: January 11, 2026  
**Deployed By**: Automated deployment script  
**Server Status**: ✅ Running  
**GPU Worker Status**: ⚠️ Awaiting deployment on target hardware
