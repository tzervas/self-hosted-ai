# Agent Server
# Dedicated server for running AI agents with Google ADK orchestration

FROM python:3.11-slim-bookworm AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Rust for native extensions
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dependency files
COPY agents/pyproject.toml agents/requirements.txt ./agents/
COPY rust-agents/Cargo.toml rust-agents/Cargo.lock ./rust-agents/
COPY rust-agents/src ./rust-agents/src

# Build Rust extensions
WORKDIR /app/rust-agents
RUN cargo build --release --features python

# Install Python dependencies
WORKDIR /app
COPY agents ./agents
RUN pip install --no-cache-dir -e "./agents[dev]"

# Copy agent server application
COPY agent-server/app ./app
COPY agent-server/alembic ./alembic
COPY agent-server/alembic.ini ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash agent && \
    chown -R agent:agent /app
USER agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
