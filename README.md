# Self-Hosted AI Stack

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready, self-hosted AI deployment using Ollama and Open WebUI with distributed GPU/CPU inference across LAN.

## Architecture

This stack runs Open WebUI on a server with CPU Ollama for lightweight tasks, connecting to a GPU worker for accelerated inference on larger coding models.

```text
+-----------------------------------------------------------------------------+
|                     Distributed AI Stack (Server + GPU Worker)              |
+-----------------------------------------------------------------------------+
|                                                                             |
|  +-------------------------------------+    +----------------------------+  |
|  |      Server (homelab)               |    |   GPU Worker (workstation) |  |
|  |      192.168.1.170                  |    |      192.168.1.99          |  |
|  |  +--------------+  +-------------+  |    |  +----------------------+  |  |
|  |  |  Open WebUI  |  | Ollama CPU  |  |    |  |    Ollama GPU        |  |  |
|  |  |    :3001     |  |   :11434    |  |    |  |      :11434          |  |  |
|  |  |              |  |  (fallback) |  |    |  |    RTX 5080 16GB     |  |  |
|  |  +------+-------+  +-------------+  |    |  +----------^-----------+  |  |
|  |         |                           |    |             |              |  |
|  |         |   Image Gen               |    |  +----------+-----------+  |  |
|  |         +-------------------------->|    |  |      ComfyUI         |  |  |
|  |                                     |    |  |       :8188          |  |  |
|  |  +------+-------+  +-------------+  |    |  |   SDXL/SD Models     |  |  |
|  |  |    Redis     |  | Prometheus  |  |    |  +----------------------+  |  |
|  |  |   :6379      |  |   :9090     |  |    +-------------|--------------+  |
|  |  +--------------+  +-------------+  |                  | LAN             |
|  |                    +-------------+  |<-----------------+                 |
|  |                    |  Grafana    |  |                                    |
|  |                    |   :3000     |  |                                    |
|  |                    +-------------+  |                                    |
|  +-------------------------------------+                                    |
|                                                                             |
|  Best for: 24/7 availability, GPU on-demand, resource separation            |
+-----------------------------------------------------------------------------+
```

### Hardware

| Host | Role | Specs | IP |
|------|------|-------|-----|
| **homelab** | Server | Dual E5-2660v4 (28c/56t), 120GB DDR4 | 192.168.1.170 |
| **akula-prime** | GPU Worker | Intel 14700K, 48GB DDR5, RTX 5080 (16GB) | 192.168.1.99 |

## Quick Start

### Prerequisites

Both machines need:

- Docker Engine 24.0+
- Docker Compose V2

GPU machine additionally needs:

- NVIDIA Driver 550+
- NVIDIA Container Toolkit

```bash
# Install NVIDIA Container Toolkit (GPU worker only)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Step 1: Clone and Bootstrap

```bash
git clone https://github.com/tzervas/self-hosted-ai.git
cd self-hosted-ai

# Install pre-commit hooks
./scripts/bootstrap.sh setup
```

### Step 2: Deploy GPU Worker (akula-prime)

```bash
# Copy and configure environment
cp gpu-worker/.env.example gpu-worker/.env

# Deploy
./scripts/deploy-gpu-worker.sh deploy
```

### Step 3: Deploy Server Stack (homelab)

```bash
# Copy and configure environment (CHANGE SECRETS!)
cp server/.env.example server/.env
# Edit server/.env - set WEBUI_SECRET_KEY and GRAFANA_ADMIN_PASSWORD

# Deploy with monitoring
./scripts/deploy-server.sh deploy monitoring
```

### Step 4: Sync Models

```bash
# Interactive mode - prompts for each model
./scripts/bootstrap.sh sync

# Or sync all missing models automatically
./scripts/bootstrap.sh sync --all
```

### Step 5: Access Open WebUI

1. Navigate to <http://192.168.1.170:3001>
2. Create admin account (first signup becomes admin)
3. Both CPU and GPU models will be available in the model selector

## Models

### GPU Worker (RTX 5080 16GB - Coding Focus)

| Model | Size | Purpose |
|-------|------|---------|
| qwen2.5-coder:14b | 8GB | Primary coding (Rust, Python, Shell) |
| phi4:latest | 8GB | Reasoning + coding |
| deepseek-coder-v2:16b | 8GB | Advanced code generation |

### CPU Server (Fallback & Embeddings)

| Model | Size | Purpose |
|-------|------|---------|
| mistral:7b | 4GB | General chat |
| phi3:latest | 2GB | Fast lightweight tasks |
| nomic-embed-text:latest | 274MB | Embeddings for RAG |

## Image Generation (ComfyUI)

ComfyUI runs on the GPU worker and integrates with Open WebUI for text-to-image generation.

### Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Image Generation Flow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    HTTP/API     ┌─────────────────────────────────────┐  │
│   │  Open WebUI │ ───────────────>│      GPU Worker (192.168.1.99)      │  │
│   │   :3001     │<─── Images ─────│  ┌────────────┐  ┌──────────────┐   │  │
│   └─────────────┘                 │  │  ComfyUI   │  │  Ollama GPU  │   │  │
│                                   │  │   :8188    │  │    :11434    │   │  │
│                                   │  │            │  │              │   │  │
│                                   │  │ ┌────────┐ │  │              │   │  │
│                                   │  │ │  SDXL  │ │  │  ┌────────┐  │   │  │
│                                   │  │ │ Models │ │  │  │ LLMs   │  │   │  │
│                                   │  │ └────────┘ │  │  └────────┘  │   │  │
│                                   │  └────────────┘  └──────────────┘   │  │
│                                   │         └───── RTX 5080 ─────┘      │  │
│                                   └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Setup ComfyUI

**1. Deploy GPU Worker with ComfyUI:**

```bash
# Update gpu-worker/.env with ComfyUI settings
cp gpu-worker/.env.example gpu-worker/.env

# Deploy (ComfyUI starts automatically with Ollama)
./scripts/deploy-gpu-worker.sh deploy
```

**2. Download Stable Diffusion Models:**

ComfyUI requires checkpoint models. Download to the GPU worker:

```bash
# SSH to GPU worker, then:
DATA_PATH=/data  # or your configured path

# Create model directories
mkdir -p ${DATA_PATH}/comfyui/models/checkpoints
mkdir -p ${DATA_PATH}/comfyui/models/vae
mkdir -p ${DATA_PATH}/comfyui/models/loras

# Download SDXL Base (recommended, ~6.5GB)
cd ${DATA_PATH}/comfyui/models/checkpoints
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors

# Or SD 1.5 for lower VRAM usage (~4GB model)
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
```

**3. Verify ComfyUI is Running:**

```bash
# Check status
./scripts/bootstrap.sh status

# Or directly test API
curl http://192.168.1.99:8188/system_stats
```

**4. Configure Open WebUI:**

Image generation is enabled by default. To customize:

```bash
# server/.env
ENABLE_IMAGE_GENERATION=true
IMAGE_GENERATION_ENGINE=comfyui
COMFYUI_BASE_URL=http://192.168.1.99:8188
```

### Using Image Generation in Open WebUI

1. Open any chat in Open WebUI
2. Type your image prompt
3. Click the image icon (🖼️) or use `/image` command
4. The request goes to ComfyUI on the GPU worker
5. Generated images appear in the chat

### Recommended Models

| Model | VRAM | Quality | Speed | Notes |
|-------|------|---------|-------|-------|
| SDXL Base 1.0 | ~8GB | Excellent | Medium | Best quality, 1024x1024 default |
| SD 1.5 | ~4GB | Good | Fast | Lower VRAM, 512x512 default |
| SDXL Turbo | ~8GB | Good | Very Fast | 1-4 steps, real-time capable |
| FLUX.1 Schnell | ~12GB | Excellent | Fast | Best prompt following |

### Available Workflows

The stack includes pre-configured workflows for different use cases:

| Workflow | Type | Description | VRAM |
|----------|------|-------------|------|
| `txt2img-sdxl` | Basic | High-quality text-to-image | 8GB |
| `txt2img-sd15` | Basic | Fast, low VRAM | 4GB |
| `txt2img-sdxl-turbo` | Fast | 4-step real-time generation | 8GB |
| `img2img-sdxl` | Edit | Transform existing images | 8GB |
| `inpaint-sdxl` | Edit | Mask-based inpainting | 10GB |
| `upscale-2x` | Enhance | 2x upscale with Real-ESRGAN | 4GB |
| `upscale-4x` | Enhance | 4x upscale | 6GB |
| `pipeline-sdxl-refiner` | Multi-step | Base → Refiner | 12GB |
| `pipeline-generate-upscale` | Multi-step | Generate → Upscale | 10GB |
| `pipeline-full-agentic` | Multi-step | Base → Refiner → Upscale | 14GB |
| `txt2img-flux-schnell` | Advanced | FLUX.1 fast generation | 12GB |

### Workflow Management

```bash
# List all available workflows
./scripts/comfyui-setup.sh list

# Show workflow details and requirements
./scripts/comfyui-setup.sh info txt2img-sdxl

# Setup a workflow (downloads required models)
./scripts/comfyui-setup.sh setup txt2img-sdxl

# Setup all required workflows
./scripts/comfyui-setup.sh setup-required

# Validate ComfyUI setup
./scripts/comfyui-setup.sh validate

# Export workflow for API use
./scripts/comfyui-setup.sh export txt2img-sdxl > workflow.json
```

### Custom Workflows

The default workflow uses SDXL with euler_ancestral sampler. To customize:

1. Design workflow in ComfyUI web UI (`http://192.168.1.99:8188`)
2. Export as API format (Save → Export API)
3. Save to `config/comfyui-workflows/my-workflow.json`
4. Add to `config/comfyui-workflows/manifest.yml`
5. Set in `server/.env`:

```bash
COMFYUI_WORKFLOW='{"3":{"inputs":{...}}}'  # Or use exported JSON
```

### Multi-Agent Pipelines

The agentic workflows chain multiple processing steps:

```text
pipeline-full-agentic:
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │  SDXL Base  │ ──> │   Refiner   │ ──> │  Upscale 2x │
  │  Steps 0-22 │     │ Steps 22-30 │     │  Real-ESRGAN│
  └─────────────┘     └─────────────┘     └─────────────┘
       1024x1024          1024x1024           2048x2048
```

### Security Settings

Workflows include built-in security limits defined in `manifest.yml`:

```yaml
security:
  max_steps: 100           # Prevent DoS via excessive steps
  max_width: 2048          # Max image dimensions
  max_height: 2048
  max_batch_size: 4        # Limit concurrent generations
  rate_limit_rpm: 10       # Requests per minute per user
```

### ComfyUI Custom Nodes

To add custom nodes (e.g., ControlNet, IPAdapter):

```bash
# On GPU worker
cd ${DATA_PATH}/comfyui/custom_nodes
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git

# Restart ComfyUI
docker restart comfyui-worker
```

## Configuration

### Environment Files

Each deployment has a `.env.example` file. Copy to `.env` and configure:

```bash
# Server - MUST change secrets
cp server/.env.example server/.env

# GPU Worker
cp gpu-worker/.env.example gpu-worker/.env
```

### Key Configuration

| Variable | Location | Description |
|----------|----------|-------------|
| `WEBUI_SECRET_KEY` | server/.env | **MUST CHANGE** - Session encryption |
| `WEBUI_PORT` | server/.env | Open WebUI port (default: 3001) |
| `OLLAMA_NUM_THREADS` | server/.env | CPU threads (default: 56) |
| `OLLAMA_NUM_PARALLEL` | gpu-worker/.env | Concurrent requests (default: 4) |
| `OLLAMA_MAX_LOADED_MODELS` | gpu-worker/.env | Models in VRAM (default: 2) |

### Model Configuration

Edit `config/models-manifest.yml` to customize which models to sync.

Edit `config/openwebui-defaults.json.template` for model-specific parameters:

- Temperature, top_p, context length
- System prompts per model
- Default model selection

## Directory Structure

```text
self-hosted-ai/
├── server/                     # Server stack (homelab)
│   ├── docker-compose.yml
│   ├── .env.example
│   └── monitoring/
├── gpu-worker/                 # GPU worker (akula-prime)
│   ├── docker-compose.yml      # Ollama GPU + ComfyUI
│   └── .env.example
├── config/                     # Configuration templates
│   ├── models-manifest.yml     # LLM model sync manifest
│   ├── comfyui-workflow.json   # Default image gen workflow
│   └── openwebui-defaults.json.template
├── scripts/
│   ├── bootstrap.sh            # Setup and model sync
│   ├── deploy-server.sh        # Server management
│   ├── deploy-gpu-worker.sh    # GPU worker management
│   └── release.sh              # Release automation
├── .pre-commit-config.yaml     # Pre-commit hooks
├── VERSION                     # Semantic version
└── README.md
```

## Management Commands

### Server

```bash
./scripts/deploy-server.sh deploy           # Start stack
./scripts/deploy-server.sh deploy monitoring # With Prometheus/Grafana
./scripts/deploy-server.sh stop             # Stop stack
./scripts/deploy-server.sh status           # Check status
./scripts/deploy-server.sh logs             # View logs
./scripts/deploy-server.sh pull-model <model>  # Pull model to CPU
```

### GPU Worker

```bash
./scripts/deploy-gpu-worker.sh deploy       # Start Ollama GPU
./scripts/deploy-gpu-worker.sh stop         # Stop
./scripts/deploy-gpu-worker.sh status       # GPU utilization
./scripts/deploy-gpu-worker.sh logs         # View logs
./scripts/deploy-gpu-worker.sh pull-model <model>  # Pull model
```

### Bootstrap

```bash
./scripts/bootstrap.sh setup                # Install pre-commit hooks
./scripts/bootstrap.sh sync                 # Interactive model sync
./scripts/bootstrap.sh sync --all           # Sync all missing models
./scripts/bootstrap.sh sync --all --gpu     # GPU models only
./scripts/bootstrap.sh status               # Show stack status
```

## Development

### Pre-commit Hooks

This project uses pre-commit hooks for code quality:

- **shellcheck** - Shell script linting
- **shfmt** - Shell script formatting (autofix)
- **hadolint** - Dockerfile linting
- **yamllint** - YAML validation
- **prettier** - JSON/YAML/Markdown formatting (autofix)
- **markdownlint** - Markdown linting (autofix)
- **detect-secrets** - Secret detection

Install hooks:

```bash
./scripts/bootstrap.sh setup
# or
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
```

### Git Workflow

- `main` - Stable releases only
- `dev` - Integration branch
- `feature/*` - Feature branches → PR to dev
- `fix/*` - Bug fixes → PR to dev

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Releases

```bash
# Bump version and create release
./scripts/release.sh bump patch   # 0.1.0 -> 0.1.1
./scripts/release.sh bump minor   # 0.1.1 -> 0.2.0
./scripts/release.sh bump major   # 0.2.0 -> 1.0.0

# Check current version
./scripts/release.sh status
```

## Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Open WebUI | <http://192.168.1.170:3001> | Web interface |
| Ollama CPU | <http://192.168.1.170:11434> | CPU inference API |
| Ollama GPU | <http://192.168.1.99:11434> | GPU inference API |
| ComfyUI | <http://192.168.1.99:8188> | Image generation API & UI |
| Prometheus | <http://192.168.1.170:9090> | Metrics |
| Grafana | <http://192.168.1.170:3000> | Dashboards |

## Troubleshooting

### GPU Worker Not Responding

```bash
# On GPU worker
docker logs ollama-gpu-worker
nvidia-smi  # Check GPU visibility

# Test API
curl http://192.168.1.99:11434/api/tags
```

### ComfyUI Not Working

```bash
# Check container status
docker logs comfyui-worker

# Verify API is responding
curl http://192.168.1.99:8188/system_stats

# Check if models are present
ls -la /data/comfyui/models/checkpoints/

# Firewall - allow from LAN
sudo ufw allow from 192.168.1.0/24 to any port 8188
```

### Image Generation Fails in Open WebUI

1. **Check ComfyUI connectivity:**
   ```bash
   curl http://192.168.1.99:8188/system_stats
   ```

2. **Verify checkpoint model exists:**
   ```bash
   ls /data/comfyui/models/checkpoints/
   # Should see .safetensors files
   ```

3. **Check Open WebUI config:**
   ```bash
   # In server/.env
   ENABLE_IMAGE_GENERATION=true
   IMAGE_GENERATION_ENGINE=comfyui
   COMFYUI_BASE_URL=http://192.168.1.99:8188
   ```

4. **Restart services:**
   ```bash
   ./scripts/deploy-server.sh stop && ./scripts/deploy-server.sh deploy
   ```

### Cannot Connect from Server to GPU Worker

```bash
# On server
curl http://192.168.1.99:11434/api/tags

# Check firewall on GPU worker
sudo ufw allow from 192.168.1.0/24 to any port 11434
sudo ufw allow from 192.168.1.0/24 to any port 8188  # ComfyUI
```

### Out of VRAM

```bash
# Check loaded models
curl http://192.168.1.99:11434/api/ps

# Reduce parallel requests in gpu-worker/.env
OLLAMA_NUM_PARALLEL=2
OLLAMA_MAX_LOADED_MODELS=1
```

## License

MIT License - Tyler Zervas (tzervas) <tz-dev@vectorweight.com>
