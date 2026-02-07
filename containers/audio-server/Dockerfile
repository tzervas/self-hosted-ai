# Audio Generation Server v1.1
# Provides AudioLDM2 (SFX), MusicGen (music), and Bark (voice) via REST API
FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

LABEL org.opencontainers.image.source=https://github.com/tzervas/self-hosted-ai
LABEL org.opencontainers.image.description="Audio generation server with AudioLDM2, MusicGen, and Bark voice synthesis"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.version="1.1.0"

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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server.py .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /models && \
    chown -R appuser:appuser /app /models

# Note: Running as root for GPU access and model directory permissions
# In production with proper volume mounts, can switch to appuser

EXPOSE 5004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5004/health')" || exit 1

CMD ["python", "server.py"]
