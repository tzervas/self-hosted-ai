# Quick Start: Production Multi-Modal AI Stack

Complete deployment guide for the full-featured AI research and development environment.

## Prerequisites

- Docker & Docker Compose v2+
- NVIDIA GPU with nvidia-container-toolkit (GPU worker)
- 16GB+ VRAM recommended for full multi-modal capabilities
- 50GB+ free disk space for models
- Network connectivity between server and GPU worker

## Step 1: Clone and Configure

```bash
# Clone repository
git clone https://github.com/tzervas/self-hosted-ai.git
cd self-hosted-ai
git checkout dev

# Server configuration
cd server
cp .env.multimodal.example .env

# Edit .env - MUST CHANGE these:
# - WEBUI_SECRET_KEY (generate with: openssl rand -hex 32)
# - LITELLM_MASTER_KEY (generate with: openssl rand -hex 32)
# - POSTGRES_PASSWORD (generate with: openssl rand -base64 32)
# - N8N_PASSWORD
# - DATA_PATH (default: /data)
# - GPU_WORKER_HOST (default: 192.168.1.99)
```

## Step 2: Deploy Server Stack

### Option A: Basic Stack (Minimal)
```bash
cd server
docker compose up -d
```

Services: Open WebUI, Ollama CPU, Redis

### Option B: Full Multi-Modal Stack (Recommended)
```bash
cd server
docker compose -f docker-compose.yml -f docker-compose.multimodal.yml \
  --profile full up -d
```

Services: All basic + audio, video, embeddings, API gateway, orchestration, monitoring

### Option C: Custom Profile
```bash
# Basic + Audio + Embeddings
docker compose -f docker-compose.yml -f docker-compose.multimodal.yml \
  --profile basic --profile audio --profile embeddings up -d
```

Available profiles:
- `basic`: Core services (included by default)
- `audio`: Whisper STT, Coqui TTS, Piper TTS
- `embeddings`: Qdrant vector database
- `video`: FFmpeg processing
- `api-gateway`: LiteLLM proxy, PostgreSQL
- `orchestration`: n8n workflows
- `monitoring`: Loki, Promtail, enhanced metrics
- `full`: All of the above

## Step 3: Deploy GPU Worker

SSH to GPU worker machine (192.168.1.99):

```bash
# On GPU worker
cd self-hosted-ai
git checkout dev
git pull origin dev

cd gpu-worker
cp .env.example .env
# Edit .env if needed (DATA_PATH, ports)

docker compose up -d
```

Services: Ollama GPU, ComfyUI

## Step 4: Initialize Models

On **server** (192.168.1.170):
```bash
./scripts/bootstrap.sh pull-models
```

This downloads all required models from the manifest:
- **GPU models** (~60GB): Coding, reasoning, vision, function calling
- **CPU models** (~25GB): Embeddings, chat, specialized tasks

Or pull models selectively:
```bash
# GPU models (on GPU worker)
ssh 192.168.1.99
docker exec ollama-gpu-worker ollama pull qwen2.5-coder:14b
docker exec ollama-gpu-worker ollama pull llava:13b
docker exec ollama-gpu-worker ollama pull mistral:7b-instruct-v0.3

# CPU models (on server)
docker exec ollama-cpu-server ollama pull nomic-embed-text:latest
docker exec ollama-cpu-server ollama pull mxbai-embed-large:latest
docker exec ollama-cpu-server ollama pull phi3:latest
```

## Step 5: Initialize ComfyUI (GPU Worker)

On GPU worker:
```bash
./scripts/comfyui-setup.sh init      # Copy workflow files
./scripts/comfyui-setup.sh models    # Download SDXL models
./scripts/comfyui-setup.sh status    # Verify setup
```

## Step 6: Verify Deployment

```bash
# Check all services
./scripts/deploy-server.sh status
./scripts/deploy-gpu-worker.sh status

# Test endpoints
curl http://192.168.1.170:11434/api/tags      # Ollama CPU
curl http://192.168.1.99:11434/api/tags       # Ollama GPU
curl http://192.168.1.99:8188/system_stats    # ComfyUI
curl http://192.168.1.170:9000/health         # Whisper (if enabled)
curl http://192.168.1.170:6333/collections    # Qdrant (if enabled)
```

## Step 7: Access Services

Open in browser:
- **Open WebUI**: http://192.168.1.170:3001
- **ComfyUI**: http://192.168.1.99:8188
- **n8n** (if enabled): http://192.168.1.170:5678
- **Prometheus** (if monitoring): http://192.168.1.170:9090
- **Grafana** (if monitoring): http://192.168.1.170:3002

## Step 8: Configure Open WebUI

1. Create admin account at http://192.168.1.170:3001
2. Import model presets from `config/openwebui-production.json`
3. Enable functions and pipelines
4. Test image generation with ComfyUI
5. Test voice transcription (if audio services enabled)

## Usage Examples

### Text Generation (Coding)
```bash
curl -X POST http://192.168.1.99:11434/api/generate -d '{
  "model": "qwen2.5-coder:14b",
  "prompt": "Write a Python function to calculate fibonacci numbers",
  "stream": false
}'
```

### Image Generation
```bash
# Via Open WebUI: Use "Generate Image" command
# Or direct ComfyUI API:
curl -X POST http://192.168.1.99:8188/api/prompt -d '{
  "prompt": "a beautiful sunset over mountains"
}'
```

### Audio Transcription (if enabled)
```bash
curl -X POST http://192.168.1.170:9000/asr \
  -F "audio_file=@recording.mp3" \
  -F "task=transcribe" \
  -F "language=en"
```

### Embeddings & Search (if enabled)
```bash
# Generate embedding
curl -X POST http://192.168.1.170:11434/api/embeddings -d '{
  "model": "nomic-embed-text:latest",
  "prompt": "machine learning best practices"
}'

# Semantic search in Qdrant
curl -X POST http://192.168.1.170:6333/collections/docs/points/search -d '{
  "vector": [...],
  "limit": 5
}'
```

### Multi-Agent Workflow
```bash
cd workflows
python -m agents.cli execute multimodal_content_processing.yaml \
  --var content_paths.image=/data/input/image.jpg \
  --var modalities=image,text
```

## Performance Tuning

### GPU Memory Optimization
Edit `gpu-worker/.env`:
```bash
OLLAMA_NUM_PARALLEL=2              # Concurrent requests (2-4)
OLLAMA_MAX_LOADED_MODELS=2         # Models in VRAM (1-3)
OLLAMA_GPU_LAYERS=99               # Full GPU offload
```

### CPU Worker Optimization  
Edit `server/.env`:
```bash
OLLAMA_NUM_THREADS=56              # CPU threads
OLLAMA_CPU_NUM_PARALLEL=8          # Concurrent requests
OLLAMA_CPU_MAX_LOADED_MODELS=4     # Models in RAM
```

### Resource Allocation
```bash
# Limit per-service memory
docker compose --profile full up -d \
  --scale whisper=1 \
  --scale coqui-tts=0  # Disable if not needed
```

## Monitoring

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f open-webui
docker compose logs -f ollama-cpu

# GPU worker
docker compose -f gpu-worker/docker-compose.yml logs -f ollama-gpu
```

### Check Resource Usage
```bash
# GPU utilization
nvidia-smi

# Container stats
docker stats

# Disk usage
du -sh /data/*
```

### Prometheus Metrics (if enabled)
- **Prometheus**: http://192.168.1.170:9090
- **Grafana**: http://192.168.1.170:3002

Pre-configured dashboards for:
- Model inference performance
- Request rates and latency
- Resource utilization
- Error rates

## Troubleshooting

### Services Not Starting
```bash
# Check logs
docker compose logs service_name

# Restart service
docker compose restart service_name

# Rebuild if needed
docker compose up -d --force-recreate service_name
```

### Out of Memory
```bash
# Check memory usage
free -h
docker stats

# Solutions:
# 1. Reduce OLLAMA_MAX_LOADED_MODELS
# 2. Use smaller model variants
# 3. Reduce OLLAMA_NUM_PARALLEL
# 4. Restart services to clear memory
docker compose restart
```

### Slow Inference
```bash
# Check GPU usage
nvidia-smi

# Verify GPU acceleration
docker logs ollama-gpu-worker | grep -i cuda

# Solutions:
# 1. Ensure nvidia-container-toolkit installed
# 2. Check GPU driver version
# 3. Reduce concurrent requests
# 4. Use quantized models (q4_0, q8_0)
```

### Network Issues
```bash
# Test connectivity
ping 192.168.1.99
curl http://192.168.1.99:11434/api/version

# Check firewall
sudo ufw status
sudo firewall-cmd --list-all

# Verify Docker network
docker network inspect server_default
```

## Backup & Maintenance

### Backup Data
```bash
# Backup all data
sudo tar -czf backup-$(date +%Y%m%d).tar.gz /data

# Backup specific components
sudo tar -czf ollama-models.tar.gz /data/ollama-cpu /data/ollama-gpu
sudo tar -czf webui-data.tar.gz /data/open-webui
sudo tar -czf vector-db.tar.gz /data/qdrant
```

### Update Services
```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d --force-recreate

# GPU worker
cd gpu-worker
docker compose pull
docker compose up -d --force-recreate
```

### Clean Up
```bash
# Remove unused Docker resources
docker system prune -a

# Remove old models
docker exec ollama-cpu-server ollama rm model_name
docker exec ollama-gpu-worker ollama rm model_name
```

## Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate secure keys for WEBUI_SECRET_KEY, LITELLM_MASTER_KEY
- [ ] Set CORS_ALLOW_ORIGIN appropriately (not *)
- [ ] Enable HTTPS with reverse proxy
- [ ] Configure firewall rules
- [ ] Enable authentication on all services
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup encryption keys securely

## Next Steps

1. **Configure Model Presets** in Open WebUI
2. **Create Custom Workflows** for your use cases
3. **Set Up Monitoring** dashboards in Grafana
4. **Build RAG Pipeline** with vector database
5. **Explore Multi-Modal** capabilities
6. **Develop Custom Agents** for specialized tasks

## Support

- **Documentation**: [PRODUCTION_FEATURES.md](PRODUCTION_FEATURES.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Issues**: https://github.com/tzervas/self-hosted-ai/issues

## License

MIT License - See [LICENSE](LICENSE) for details.
