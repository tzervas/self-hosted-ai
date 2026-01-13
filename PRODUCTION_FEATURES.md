# Production Multi-Modal AI Capabilities

This document describes the comprehensive multi-modal AI setup including text, image, video, audio, embeddings, and hybrid workflows.

## Overview

The production stack provides:
- **Text Generation**: Multiple specialized models for coding, reasoning, chat, function calling
- **Image Generation**: ComfyUI with SDXL and custom workflows
- **Video Generation**: Stable Video Diffusion for text-to-video
- **Audio Processing**: Speech-to-Text (Whisper), Text-to-Speech (Coqui TTS)
- **Embeddings & RAG**: Vector database (Qdrant) with semantic search
- **Multi-Modal Analysis**: Combined processing of text, images, audio, video
- **Workflow Orchestration**: Multi-agent pipelines for complex tasks

## Model Coverage

### Text Models (Ollama)

**GPU Worker Models** (RTX 5080 16GB):
- `qwen2.5-coder:14b` - Primary coding model (Rust, Python, Shell, multi-language)
- `deepseek-coder-v2:16b` - Advanced coding with architecture design
- `codellama:13b` - Code completion and explanation
- `phi4:latest` - Reasoning, mathematics, analysis
- `llama3.1:8b` - Instruction following, general reasoning
- `llava:13b` - Vision language model (image understanding, OCR, visual reasoning)
- `bakllava:latest` - Advanced image analysis
- `mistral:7b-instruct-v0.3` - Function calling, tool use, JSON mode
- `llama3.1:70b-instruct-q4_0` - Large context function calling (optional)

**CPU Server Models** (120GB RAM):
- `mistral:7b` - Fast general chat and fallback
- `phi3:latest` - Lightweight for simple tasks
- `gemma2:2b` - Ultra-fast model for testing
- `nomic-embed-text:latest` - Primary embeddings (semantic search, RAG)
- `mxbai-embed-large:latest` - High-quality embeddings
- `nomic-embed-text:137m-v1.5-q8_0` - Fast code embeddings
- `sqlcoder:15b` - SQL generation and database queries
- `llama3.1:8b-instruct-q8_0` - Document analysis
- `deepseek-math:7b` - Mathematical reasoning
- `qwen2.5:7b` - Long context processing (128k tokens)

## Multi-Modal Services

### Audio Services

**Whisper** (Speech-to-Text):
- Port: 9000
- Models: tiny, base, small, medium, large
- GPU-accelerated transcription
- Multi-language support

**Coqui TTS** (Text-to-Speech):
- Port: 5002
- Voice cloning capabilities
- Multiple languages and voices
- GPU-accelerated synthesis

**Piper TTS** (Lightweight TTS):
- Port: 5000
- Fast, efficient synthesis
- Multiple voice models

### Vector Database & Embeddings

**Qdrant** (Vector Database):
- Port: 6333 (HTTP), 6334 (gRPC)
- High-performance similarity search
- Collections for different content types
- Integrates with embedding models

### Document Processing

**Apache Tika**:
- Port: 9998
- Extract text from PDFs, Word docs, etc.
- Metadata extraction
- Content analysis

### Video Processing

**FFmpeg Service**:
- Video encoding/decoding
- Frame extraction
- Format conversion
- Effects and transitions

### API Gateway

**LiteLLM Proxy**:
- Port: 4000
- Unified API for all models
- Load balancing
- Rate limiting and caching
- Usage tracking

### Workflow Orchestration

**n8n**:
- Port: 5678
- Visual workflow builder
- API integrations
- Scheduled tasks
- Webhook support

## Model Presets (Open WebUI)

Pre-configured model presets for common tasks:

1. **Coding Expert** (`qwen2.5-coder:14b`)
   - Clean, efficient code generation
   - Multiple languages, error handling
   - Best practices and documentation

2. **Research Analyst** (`llama3.1:8b`)
   - Deep research with citations
   - Multiple perspectives
   - Evidence-based conclusions

3. **Vision Analyzer** (`llava:13b`)
   - Detailed image descriptions
   - OCR and text extraction
   - Visual reasoning

4. **Function Caller** (`mistral:7b-instruct-v0.3`)
   - Tool use and API calls
   - JSON mode for structured output
   - External system integration

5. **Embedding Expert** (`nomic-embed-text:latest`)
   - Semantic search
   - Vector similarity
   - RAG operations

6. **SQL Master** (`sqlcoder:15b`)
   - Database queries
   - Query optimization
   - Index suggestions

7. **Math Solver** (`deepseek-math:7b`)
   - Step-by-step solutions
   - Multiple problem types
   - Clear explanations

8. **Document Analyzer** (`qwen2.5:7b`)
   - Long document processing (128k tokens)
   - Information extraction
   - Comprehensive summaries

9. **Quick Chat** (`phi3:latest`)
   - Fast responses
   - Simple queries
   - Efficient inference

10. **Creative Writer** (`llama3.1:8b`)
    - Engaging narratives
    - Multiple genres
    - Vivid descriptions

## Built-In Functions

Open WebUI functions for multi-modal operations:

- **generate_embeddings**: Create vector embeddings for text
- **transcribe_audio**: Convert audio to text (Whisper)
- **generate_speech**: Text-to-speech conversion
- **analyze_image**: Vision model image analysis
- **semantic_search**: Search vector database for similar content
- **execute_sql**: Run database queries
- **generate_image**: ComfyUI image generation

## Pipelines

Pre-configured multi-step workflows:

### RAG Pipeline
1. Generate embeddings for query
2. Search vector database for relevant context
3. Generate response with retrieved context
4. Return answer with citations

### Multi-Modal Analysis
1. Analyze image (if provided)
2. Transcribe audio (if provided)
3. Combine with text input
4. Comprehensive multi-modal analysis

### Code Review Pipeline
1. Initial code review (correctness, best practices)
2. Security review
3. Synthesize reviews
4. Final recommendations

## Advanced Workflows

### Multi-Modal Content Processing
- Ingest text, images, audio, video
- Generate embeddings and store in vector DB
- Analyze across all modalities
- Produce structured documentation

**Variables**:
- content_paths (dict)
- modalities (list)
- collection_name (string)
- output_format (markdown/json/html)

### Video Production Pipeline
- Generate script from topic
- Design visual elements
- Generate voiceover (TTS)
- Create sound effects
- Render visuals (ComfyUI)
- Assemble final video (FFmpeg)

**Variables**:
- video_topic (string)
- target_duration (seconds)
- video_style (documentary/explainer/tutorial)
- visual_style (realistic/animated/artistic)
- voice_style (professional/casual/energetic)
- output_resolution (720p/1080p/4K)

## Deployment

### Basic Stack
```bash
cd server
docker compose up -d
```

### With Multi-Modal Services
```bash
cd server
docker compose -f docker-compose.yml -f docker-compose.multimodal.yml --profile multimodal up -d
```

### Profiles Available
- `basic`: Core services (Open WebUI, Ollama, Redis)
- `audio`: + Audio services (Whisper, TTS)
- `embeddings`: + Vector database (Qdrant)
- `video`: + Video processing (FFmpeg)
- `full`: All services
- `api-gateway`: + LiteLLM proxy
- `orchestration`: + n8n workflows
- `monitoring`: + Prometheus, Grafana, Loki

### Environment Configuration

Copy and configure:
```bash
cp server/.env.multimodal.example server/.env
# Edit .env with your settings
```

Key variables:
- `ENABLE_MULTIMODAL=true`
- `ENABLE_VIDEO_GENERATION=true`
- `ENABLE_AUDIO_GENERATION=true`
- `ENABLE_EMBEDDINGS=true`
- `ENABLE_FUNCTION_CALLING=true`

## Usage Examples

### Image Analysis
```python
from agents import MultiModalAgent, AgentConfig

config = AgentConfig(model="llava:13b", temperature=0.3)
agent = MultiModalAgent(config)

result = await agent.execute(
    "Analyze this product image",
    image_path="/path/to/image.jpg"
)
print(result.output)
```

### Audio Transcription
```python
result = await agent.execute(
    "Transcribe and summarize",
    audio_path="/path/to/audio.mp3",
    modalities=["audio"]
)
```

### Semantic Search
```python
from agents import EmbeddingAgent

agent = EmbeddingAgent(config, embedding_model="mxbai-embed-large:latest")

result = await agent.execute(
    "machine learning best practices",
    operation="search",
    collection="knowledge_base",
    top_k=10
)
```

### Multi-Modal Pipeline
```bash
# Execute workflow
cd workflows
python -m agents.cli execute multimodal_content_processing.yaml \
  --var content_paths.image=/data/input/image.jpg \
  --var content_paths.audio=/data/input/audio.mp3 \
  --var modalities=image,audio,text \
  --var output_format=markdown
```

## Performance

### Model Loading Times
- **Small models** (2-7B): 2-5 seconds
- **Medium models** (8-14B): 5-10 seconds
- **Large models** (70B): 20-30 seconds

### Inference Speed (RTX 5080)
- **Code generation** (14B): ~40 tokens/sec
- **Vision analysis** (13B): ~3-5 sec per image
- **Embeddings**: ~100 texts/sec

### Concurrent Requests
- **GPU worker**: 2-4 parallel requests
- **CPU server**: 8-16 parallel requests (embedding/small models)

## Model Downloads

Total storage requirements:
- **Required GPU models**: ~60GB
- **Required CPU models**: ~25GB
- **Optional models**: ~50GB
- **ComfyUI models**: ~10-30GB (SDXL, SVD, etc.)

Automatic download:
```bash
./scripts/bootstrap.sh pull-models
```

## API Endpoints

### Ollama
- CPU: `http://192.168.1.170:11434`
- GPU: `http://192.168.1.99:11434`

### Services
- Open WebUI: `http://192.168.1.170:3001`
- ComfyUI: `http://192.168.1.99:8188`
- Whisper: `http://192.168.1.170:9000`
- Coqui TTS: `http://192.168.1.170:5002`
- Qdrant: `http://192.168.1.170:6333`
- LiteLLM: `http://192.168.1.170:4000`
- n8n: `http://192.168.1.170:5678`

## Security Considerations

- Change all default passwords in `.env`
- Generate secure secret keys: `openssl rand -hex 32`
- Set `CORS_ALLOW_ORIGIN` appropriately in production
- Use HTTPS with reverse proxy (nginx/Caddy)
- Enable authentication on all services
- Configure firewall rules
- Regular security updates

## Monitoring

### Prometheus Metrics
- Model inference times
- Request rates and errors
- Resource utilization
- Queue depths

### Grafana Dashboards
- Real-time inference monitoring
- Model performance comparisons
- Resource utilization trends
- Cost tracking

### Loki Logs
- Aggregated logs from all services
- Error tracking
- Audit trails
- Performance analysis

## Troubleshooting

### Service Not Responding
```bash
docker compose ps
docker compose logs service_name
```

### Out of Memory
- Reduce `OLLAMA_MAX_LOADED_MODELS`
- Adjust `OLLAMA_NUM_PARALLEL`
- Use smaller model variants

### Slow Inference
- Check GPU utilization: `nvidia-smi`
- Verify model is using GPU: check logs
- Reduce concurrent requests
- Use faster model variants

### Audio/Video Issues
- Verify FFmpeg installation
- Check codec support
- Ensure sufficient disk space
- Verify file permissions

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to submit changes.

## License

MIT License - See [LICENSE](LICENSE) for details.
