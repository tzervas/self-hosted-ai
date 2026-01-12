"""
Image Generation Router Service

Routes image generation requests between ComfyUI and Automatic1111
based on workflow complexity, model requirements, and current load.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Image Generation Router", version="1.0.0")

# Backend configurations
BACKENDS = {
    "comfyui": {
        "url": "http://192.168.1.99:8188",
        "type": "comfyui",
        "priority": 1,  # Higher priority for complex workflows
        "max_concurrent": 2,
        "current_load": 0,
    },
    "automatic1111": {
        "url": "http://192.168.1.99:7860",
        "type": "automatic1111",
        "priority": 2,  # Lower priority, simpler interface
        "max_concurrent": 3,
        "current_load": 0,
    }
}

class ImageRequest(BaseModel):
    """Image generation request model."""
    prompt: str
    negative_prompt: Optional[str] = ""
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    steps: Optional[int] = 30
    cfg_scale: Optional[float] = 7.0
    sampler_name: Optional[str] = "Euler a"
    scheduler: Optional[str] = "Normal"
    seed: Optional[int] = -1
    batch_size: Optional[int] = 1
    workflow: Optional[str] = None  # For ComfyUI workflows

async def check_backend_health(url: str) -> bool:
    """Check if a backend is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/")
            return response.status_code == 200
    except Exception:
        return False

async def select_backend(request: ImageRequest) -> str:
    """Select the best backend for the request."""
    # Check health of all backends
    healthy_backends = {}
    for name, config in BACKENDS.items():
        if await check_backend_health(config["url"]):
            healthy_backends[name] = config
        else:
            logger.warning(f"Backend {name} is unhealthy")

    if not healthy_backends:
        raise HTTPException(status_code=503, detail="No healthy image generation backends available")

    # Route based on workflow complexity and load
    if request.workflow and request.workflow.startswith("comfyui"):
        # Force ComfyUI for specific workflows
        if "comfyui" in healthy_backends:
            return "comfyui"
    elif len(request.prompt.split()) > 50 or request.workflow:
        # Complex prompts or workflows -> ComfyUI
        if "comfyui" in healthy_backends and healthy_backends["comfyui"]["current_load"] < healthy_backends["comfyui"]["max_concurrent"]:
            return "comfyui"
    else:
        # Simple requests -> A1111 (more user-friendly)
        if "automatic1111" in healthy_backends and healthy_backends["automatic1111"]["current_load"] < healthy_backends["automatic1111"]["max_concurrent"]:
            return "automatic1111"

    # Fallback to least loaded backend
    return min(healthy_backends.items(), key=lambda x: x[1]["current_load"])[0]

async def route_to_comfyui(request: ImageRequest) -> Dict[str, Any]:
    """Route request to ComfyUI."""
    # Load workflow template
    workflow_name = request.workflow or "txt2img-sdxl"
    workflow_path = f"/app/workflows/{workflow_name}.json"

    try:
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
    except FileNotFoundError:
        # Fallback to basic workflow
        workflow = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.cfg_scale,
            "seed": request.seed
        }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{BACKENDS['comfyui']['url']}/prompt",
            json={"prompt": workflow}
        )
        return response.json()

async def route_to_automatic1111(request: ImageRequest) -> Dict[str, Any]:
    """Route request to Automatic1111."""
    payload = {
        "prompt": request.prompt,
        "negative_prompt": request.negative_prompt or "",
        "width": request.width,
        "height": request.height,
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
        "sampler_name": request.sampler_name,
        "scheduler": request.scheduler,
        "seed": request.seed,
        "batch_size": request.batch_size,
        "save_images": True
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{BACKENDS['automatic1111']['url']}/sdapi/v1/txt2img",
            json=payload
        )
        return response.json()

@app.post("/v1/images/generations")
async def generate_image(request: ImageRequest):
    """Generate an image using the best available backend."""
    backend_name = await select_backend(request)

    # Increment load counter
    BACKENDS[backend_name]["current_load"] += 1

    try:
        if backend_name == "comfyui":
            result = await route_to_comfyui(request)
        else:
            result = await route_to_automatic1111(request)

        return {
            "backend": backend_name,
            "result": result
        }
    finally:
        # Decrement load counter
        BACKENDS[backend_name]["current_load"] -= 1

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    backend_status = {}
    for name, config in BACKENDS.items():
        backend_status[name] = await check_backend_health(config["url"])

    return {
        "status": "healthy" if any(backend_status.values()) else "unhealthy",
        "backends": backend_status,
        "timestamp": time.time()
    }

@app.get("/backends")
async def list_backends():
    """List available backends and their status."""
    backend_info = {}
    for name, config in BACKENDS.items():
        backend_info[name] = {
            "url": config["url"],
            "type": config["type"],
            "healthy": await check_backend_health(config["url"]),
            "current_load": config["current_load"],
            "max_concurrent": config["max_concurrent"]
        }

    return backend_info

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)