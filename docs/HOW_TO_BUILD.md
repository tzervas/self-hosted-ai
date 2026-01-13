# Self-Hosted AI Stack - How to Build

**Version:** 2.0.0 | **Last Updated:** January 11, 2026

---

## Table of Contents

1. [Adding Custom Models](#adding-custom-models)
2. [Creating ComfyUI Workflows](#creating-comfyui-workflows)
3. [Installing ComfyUI Custom Nodes](#installing-comfyui-custom-nodes)
4. [Building A1111 Extensions](#building-a1111-extensions)
5. [Creating Agent Workflows](#creating-agent-workflows)
6. [Extending the Ingest Pipeline](#extending-the-ingest-pipeline)
7. [Building API Integrations](#building-api-integrations)
8. [Local Development Setup](#local-development-setup)

---

## Adding Custom Models

### Ollama Models (LLMs)

**Pull existing models:**
```bash
# On GPU worker
docker exec ollama-gpu-worker ollama pull llama3.2:70b

# On server (CPU)
docker exec ollama-cpu-server ollama pull mistral:7b
```

**Create custom Modelfile:**
```dockerfile
# Save as MyModel.modelfile
FROM llama3.2:latest

PARAMETER temperature 0.7
PARAMETER num_ctx 8192
PARAMETER top_p 0.9

SYSTEM """
You are a specialized coding assistant with expertise in Python and Rust.
Always provide clear explanations and working code examples.
"""
```

**Build and push:**
```bash
docker exec ollama-gpu-worker ollama create my-coder -f /path/to/MyModel.modelfile
```

### ComfyUI Models

**Directory structure:**
```
/data/comfyui/models/
├── checkpoints/     # Main model files (.safetensors, .ckpt)
├── loras/           # LoRA adapters
├── vae/             # VAE models
├── embeddings/      # Textual embeddings
├── controlnet/      # ControlNet models
├── upscale_models/  # Upscaler models
├── clip/            # CLIP models
└── unet/            # UNet models (FLUX)
```

**Sync from local:**
```bash
./scripts/sync-models.sh sync checkpoints
```

**Manual download:**
```bash
# On GPU worker
cd /data/comfyui/models/checkpoints
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

### A1111 Models

Models are shared with ComfyUI. Place in:
```
/data/models/Stable-diffusion/  # Checkpoints
/data/models/Lora/              # LoRAs
/data/models/VAE/               # VAE
```

---

## Creating ComfyUI Workflows

### Workflow Structure

```json
{
  "last_node_id": 10,
  "last_link_id": 12,
  "nodes": [
    {
      "id": 1,
      "type": "CheckpointLoaderSimple",
      "pos": [50, 100],
      "size": [315, 98],
      "properties": {},
      "widgets_values": ["sd_xl_base_1.0.safetensors"]
    }
  ],
  "links": [
    [1, 1, 0, 2, 0, "MODEL"]  // [link_id, from_node, from_slot, to_node, to_slot, type]
  ],
  "groups": [],
  "config": {},
  "extra": {
    "workflow_type": "txt2img",
    "version": "1.0"
  }
}
```

### Step-by-Step: Create a Style Transfer Workflow

1. **Start with base txt2img:**
   ```json
   {
     "nodes": [
       {"id": 1, "type": "CheckpointLoaderSimple"},
       {"id": 2, "type": "CLIPTextEncode"},  // Positive
       {"id": 3, "type": "CLIPTextEncode"},  // Negative
       {"id": 4, "type": "EmptyLatentImage"},
       {"id": 5, "type": "KSampler"},
       {"id": 6, "type": "VAEDecode"},
       {"id": 7, "type": "SaveImage"}
     ]
   }
   ```

2. **Add LoRA loader for style:**
   ```json
   {"id": 8, "type": "LoraLoader", "widgets_values": ["style_lora.safetensors", 0.8, 0.8]}
   ```

3. **Insert into chain:**
   - Checkpoint → LoRA Loader → CLIP Encoders

4. **Test in ComfyUI UI** before saving

### Registering Workflows

Add to `config/comfyui-workflows/manifest.yml`:

```yaml
workflows:
  my-custom-workflow:
    name: "My Custom Workflow"
    file: my-custom-workflow.json
    description: "Description of what it does"
    priority: optional
    tags: [custom, style]
    requirements:
      vram_min_gb: 8
      models:
        - type: checkpoint
          name: sd_xl_base_1.0.safetensors
          path: checkpoints/
        - type: lora
          name: style_lora.safetensors
          path: loras/
```

---

## Installing ComfyUI Custom Nodes

### Via Git Clone

```bash
# SSH into GPU worker
ssh kang@192.168.1.99

# Navigate to custom nodes
cd /data/comfyui/custom_nodes

# Clone node repository
git clone https://github.com/comfyanonymous/ComfyUI_ExampleNode.git

# Install dependencies
cd ComfyUI_ExampleNode
pip install -r requirements.txt

# Restart ComfyUI
docker restart comfyui-worker
```

### Popular Custom Nodes

| Node | Purpose | Repo |
|------|---------|------|
| ComfyUI-Manager | Node management UI | ltdrdata/ComfyUI-Manager |
| VideoHelperSuite | Video I/O | Kosinkadink/ComfyUI-VideoHelperSuite |
| ComfyUI-Whisper | Audio transcription | digitaljohn/ComfyUI-Whisper |
| ComfyUI-BLIP | Image captioning | WASasquatch/ComfyUI-BLIP |
| ControlNet | Pose/edge control | Fannovel16/comfyui_controlnet_aux |

### Via ComfyUI Manager (Recommended)

1. Install ComfyUI Manager first
2. Access ComfyUI UI
3. Click "Manager" button
4. Search and install nodes

---

## Building A1111 Extensions

### Extension Structure

```
my_extension/
├── scripts/
│   └── my_script.py       # Main script
├── javascript/
│   └── my_extension.js    # UI additions
├── style.css              # Custom styles
├── install.py             # Installation script
└── requirements.txt       # Dependencies
```

### Basic Extension Script

```python
# scripts/my_script.py
import gradio as gr
from modules import script_callbacks

def on_ui_tabs():
    with gr.Blocks() as my_interface:
        gr.Markdown("# My Extension")
        
        with gr.Row():
            input_text = gr.Textbox(label="Input")
            output_text = gr.Textbox(label="Output")
        
        btn = gr.Button("Process")
        btn.click(process_fn, inputs=[input_text], outputs=[output_text])
    
    return [(my_interface, "My Extension", "my_extension")]

def process_fn(text):
    return f"Processed: {text}"

script_callbacks.on_ui_tabs(on_ui_tabs)
```

### Installation

```bash
cd /data/automatic1111/extensions
git clone https://github.com/your-repo/my_extension.git
docker restart automatic1111-worker
```

---

## Creating Agent Workflows

### Workflow YAML Structure

```yaml
# workflows/my_workflow.yaml
name: "My Custom Workflow"
version: "1.0.0"
description: "What this workflow does"

triggers:
  - type: api
    endpoint: /api/my-workflow
  - type: chat_command
    pattern: "/myworkflow {input}"

stages:
  stage_1:
    description: "First step"
    agent: ollama
    model: llama3.2:latest
    prompt_template: |
      Process this: {input}
    output_format: text
    
  stage_2:
    description: "Second step"
    service: comfyui
    workflow: txt2img-sdxl
    config:
      prompt_template: "{stage_1.output}"
    
outputs:
  result:
    type: file
    path: "/data/outputs/"
```

### Python Agent Implementation

```python
# agents/specialized/my_agent.py
from core.base import BaseAgent
from core.task import Task, TaskResult

class MyCustomAgent(BaseAgent):
    """Custom agent for specific task."""
    
    def __init__(self):
        super().__init__(
            name="my-custom-agent",
            description="Does something specific"
        )
        
    async def execute(self, task: Task) -> TaskResult:
        # Process input
        input_data = task.input_data
        
        # Call services
        response = await self.call_ollama(
            prompt=f"Process: {input_data}",
            model="llama3.2:latest"
        )
        
        # Generate image if needed
        if task.config.get("generate_image"):
            image = await self.call_comfyui(
                workflow="txt2img-sdxl",
                prompt=response
            )
            return TaskResult(success=True, output={"text": response, "image": image})
        
        return TaskResult(success=True, output=response)
```

---

## Extending the Ingest Pipeline

### Custom Processor

```python
# ingest-service/processors/my_processor.py
from main import DocumentProcessor, DocumentType

class MyCustomProcessor(DocumentProcessor):
    """Process custom file type."""
    
    EXTENSION_TO_TYPE = {
        **DocumentProcessor.EXTENSION_TO_TYPE,
        ".myext": DocumentType.UNKNOWN,  # Add custom extension
    }
    
    async def extract_text(self, filepath: str, doc_type: DocumentType) -> str:
        if filepath.endswith(".myext"):
            return await self._extract_myext(filepath)
        return await super().extract_text(filepath, doc_type)
    
    async def _extract_myext(self, filepath: str) -> str:
        # Custom extraction logic
        with open(filepath, 'r') as f:
            return f.read()
```

### Adding a Webhook

```python
# Add to ingest-service/main.py

@app.post("/webhooks/process")
async def webhook_process(request: Request):
    """Webhook to trigger processing."""
    data = await request.json()
    filepath = data.get("filepath")
    
    if filepath and os.path.exists(filepath):
        doc = await processor.process_document(filepath)
        return {"status": "processed", "document_id": doc.id}
    
    raise HTTPException(400, "Invalid filepath")
```

---

## Building API Integrations

### OpenAI-Compatible API

The stack provides OpenAI-compatible endpoints via Ollama:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://192.168.1.170:11434/v1",
    api_key="not-needed"  # Ollama doesn't require key
)

response = client.chat.completions.create(
    model="llama3.2:latest",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"}
    ]
)
print(response.choices[0].message.content)
```

### Custom FastAPI Service

```python
# services/my_service/main.py
from fastapi import FastAPI
import httpx

app = FastAPI()

OLLAMA_URL = "http://ollama-cpu:11434"
COMFYUI_URL = "http://192.168.1.99:8188"

@app.post("/generate")
async def generate(prompt: str):
    async with httpx.AsyncClient() as client:
        # Get text response
        text_resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False}
        )
        text = text_resp.json()["response"]
        
        # Generate image
        # ... ComfyUI API call ...
        
        return {"text": text, "image_url": "..."}
```

### Docker Integration

```yaml
# Add to docker-compose.yml
my-service:
  build: ./services/my_service
  ports:
    - "8400:8400"
  environment:
    - OLLAMA_URL=http://ollama-cpu:11434
  depends_on:
    - ollama-cpu
```

---

## Local Development Setup

### Prerequisites

```bash
# Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Rust (for rust-agents)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### Development Mode

```bash
# Run setup script
./scripts/setup-dev.sh

# Run tests
pytest tests/ -v

# Type checking
mypy agents/

# Linting
ruff check .
```

### Testing Workflows Locally

```bash
# Start local services (without GPU)
cd server
docker compose --profile basic up -d

# Test with CPU inference
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.2:3b", "prompt": "Hello"}'
```

### Remote Debugging

```bash
# SSH tunnel to GPU worker
ssh -L 8188:localhost:8188 -L 7860:localhost:7860 kang@192.168.1.99

# Access ComfyUI at localhost:8188
# Access A1111 at localhost:7860
```

---

## Best Practices

### Code Quality

1. **Type hints everywhere**
2. **Docstrings for public methods**
3. **Tests for new features**
4. **Follow existing patterns**

### Performance

1. **Async where possible**
2. **Batch operations**
3. **Cache expensive computations**
4. **Use appropriate models for task**

### Security

1. **Never commit credentials**
2. **Use environment variables**
3. **Validate all inputs**
4. **Rate limit public endpoints**

---

*For API reference and specifications, see [API_REFERENCE.md](API_REFERENCE.md).*
