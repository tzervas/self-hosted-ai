# Self-hosted AI homelab stack: verified configurations and patterns

**Your configuration assumptions are largely accurate**, but several critical environment variables need correction—particularly n8n's license activation and Ollama's GPU memory settings. The 14GB VRAM soft cap supports models up to ~20B parameters at Q4_K_M quantization, and video generation is now highly feasible with optimized forks like Wan2GP reducing requirements to 6-12GB VRAM.

This verification covers exact environment variable syntax against official documentation (January 2026), GitOps patterns, VRAM calculations, and identifies discrepancies where your assumptions may differ from current implementations.

---

## n8n configuration verification

The n8n documentation confirms most environment variables but reveals important distinctions between community and enterprise features.

**License activation** uses `N8N_LICENSE_KEY` (not `N8N_LICENSE_ACTIVATION_KEY`). The enterprise license enables source control, external secrets, LDAP, SAML, OIDC, RBAC, and log streaming—none available in community edition. Clear a license with `n8n license:clear` via CLI.

**Queue mode with Redis/Valkey** requires these exact variables:
```bash
EXECUTIONS_MODE=queue
QUEUE_BULL_REDIS_HOST=redis-hostname
QUEUE_BULL_REDIS_PORT=6379
QUEUE_BULL_REDIS_PASSWORD=yourpassword
```
Workers run separately using `n8n worker` command. Valkey is wire-compatible with Redis, requiring no configuration changes.

**Binary data handling** options for `N8N_DEFAULT_BINARY_DATA_MODE`:
- `default` — stores in memory (small files only)
- `filesystem` — local storage at `N8N_BINARY_DATA_STORAGE_PATH`
- `s3` — external storage using `N8N_EXTERNAL_STORAGE_S3_HOST`, `N8N_EXTERNAL_STORAGE_S3_BUCKET_NAME`, `N8N_EXTERNAL_STORAGE_S3_ACCESS_KEY`, `N8N_EXTERNAL_STORAGE_S3_SECRET_KEY`

**PostgreSQL backing database**:
```bash
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres-hostname
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=yourpassword
```

**Workflow import/export** supports three methods: CLI commands (`n8n export:workflow --all --output=backups/`), REST API (`POST /rest/workflows`), and UI paste/upload. Bootstrapping uses `n8n import:workflow --input=file.json` with `--truncateTables` for non-empty databases.

---

## Open WebUI configuration verification

All queried environment variables are confirmed accurate in the v0.7.1 documentation.

**Admin account creation** uses exactly these variables:
```bash
WEBUI_ADMIN_EMAIL=admin@example.com
WEBUI_ADMIN_PASSWORD=secure_password
WEBUI_ADMIN_NAME=Administrator  # Optional, defaults to "Admin"
```
Admin creation triggers automatically only on fresh installations. `ENABLE_SIGNUP` is automatically disabled after admin creation for security.

**SearXNG integration** requires this exact syntax:
```bash
ENABLE_RAG_WEB_SEARCH=True
RAG_WEB_SEARCH_ENGINE=searxng  # lowercase required
SEARXNG_QUERY_URL=http://searxng:8080/search?q=<query>  # <query> placeholder mandatory
RAG_WEB_SEARCH_RESULT_COUNT=3
```
The `<query>` placeholder gets replaced at runtime—omitting it breaks search functionality.

**Ollama connection** uses `OLLAMA_BASE_URL` (not `OLLAMA_API_BASE_URL`, which is deprecated):
```bash
OLLAMA_BASE_URL=http://localhost:11434  # No trailing slash
```
For multiple instances: `OLLAMA_BASE_URLS="http://host-one:11434;http://host-two:11434"` (semicolon-separated).

**Voice/audio configuration** verified options:
| Variable | Valid Values |
|----------|-------------|
| `AUDIO_STT_ENGINE` | `""` (local Whisper), `openai`, `azure`, `deepgram`, `mistral` |
| `AUDIO_TTS_ENGINE` | `""` (disabled), `openai`, `elevenlabs`, `azure`, `transformers` |
| `WHISPER_MODEL` | `base`, `small`, `medium`, `large-v3` |
| `WHISPER_COMPUTE_TYPE` | `int8`, `float16`, `int8_float16`, `float32` |

**RAG configuration** uses `RAG_EMBEDDING_ENGINE=ollama` with `RAG_EMBEDDING_MODEL=nomic-embed-text-v1.5` for local embeddings. Vector store options: `chroma` (default), `pgvector`, `milvus`, `qdrant`, `elasticsearch`, `opensearch`, `pinecone`. Chunk size/overlap configured in Admin Panel UI, not environment variables.

**ENABLE_SIGNUP behavior**: Setting `false` hides registration completely. First user becomes admin regardless. This is a `PersistentConfig` variable—values persist in database after first launch, potentially overriding environment variables. Use `ENABLE_PERSISTENT_CONFIG=False` to force environment variable precedence.

---

## GitLab and Traefik configuration verification

**GitLab Helm chart monitoring**:
```yaml
prometheus:
  install: false  # or true to include bundled Prometheus

gitlab:
  webservice:
    metrics:
      enabled: true
      serviceMonitor:
        enabled: true  # Creates Prometheus Operator ServiceMonitor
```

**monitoring_whitelist** syntax in gitlab.rb:
```ruby
gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '192.168.0.1', '10.0.0.0/8']
```
Supports CIDR ranges and single hosts. Default allows only localhost; Helm chart defaults to `0.0.0.0/0` (all addresses).

**Distributed tracing** uses this exact format:
```bash
GITLAB_TRACING="opentracing://jaeger?http_endpoint=http%3A%2F%2Flocalhost%3A14268%2Fapi%2Ftraces&sampler=const&sampler_param=1"
```
Note URL-encoded characters. Additional variables: `GITLAB_TRACING_TRACK_CACHES=true`, `GITLAB_TRACING_TRACK_REDIS=true`.

**External PostgreSQL/Redis configuration**:
```yaml
postgresql:
  install: false
global:
  psql:
    host: psql.example.com
    port: 5432
    database: gitlabhq_production
    password:
      secret: gitlab-postgresql-password
      key: postgres-password

redis:
  install: false
global:
  redis:
    host: redis.example.com
    auth:
      enabled: true
      secret: gitlab-redis
      key: redis-password
```

**Traefik Docker labels** verified syntax:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.myapp.rule=Host(`example.com`)"
  - "traefik.http.routers.myapp.entrypoints=websecure"
  - "traefik.http.routers.myapp.tls.certresolver=myresolver"
  - "traefik.http.services.myapp.loadbalancer.server.port=8080"
```

**SSL/TLS with Let's Encrypt** (HTTP challenge):
```yaml
certificatesResolvers:
  myresolver:
    acme:
      email: your-email@example.com
      storage: acme.json
      httpChallenge:
        entryPoint: web
```
DNS challenge required for wildcard certificates.

**WebSocket support**: Traefik supports WebSocket **out of the box**—no special configuration needed. For SSE/streaming: Traefik does **NOT** buffer responses by default, so SSE works natively. There's no `proxy_buffering off` equivalent because buffering isn't enabled. Avoid the Buffering middleware for streaming endpoints.

---

## Ollama and LiteLLM configuration verification

**OLLAMA_KEEP_ALIVE** exact syntax and behavior:
```bash
OLLAMA_KEEP_ALIVE=5m    # Default: 5 minutes
OLLAMA_KEEP_ALIVE=24h   # 24 hours
OLLAMA_KEEP_ALIVE=-1    # Keep loaded forever
OLLAMA_KEEP_ALIVE=0     # Immediate unload after response
```
Duration strings supported: `10m`, `1h`, `24h`. API `keep_alive` parameter overrides environment variable per-request.

**⚠️ DISCREPANCY: No OLLAMA_GPU_MEMORY_FRACTION exists.** Ollama uses different mechanisms:
| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_GPU_OVERHEAD` | Reserve VRAM per GPU (bytes) | 0 |
| `OLLAMA_MAX_LOADED_MODELS` | Max concurrent models | 3 × GPUs |
| `OLLAMA_NUM_PARALLEL` | Parallel requests/model | 1 or 4 |
| `OLLAMA_FLASH_ATTENTION` | Enable flash attention | false |
| `OLLAMA_KV_CACHE_TYPE` | KV cache quantization | `f16` (also `q8_0`, `q4_0`) |

**GGUF model loading** via Modelfile:
```dockerfile
FROM /path/to/file.gguf
# Or with adapter:
FROM llama3.1
ADAPTER /path/to/adapter.gguf
```
Create with: `ollama create my-model -f Modelfile`. Supported quantizations: `q4_0`, `q4_1`, `q5_0`, `q5_1`, `q8_0`, `q3_K_S/M/L`, `q4_K_S/M`, `q5_K_S/M`, `q6_K`.

**Hugging Face GGUF models**: `ollama run hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q8_0`

**ReBAR**: No Ollama-specific configuration exists. ReBAR is a hardware/BIOS feature that may improve VRAM access speeds but requires no Ollama settings.

**LiteLLM LITELLM_MASTER_KEY** must start with `sk-`:
```bash
export LITELLM_MASTER_KEY=sk-1234
```
Used for admin authentication and generating virtual keys via `/key/generate`.

**LiteLLM Ollama proxy configuration** (config.yaml):
```yaml
model_list:
  - model_name: "llama3.1"
    litellm_params:
      model: "ollama_chat/llama3.1"  # Use ollama_chat/ for /api/chat endpoint
      api_base: "http://localhost:11434"
      keep_alive: "8m"
```
Prefix `ollama/` routes to `/api/generate`; `ollama_chat/` routes to `/api/chat` (recommended).

**Virtual keys and rate limiting** require PostgreSQL (`DATABASE_URL`):
```bash
curl 'http://0.0.0.0:4000/key/generate' \
  -H 'Authorization: Bearer sk-1234' \
  -d '{"tpm_limit": 1000, "rpm_limit": 100, "max_budget": 50, "budget_duration": "30d"}'
```

---

## ArgoCD GitOps patterns for homelab

**App-of-Apps pattern** structure:
```yaml
# Root application (argocd/apps/root.yaml)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-apps
  namespace: argocd
spec:
  source:
    path: apps  # Contains child Application manifests
    repoURL: https://github.com/your-org/gitops-repo.git
  destination:
    namespace: argocd
    server: https://kubernetes.default.svc
  syncPolicy:
    automated:
      selfHeal: true
      prune: true
```

**Sync waves annotation syntax**:
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"  # Lower numbers sync first
```
Convention: `-2` namespaces, `-1` configmaps/secrets, `0` databases, `1` migrations, `2+` applications.

**Database-first ordering** example:
```yaml
# Wave 0: PostgreSQL StatefulSet
# Wave 1: Database migration Job (with argocd.argoproj.io/hook: PreSync)
# Wave 2: n8n Deployment
# Wave 3: Open WebUI Deployment
```

**Self-management pattern** safety:
```yaml
syncPolicy:
  automated:
    prune: false  # CRITICAL: Never auto-prune ArgoCD itself
    selfHeal: true
```

**Secret management options** (ranked):
1. **External Secrets Operator** — Multi-provider (Vault, AWS, GCP), auto-refresh
2. **SealedSecrets** — K8s-native, git-friendly, per-cluster encryption
3. **SOPS** — Supports multiple key types, version-controlled

**argocd-initial-admin-secret** retrieval:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

**Helm chart sources**:
| Component | Chart Repository | Notes |
|-----------|-----------------|-------|
| Ollama | `helm repo add otwld https://helm.otwld.com/` | Community-maintained |
| Open WebUI | `helm repo add open-webui https://helm.openwebui.com/` | **Official** |
| n8n | `helm repo add community-charts https://community-charts.github.io/helm-charts` | 8gears community |
| GitLab | `helm repo add gitlab https://charts.gitlab.io/` | Official |
| ArgoCD | `helm repo add argo https://argoproj.github.io/argo-helm` | Official |

**GPU resource reservations**:
```yaml
spec:
  runtimeClassName: nvidia
  containers:
    - resources:
        limits:
          nvidia.com/gpu: "1"
        requests:
          nvidia.com/gpu: "1"
  nodeSelector:
    nvidia.com/gpu.present: "true"
```

**PVC sizing for Ollama models**: 20-30GB for single 7B models, 50-100GB for multiple models, 200GB+ for production with many models. Use `local-path` or `openebs-hostpath` for fast local NVMe—avoid network storage.

---

## VRAM estimation and model recommendations

**Verified VRAM formula**:
```
VRAM (GB) = (Parameters × Bytes_per_weight) + CUDA_overhead + KV_cache
```
Where:
- CUDA overhead ≈ 0.55GB + (0.08 × Parameters in billions)
- Standard overhead multiplier: **1.2×** (20%)

**Quantization specifications**:
| Format | Bytes/Weight | 7B Model Size | PPL Impact |
|--------|-------------|---------------|------------|
| FP16 | 2.0 | 14 GB | Baseline |
| Q8_0 | 1.0 | 7 GB | +0.00 (lossless) |
| Q6_K | ~0.78 | 5.5 GB | +0.02 |
| Q5_K_M | ~0.68 | 4.8 GB | +0.04 |
| **Q4_K_M** | **~0.57** | **4.1 GB** | **+0.05** (recommended) |
| Q3_K_M | ~0.45 | 3.1 GB | +0.24 |

**⚠️ MXFP4 requires compute capability ≥9.0**: Only H100, B100, B200, RTX 5090. Not viable for RTX 3090/4090. Use Q4_K_M as consumer alternative.

**KV cache sizing formula**:
```
KV_cache (bytes/token) = 4 × num_layers × hidden_dim × bytes_per_kv
```
For Llama 7B (32 layers, 4096 dim, FP16): ~0.5 MB/token → **4GB at 8K context**, **16GB at 32K context**.

**14GB soft cap viability**:
| Model | Q4_K_M Size | With 8K Context | Viable? |
|-------|-------------|-----------------|---------|
| Qwen3 8B | 4.6 GB | ~5.9 GB | ✅ |
| Gemma 3 12B | 6.8 GB | ~8.5 GB | ✅ |
| Qwen3 14B | 8.0 GB | ~9.8 GB | ✅ |
| GPT-OSS 20B | 11.4 GB | ~13.7 GB | ✅ (tight) |
| 32B models | 18+ GB | — | ❌ |

**Best models for 16GB VRAM (January 2026)**:
- **Fast general use**: `ollama pull qwen3:8b` (~5.8 GB, 40-60 t/s)
- **Best quality**: `ollama pull gemma3:12b` (~8.5 GB)
- **Top reasoning**: `ollama pull qwen3:14b` or `ollama pull phi4:14b`
- **Maximum size**: `ollama pull gpt-oss:20b-q4_k_m` (~13.7 GB at 8K context)

**Uncensored models**:
- `ollama run dolphin3-abliterated:8b` — Abliterated Dolphin 3.0
- `ollama run dolphin-llama3` — Eric Hartford's flagship
- `ollama run wizardlm-uncensored:13b` — Complex instructions
- `huihui_ai/dolphin3-abliterated` on Hugging Face

**Vision models for 14GB**:
- `ollama pull qwen2-vl:7b` — ~6 GB with images, excellent OCR
- `ollama pull llava:7b` — <8 GB, general vision tasks

---

## Video generation within 14GB VRAM

**Wan2.1/Wan2.2 confirmed** with excellent 14GB viability via Wan2GP fork:
| Model | Resolution | VRAM (Wan2GP) | Duration |
|-------|-----------|---------------|----------|
| T2V-1.3B | 832×480 | **8.2 GB** | 5s |
| T2V-14B | 480p | **8 GB** (offload) | 5s |
| T2V-14B | 480p, 128 frames | **12 GB** | 8s |
| Wan 2.2 Ovi | 720p | **6 GB** | 121 frames |

The [deepbeepmeep/Wan2GP](https://github.com/deepbeepmeep/Wan2GP) fork provides **2× VRAM reduction** through aggressive offloading and includes FastWan LoRA Accelerator for 10× speed.

**HunyuanVideo 1.5** is the **best quality option** at exactly 14GB:
- 8.3B parameters, step-distilled model (8-12 steps vs 50)
- 480p I2V in ~75 seconds on RTX 4090
- Native 14GB with offloading enabled

**FramePack** enables **minute-long videos** at just 6GB VRAM through fixed-length temporal context compression.

**Model comparison for 14GB**:
| Model | Max Resolution | Max Duration | Quality |
|-------|---------------|--------------|---------|
| AnimateDiff | 512×768 | 2s | Good |
| SVD-XT | 1024×576 | 3.5s | Very Good |
| CogVideoX-2B | 720×480 | 6s | Good |
| Wan2.1 14B (GP) | 720p | 8s | Excellent |
| HunyuanVideo 1.5 | 720p | 5-10s | Excellent |
| **FramePack** | 720p | **60s** | Good |

**Consistency techniques VRAM overhead**:
- IP-Adapter SD1.5: +1-2 GB
- ControlNet (per model): +1-1.5 GB
- IP-Adapter Plus fights motion—use strength 0.4-0.6

**ComfyUI + n8n integration**:
```bash
# Queue prompt via HTTP
POST http://comfyui:8188/prompt
{"prompt": {workflow_json}, "client_id": "unique_id"}

# Check status
GET http://comfyui:8188/history/{prompt_id}
```
Install `n8n-nodes-comfyui` via Settings → Community Nodes.

**5-minute video generation strategy**: Use FramePack for 60-second clips → stitch 5 clips → RIFE interpolation for smooth 30fps. Total time: ~1.5-2 hours at 14GB.

---

## Audio and image generation verification

**Whisper Large V3 Turbo VRAM**:
| Variant | VRAM | Speed |
|---------|------|-------|
| Large V3 (full) | ~10 GB | Baseline |
| Large V3 Turbo | **~6 GB** | 8× faster |
| Faster-Whisper (INT8) | **~3 GB** | 4× faster |
| Distil-Large-V3 | **~2.5 GB** | 6.3× faster (English-only) |

**Kokoro TTS confirmed** at `hexgrad/Kokoro-82M`:
- **82M parameters**, ~350MB model size
- **2-3 GB VRAM** (can run on CPU)
- 40-70ms latency, 54 voices, Apache 2.0 license
- No voice cloning—uses predefined voice packs

**CosyVoice2 confirmed** from Alibaba FunAudioLLM:
- **6-8 GB VRAM** for 0.5B model
- ~150ms first-packet latency
- Zero-shot voice cloning from 3-10 seconds audio
- Install: `pip install -r requirements.txt` then download from ModelScope

**Piper TTS**: CPU-only capable, 5-20MB per voice, real-time synthesis even on Raspberry Pi. Install: `pip install piper-tts`.

**FLUX.1 VRAM requirements**:
| Precision | VRAM | Quality |
|-----------|------|---------|
| FP16/BF16 | ~24 GB | Full |
| **FP8** | **~12 GB** | Near-lossless |
| Q8 GGUF | ~14 GB | Near-lossless |
| Q5 GGUF | ~10 GB | Minimal loss |
| NF4 | ~6-8 GB | Noticeable loss |

**14GB recommendation**: FLUX.1-dev Q8 GGUF or FP8 for best quality; FLUX.1-schnell Q5 for speed.

---

## MCP, GitHub Spec-Kit, and Agent Skills

**MCP Registry**: https://registry.modelcontextprotocol.io (launched September 2025, ~2000 servers registered)
- API: `GET /v0/servers?search=filesystem`
- November 2025 spec added Tasks capability and governance model

**Open WebUI MCP integration** (since v0.6.31):
- Supports Streamable HTTP only (not stdio directly)
- Use [MCPO proxy](https://github.com/open-webui/mcpo) for stdio servers:
```bash
uvx mcpo --port 8000 -- uvx mcp-server-time
# Then add http://localhost:8000 in Open WebUI Settings → Tools
```

**n8n MCP integration**:
- MCP Server Trigger Node — exposes workflows as MCP tools
- MCP Client Tool Node — connects to external MCP servers via SSE
- Community node: `n8n-nodes-mcp`

**MCP security considerations**:
- Servers execute arbitrary code—only use trusted sources
- Implement sandboxing (containers, chroot)
- Follow least privilege principle
- Mutual TLS or API key authentication required

**GitHub Spec-Kit** (https://github.com/github/spec-kit):
- Open-source toolkit for Spec-Driven Development
- Install: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`
- Supports Claude Code, Copilot, Cursor, Gemini CLI, 11+ agents
- Commands: `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`

**Agent Skills** (https://agentskills.io):
- Open standard released December 2025
- SKILL.md format with YAML frontmatter
- Supported by Claude, Copilot, Cursor, OpenAI Codex
- Partner skills: Atlassian, Figma, Canva, Stripe, Notion, Zapier

**SafeTensors to GGUF conversion**:
```bash
# Convert HF model to GGUF
python convert_hf_to_gguf.py /path/to/model --outfile model-f16.gguf --outtype f16

# Quantize
./llama-quantize model-f16.gguf model-Q4_K_M.gguf Q4_K_M
```
Recommended quantizations: Q4_K_M (best 4-bit balance), Q5_K_M (high quality), Q6_K (near-lossless).

---

## Critical discrepancies identified

| Claim | Actual Status |
|-------|--------------|
| `N8N_LICENSE_ACTIVATION_KEY` | ❌ Use `N8N_LICENSE_KEY` |
| `OLLAMA_GPU_MEMORY_FRACTION` | ❌ Does not exist—use `OLLAMA_GPU_OVERHEAD` (bytes) |
| `OLLAMA_API_BASE_URL` | ❌ Deprecated—use `OLLAMA_BASE_URL` |
| MXFP4 for consumer GPUs | ❌ Requires H100/B100/RTX 5090 |
| Traefik needs SSE config | ❌ Works out of the box—no buffering by default |
| Enterprise features in community n8n | ❌ Source control, LDAP, SAML require enterprise license |

## Conclusion

Your homelab stack configuration is architecturally sound for a 14GB VRAM constraint. The critical corrections involve using `N8N_LICENSE_KEY` instead of `N8N_LICENSE_ACTIVATION_KEY`, replacing nonexistent `OLLAMA_GPU_MEMORY_FRACTION` with `OLLAMA_GPU_OVERHEAD` (measured in bytes), and ensuring Open WebUI uses `OLLAMA_BASE_URL` without a trailing slash. For video generation, Wan2GP and FramePack have transformed the 14GB landscape—full 720p video generation at 8-14GB VRAM is now achievable with generation times under 10 minutes for 5-10 second clips. The ArgoCD App-of-Apps pattern with sync waves provides robust dependency ordering for database-first deployments, while External Secrets Operator offers the most flexible secret management for GitOps workflows.