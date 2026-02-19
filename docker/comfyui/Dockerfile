# ComfyUI with Blackwell (RTX 5080) support
# Base: NVIDIA CUDA 12.8 runtime + PyTorch 2.7 stable
#
# Build:
#   docker build -t ghcr.io/tzervas/comfyui-blackwell:latest .
#
# Run:
#   docker run --gpus all -p 8188:8188 -v models:/app/models ghcr.io/tzervas/comfyui-blackwell:latest

FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    TORCH_CUDA_ARCH_LIST="12.0" \
    PYTHONUNBUFFERED=1

# System dependencies for ComfyUI (opencv, pillow, ffmpeg for video)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev git \
    libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone ComfyUI (shallow, master branch)
RUN git clone --branch master --depth 1 https://github.com/comfyanonymous/ComfyUI.git .

# Install PyTorch 2.7+ with CUDA 12.8 (supports sm_120 / Blackwell)
RUN pip install --no-cache-dir \
    torch==2.7.0 torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128

# Install ComfyUI dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install ComfyUI-Manager for custom node management
RUN cd custom_nodes && \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Create model directories (will be overridden by PVC mounts)
RUN mkdir -p models/checkpoints models/vae models/clip models/loras \
    models/controlnet models/embeddings models/diffusion_models \
    models/text_encoders models/unet models/upscale_models

EXPOSE 8188

# Health check: ComfyUI returns JSON on /system_stats
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8188/system_stats')" || exit 1

# Run ComfyUI listening on all interfaces
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
