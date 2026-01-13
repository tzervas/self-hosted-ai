# Multi-Modal AI Platform - Gap Remediation Deployment Guide

This guide walks through deploying the updated platform with all gap fixes implemented.

## Prerequisites

- Docker and Docker Compose installed on both server and GPU worker nodes
- NVIDIA drivers and nvidia-container-toolkit on GPU worker
- Network connectivity between nodes (192.168.1.170 ↔ 192.168.1.99)

## 1. Configure Host Systems

Run on **both** server and GPU worker nodes:

```bash
# Configure system settings (inotify, vm, network)
sudo ./scripts/configure-host-system.sh

# Logout and back in for ulimit changes, then restart Docker
sudo systemctl restart docker
```

## 2. Deploy GPU Worker Services

On the GPU worker node (192.168.1.99):

```bash
cd /home/kang/self-hosted-ai/gpu-worker

# Create required directories
sudo mkdir -p /data/comfyui/{models,output,input,custom_nodes,workflows}
sudo mkdir -p /data/whisper

# Start core services (Ollama + GPU Manager)
docker compose up -d ollama-gpu gpu-manager

# Start image generation (ComfyUI)
docker compose --profile image-gen up -d

# Start audio transcription (Whisper)
docker compose --profile audio up -d

# Or start all at once:
docker compose --profile full up -d
```

### Download ComfyUI Models

```bash
# Setup SDXL text-to-image workflow
./scripts/comfyui-setup.sh setup txt2img-sdxl

# List available workflows
./scripts/comfyui-setup.sh list

# Validate setup
./scripts/comfyui-setup.sh validate
```

## 3. Deploy Server Services

On the server node (192.168.1.170):

```bash
cd /home/kang/self-hosted-ai/server

# Create required directories
sudo mkdir -p /data/{n8n,postgres,traefik/{certs,config},searxng-redis}
sudo chown -R 1000:1000 /data/n8n

# Start basic services
docker compose --profile basic up -d

# Start full stack (includes N8N, LiteLLM, Ingest)
docker compose --profile full up -d
```

## 4. Setup TLS (Optional but Recommended)

```bash
# Generate self-signed certificates
export DOMAIN=yourdomain.local
./scripts/setup-traefik-tls.sh generate

# Start Traefik reverse proxy
docker compose --profile secure up -d traefik
```

## 5. Verify Deployment

### Check Service Health

```bash
# Server services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# GPU worker services (run on GPU worker)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Test Endpoints

| Service | URL | Expected |
|---------|-----|----------|
| Open WebUI | http://192.168.1.170:3000 | Login page |
| LiteLLM API | http://192.168.1.170:4000/health | `{"status":"ok"}` |
| SearXNG | http://192.168.1.170:8082 | Search page |
| N8N | http://192.168.1.170:5678 | Login page |
| ComfyUI | http://192.168.1.99:8188 | ComfyUI interface |
| Whisper | http://192.168.1.99:9000/health | Health response |

## 6. Configure Integrations

### Open WebUI → ComfyUI

1. Login to Open WebUI
2. Go to Settings → Images
3. Set ComfyUI URL: `http://192.168.1.99:8188`
4. Test connection

### N8N → Ollama

1. Login to N8N (admin / password from .env)
2. Create new workflow
3. Add Ollama node
4. Configure URL: `http://ollama-cpu:11434` or `http://192.168.1.99:11434`

### LiteLLM API Usage

```bash
# Test LiteLLM
curl http://192.168.1.170:4000/v1/models

# Generate completion
curl http://192.168.1.170:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:14b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Docker Compose Profiles Reference

### Server (docker-compose.yml)

| Profile | Services |
|---------|----------|
| `basic` | open-webui, ollama-cpu, redis, searxng |
| `full` | basic + n8n, litellm, postgres, ingest-service |
| `monitoring` | basic + prometheus, grafana, node-exporter |
| `secure` | traefik (adds TLS) |
| `api-gateway` | litellm, postgres |
| `search` | searxng, searxng-redis |
| `automation` | n8n |

### GPU Worker (gpu-worker/docker-compose.yml)

| Profile | Services |
|---------|----------|
| (default) | ollama-gpu, gpu-manager |
| `image-gen` | comfyui |
| `audio` | whisper |
| `full` | all services |

## Troubleshooting

### ComfyUI Not Starting

```bash
# Check GPU availability
nvidia-smi

# Check container logs
docker logs comfyui-worker

# Verify model directory
ls -la /data/comfyui/models/checkpoints/
```

### SearXNG Restarting

```bash
# Ensure searxng-redis is running
docker ps | grep searxng-redis

# Check SearXNG logs
docker logs searxng-server
```

### Ingest Service inotify Errors

```bash
# Check current limit
cat /proc/sys/fs/inotify/max_user_watches

# Should be 524288 after running configure-host-system.sh
# If not, reboot or run:
sudo sysctl -w fs.inotify.max_user_watches=524288
```

### LiteLLM Database Errors

```bash
# Check postgres is healthy
docker exec -it postgres-server pg_isready

# Check DATABASE_URL encoding (special chars need URL encoding)
# @ → %40, # → %23, etc.
```

## Video Generation (Off-Peak)

Video generation requires 16GB+ VRAM and is configured as an optional off-peak service through ComfyUI:

```bash
# Download SVD models
./scripts/comfyui-setup.sh setup text2video-svd

# Use text2video-svd.json workflow in ComfyUI
```

## Next Steps

1. **Security Hardening**: Generate strong passwords, enable HTTPS
2. **Monitoring Dashboards**: Configure Grafana with provided rules
3. **Backups**: Set up automated backups for `/data` directory
4. **Model Updates**: Use `./scripts/sync-models.sh` for model management
