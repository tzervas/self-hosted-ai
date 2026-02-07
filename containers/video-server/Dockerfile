# Video Generation Server v1.0
# Provides AnimateDiff-Lightning (text-to-video) and SVD (image-to-video) via REST API
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

LABEL org.opencontainers.image.source=https://github.com/tzervas/self-hosted-ai
LABEL org.opencontainers.image.description="Video generation server with AnimateDiff-Lightning and Stable Video Diffusion"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models/huggingface \
    TORCH_HOME=/models/torch \
    TRANSFORMERS_CACHE=/models/huggingface \
    DEVICE=cuda

WORKDIR /app

# Install system dependencies for video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /models /outputs && \
    chown -R appuser:appuser /app /models /outputs

# Note: Running as root for GPU access and model directory permissions
# In production with proper volume mounts, can switch to appuser

EXPOSE 5005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5005/health')" || exit 1

CMD ["python", "server.py"]
