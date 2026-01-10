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
|  |  +------+-------+  +-------------+  |    +-------------|--------------+  |
|  |  |    Redis     |  | Prometheus  |  |                  | LAN             |
|  |  |   :6379      |  |   :9090     |  |                  |                 |
|  |  +--------------+  +-------------+  |<-----------------+                 |
|  |                    +-------------+  |                                    |
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
│   ├── docker-compose.yml
│   └── .env.example
├── config/                     # Configuration templates
│   ├── models-manifest.yml     # Model sync manifest
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

### Cannot Connect from Server to GPU Worker

```bash
# On server
curl http://192.168.1.99:11434/api/tags

# Check firewall on GPU worker
sudo ufw allow from 192.168.1.0/24 to any port 11434
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
