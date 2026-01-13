# Self-Hosted AI Stack - Complete Usage Guide

**Version:** 2.1.0 | **Last Updated:** January 13, 2026  
**Deployment Status:** ✅ Fully Operational with Multi-Modal Capabilities

---

## 🚀 Quick Access

### Service Dashboard

| Service | URL | Purpose | Status |
|---------|-----|---------|--------|
| **Open WebUI** | http://192.168.1.170:3001 | Main AI interface | ✅ |
| **LiteLLM API** | http://192.168.1.170:4000 | API gateway | ✅ |
| **N8N** | http://192.168.1.170:5678 | Automation | ✅ |
| **SearXNG** | http://192.168.1.170:8082 | Search | ⚠️ |
| **Ollama CPU** | http://192.168.1.170:11434 | CPU inference | ✅ |
| **Ollama GPU** | http://192.168.1.99:11435 | GPU inference | ✅ |
| **ComfyUI** | http://192.168.1.99:8188 | Image gen | ✅ |
| **Whisper ASR** | http://192.168.1.99:9000 | Audio | ✅ |
| **Grafana** | http://192.168.1.170:3000 | Monitoring | ✅ |

---

## 💬 Chat Interface (Open WebUI)

### Getting Started

1. Navigate to http://192.168.1.170:3001
2. Create an account (first signup = admin)
3. Select a model from the dropdown
4. Start chatting!

### Available Models (16 total)

**Vision Models** 🎨 (Image Understanding):
- `llava:13b` - Full multimodal vision
- `bakllava:latest` - Optimized variant

**Coding Models** 💻:
- `qwen2.5-coder:14b` - Best for Python/Web dev
- `deepseek-coder-v2:16b` - Strong reasoning
- `codellama:13b` - Multi-language support

**General Chat** 🗣️:
- `llama3.1:8b` - Fast & capable
- `phi4:latest` - Small but powerful  
- `mistral:latest` - Efficient 7B
- `gemma2:2b` - Ultra-fast responses

**Embeddings** 📊 (RAG/Search):
- `nomic-embed-text` - Text embeddings
- `mxbai-embed-large` - Multilingual

### Usage Examples

#### Basic Chat
```
User: Write a Python function to validate email addresses
Assistant: [Uses qwen2.5-coder:14b to generate code]
```

#### Image Analysis
```
User: [Upload image] What's in this photo?
Assistant: [Uses llava:13b to analyze]
```

#### Document Q&A
```
User: [Upload PDF] Summarize the key points
Assistant: [Processes via ingest service, uses RAG]
```

---

## 🔌 LiteLLM API (OpenAI Compatible)

### Base URL
```
http://192.168.1.170:4000
```

### Python Example

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.1.170:4000/v1",
    api_key="dummy"  # No auth required (change for production)
)

# Chat completion
response = client.chat.completions.create(
    model="ollama/qwen2.5-coder:14b",
    messages=[
        {"role": "system", "content": "You are an expert programmer"},
        {"role": "user", "content": "Write a FastAPI hello world app"}
    ]
)

print(response.choices[0].message.content)
```

### cURL Example

```bash
curl http://192.168.1.170:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/llama3.1:8b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### Streaming

```python
stream = client.chat.completions.create(
    model="ollama/phi4:latest",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### List Available Models

```bash
curl http://192.168.1.170:4000/v1/models
```

---

## 🎨 Image Generation (ComfyUI)

### Access
http://192.168.1.99:8188

### Quick Start

1. Open ComfyUI in browser
2. Load a workflow (File → Load)
3. Modify the prompt
4. Click "Queue Prompt"

### Workflow Library

Pre-configured workflows in `/home/kang/self-hosted-ai/config/comfyui-workflows/`:

| Workflow | Purpose | VRAM Required |
|----------|---------|---------------|
| basic-txt2img | Simple text→image | 4GB |
| sdxl-high-quality | SDXL quality | 8GB |
| img2img | Transform images | 6GB |
| upscale-2x | Enhance resolution | 4GB |

### Example: Generate Image

```bash
# Via API (requires workflow JSON)
curl -X POST http://192.168.1.99:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {
      "3": {
        "inputs": {
          "seed": 42,
          "steps": 20,
          "cfg": 8,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 1,
          "text": "A beautiful sunset over mountains, 4k, detailed"
        }
      }
    }
  }'
```

### Tips

- **Prompt quality matters**: Be descriptive!
- **Steps**: 20-30 for most cases
- **CFG Scale**: 7-9 for balanced results
- **Negative prompts**: "blurry, low quality, distorted"

---

## 🎙️ Audio Transcription (Whisper)

### Access
http://192.168.1.99:9000

### Transcribe Audio

```bash
curl -X POST http://192.168.1.99:9000/asr?task=transcribe \
  -F "audio_file=@your_recording.mp3" \
  -F "language=en"
```

### Python Example

```python
import requests

files = {'audio_file': open('meeting.wav', 'rb')}
params = {'task': 'transcribe', 'language': 'en'}

response = requests.post(
    'http://192.168.1.99:9000/asr',
    files=files,
    params=params
)

print(response.json()['text'])
```

### Supported Formats
- MP3, WAV, M4A, FLAC, OGG
- Max size: 25MB

### Current Model
- **Model**: `base` (low VRAM usage ~2GB)
- **Accuracy**: Good for most use cases
- **Speed**: Fast on GPU

---

## 🔄 Workflow Automation (N8N)

### Access
http://192.168.1.170:5678

### Default Credentials
- **Username**: admin
- **Password**: admin (⚠️ Change this!)

### Example Workflows

#### 1. Document Processing Pipeline
```
Webhook → Download File → Ollama Summarize → Store in Qdrant
```

#### 2. Scheduled Image Generation
```
Cron → ComfyUI Generate → Upload to Storage → Notify
```

#### 3. Audio Transcription Flow
```
File Upload → Whisper ASR → Ollama Analyze → Save Results
```

### Connecting to Services

Use internal Docker network names:
- Ollama: `http://ollama-cpu-server:11434`
- ComfyUI: `http://192.168.1.99:8188`
- Whisper: `http://192.168.1.99:9000`
- Qdrant: `http://qdrant-vector-db:6333`

---

## 🔍 Private Search (SearXNG)

### Access
http://192.168.1.170:8082

### Features
- No tracking
- Aggregates multiple search engines
- Can be integrated into chat responses

### Search Shortcuts
- `!gh python asyncio` - GitHub
- `!so javascript promise` - Stack Overflow
- `!wp machine learning` - Wikipedia
- `!hf llama` - HuggingFace

### API Search

```python
import httpx

response = httpx.get(
    "http://192.168.1.170:8082/search",
    params={
        "q": "latest AI models 2026",
        "format": "json"
    }
)

results = response.json()
for result in results['results']:
    print(f"{result['title']}: {result['url']}")
```

---

## 📊 Monitoring (Grafana)

### Access
http://192.168.1.170:3000

### Default Credentials
- **Username**: admin
- **Password**: admin

### Available Dashboards
- **System Overview**: CPU, RAM, disk usage
- **GPU Metrics**: VRAM, utilization, temperature
- **Service Health**: All containers status
- **API Metrics**: Request rates, latency

### Quick Health Check

```bash
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check specific service logs
docker logs -f open-webui-server
docker logs -f litellm-proxy
docker logs -f n8n-server
```

---

## 🛠️ Model Management

### List Models

```bash
# CPU models
curl http://192.168.1.170:11434/api/tags | jq '.models[].name'

# GPU models
curl http://192.168.1.99:11435/api/tags | jq '.models[].name'
```

### Pull New Models

```bash
# On CPU server
docker exec ollama-cpu-server ollama pull mistral:7b

# On GPU worker
docker exec ollama-gpu-worker ollama pull llama3.1:70b
```

### Remove Models

```bash
docker exec ollama-cpu-server ollama rm mistral:7b
```

### Sync Models Between Nodes

```bash
# Use the sync script
/home/kang/self-hosted-ai/scripts/sync-models-from-akula.sh
```

### Model Storage Locations

| Node | Path |
|------|------|
| CPU Server | `/data/ollama-cpu/models/` |
| GPU Worker | `/data/ollama-gpu/models/` |

---

## 🎯 Common Use Cases

### 1. Code Assistant

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.1.170:4000/v1",
    api_key="dummy"
)

response = client.chat.completions.create(
    model="ollama/qwen2.5-coder:14b",
    messages=[
        {"role": "system", "content": "You are a senior Python developer"},
        {"role": "user", "content": "Write a async function to fetch URLs in parallel"}
    ]
)

print(response.choices[0].message.content)
```

### 2. Image Analysis

```bash
# Encode image
IMAGE_B64=$(base64 -w 0 photo.jpg)

# Analyze with vision model
curl http://192.168.1.99:11435/api/generate \
  -d "{
    \"model\": \"llava:13b\",
    \"prompt\": \"Describe this image in detail\",
    \"images\": [\"$IMAGE_B64\"],
    \"stream\": false
  }"
```

### 3. Document Summarization

1. Upload document to ingest service:
```bash
curl -X POST http://192.168.1.170:8200/upload \
  -F "file=@report.pdf"
```

2. Wait for processing (~5-10 seconds)

3. Query via chat or API:
```python
response = client.chat.completions.create(
    model="ollama/llama3.1:8b",
    messages=[{"role": "user", "content": "Summarize the uploaded report"}]
)
```

### 4. Batch Image Generation

```python
import requests
import json

workflow = json.load(open('workflow.json'))

for i, prompt in enumerate(prompts):
    workflow['3']['inputs']['text'] = prompt
    workflow['3']['inputs']['seed'] = i
    
    requests.post(
        'http://192.168.1.99:8188/prompt',
        json={'prompt': workflow}
    )
    print(f"Queued: {prompt[:50]}...")
```

---

## 🔐 Security Recommendations

### 1. Change Default Passwords

```bash
# N8N
docker exec -it n8n-server n8n user-management:reset --email=admin

# Grafana
docker exec -it grafana grafana-cli admin reset-admin-password newpassword
```

### 2. Enable LiteLLM Authentication

Edit `/home/kang/self-hosted-ai/config/litellm-config.yml`:
```yaml
general_settings:
  master_key: "your-secure-random-key-here"
```

Then use in requests:
```bash
curl http://192.168.1.170:4000/v1/chat/completions \
  -H "Authorization: Bearer your-secure-random-key-here" \
  -H "Content-Type: application/json" \
  -d '{"model": "ollama/llama3.1:8b", "messages": [...]}'
```

### 3. Setup Traefik TLS (Optional)

```bash
# Generate certificates
/home/kang/self-hosted-ai/scripts/setup-traefik-tls.sh generate

# Then access via HTTPS:
# https://ai.yourdomain.com
# https://api.yourdomain.com
```

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs <service-name>

# Check resources
docker stats

# Restart service
docker restart <service-name>
```

### Out of Memory

```bash
# Check system memory
free -h

# Check container limits
docker stats

# Solution: Use smaller models or increase swap
```

### Slow Inference

- **Check GPU**: `curl http://192.168.1.99:8100/gpu/stats`
- **Use smaller models**: phi4 instead of llama3.1:70b
- **Reduce context length**: Set max_tokens lower

### ComfyUI Out of VRAM

Edit `gpu-worker/docker-compose.yml`:
```yaml
comfyui-gpu:
  environment:
    - CLI_ARGS=--lowvram  # For <8GB VRAM
```

### Ingest Service Not Watching Files

```bash
# Check inotify limits
cat /proc/sys/fs/inotify/max_user_watches

# Increase if needed
sudo /home/kang/self-hosted-ai/scripts/configure-host-system.sh
```

### SearXNG Restarting

Known issue with Python 3.14 threading. Service is functional but may restart periodically. Workaround being investigated.

---

## 🔄 Maintenance

### Update Services

```bash
# Pull latest images
docker compose --profile full pull

# Restart with new images
docker compose --profile full up -d

# Check GPU worker
cd gpu-worker && docker compose --profile full pull && docker compose --profile full up -d
```

### Backup Data

```bash
# Run backup script
/home/kang/self-hosted-ai/scripts/backup-components.sh

# Backups saved to: /data/backups/
```

### Clean Up

```bash
# Remove unused images/containers
docker system prune -a

# Check disk space
df -h /data
```

### Database Maintenance

```bash
# PostgreSQL vacuum
docker exec postgres-server psql -U litellm -d litellm -c "VACUUM ANALYZE;"

# Check database size
docker exec postgres-server psql -U postgres -c "\l+"
```

---

## 📚 Advanced Topics

### Custom RAG Pipeline

```python
from qdrant_client import QdrantClient
import ollama

# Initialize
qdrant = QdrantClient(url="http://192.168.1.170:6333")
ollama_client = ollama.Client(host="http://192.168.1.170:11434")

# Embed query
query = "How does async/await work?"
embedding = ollama_client.embeddings(
    model="nomic-embed-text",
    prompt=query
)

# Search vectors
results = qdrant.search(
    collection_name="documents",
    query_vector=embedding['embedding'],
    limit=5
)

# Generate with context
context = "\n".join([r.payload['text'] for r in results])
response = ollama_client.generate(
    model="qwen2.5-coder:14b",
    prompt=f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
)

print(response['response'])
```

### Distributed Inference

Route large models to GPU worker via LiteLLM config:
```yaml
model_list:
  - model_name: llama-gpu
    litellm_params:
      model: ollama/llama3.1:70b
      api_base: http://192.168.1.99:11435
```

### ComfyUI Custom Nodes

```bash
# SSH into GPU worker
ssh akula-prime

# Navigate to custom nodes
cd /data/comfyui/custom_nodes

# Clone node repository
git clone https://github.com/author/custom-node

# Restart ComfyUI
docker restart comfyui-gpu
```

---

## 📞 Support & Resources

### Documentation
- [Quick Start](QUICKSTART.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Gap Remediation](GAP_REMEDIATION_GUIDE.md)

### Health Endpoints

| Service | Endpoint |
|---------|----------|
| LiteLLM | http://192.168.1.170:4000/health |
| Open WebUI | http://192.168.1.170:3001/health |
| Ollama CPU | http://192.168.1.170:11434/api/tags |
| Ollama GPU | http://192.168.1.99:11435/api/tags |
| Qdrant | http://192.168.1.170:6333/health |

### Logs

```bash
# View all service logs
docker compose logs -f

# Specific service
docker logs -f open-webui-server

# Last 100 lines
docker logs --tail 100 litellm-proxy
```

---

## 🎓 Quick Recipes

### Recipe 1: Chat with Code Review

```bash
curl http://192.168.1.170:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen2.5-coder:14b",
    "messages": [
      {"role": "system", "content": "You are a code reviewer. Be thorough and constructive."},
      {"role": "user", "content": "Review this code:\n\n```python\ndef process(data):\n    return [x*2 for x in data]\n```"}
    ]
  }'
```

### Recipe 2: Generate & Analyze Image

```bash
# 1. Generate image via ComfyUI
curl -X POST http://192.168.1.99:8188/prompt -d @workflow.json

# 2. Wait for completion
sleep 30

# 3. Analyze with vision model
IMAGE_B64=$(base64 -w 0 /data/comfyui/output/image.png)
curl http://192.168.1.99:11435/api/generate \
  -d "{\"model\": \"llava:13b\", \"prompt\": \"Describe this\", \"images\": [\"$IMAGE_B64\"]}"
```

### Recipe 3: Transcribe → Summarize

```python
import requests

# Transcribe
files = {'audio_file': open('meeting.mp3', 'rb')}
transcription = requests.post(
    'http://192.168.1.99:9000/asr',
    files=files
).json()['text']

# Summarize
from openai import OpenAI
client = OpenAI(base_url="http://192.168.1.170:4000/v1", api_key="dummy")

summary = client.chat.completions.create(
    model="ollama/llama3.1:8b",
    messages=[
        {"role": "system", "content": "Summarize meeting transcripts concisely"},
        {"role": "user", "content": transcription}
    ]
).choices[0].message.content

print(summary)
```

---

**Current Stack Status**: ✅ All core services operational  
**Model Count**: 16 models across CPU and GPU nodes  
**Multi-Modal**: Text, Image, Audio capabilities active  
**Last Updated**: January 13, 2026

