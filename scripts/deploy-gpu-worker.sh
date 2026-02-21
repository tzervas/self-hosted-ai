#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GPU_WORKER_DIR="$PROJECT_DIR/gpu-worker"

cd "$GPU_WORKER_DIR"

# Detect container runtime (prefer podman, fallback to docker)
if command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
    COMPOSE_COMMAND="podman compose"
elif command -v docker &> /dev/null; then
    CONTAINER_RUNTIME="docker"
    COMPOSE_COMMAND="docker compose"
else
    echo "Error: Neither Podman nor Docker is installed"
    exit 1
fi

echo "Using container runtime: $CONTAINER_RUNTIME"

usage() {
    echo "Usage: $0 {deploy|stop|status|logs|update|pull-model <model>|list-models|test|benchmark|comfyui-status}"
    exit 1
}

check_dependencies() {
    if ! command -v $CONTAINER_RUNTIME &> /dev/null; then
        echo "Error: $CONTAINER_RUNTIME is not installed"
        exit 1
    fi

    if ! $COMPOSE_COMMAND version &> /dev/null; then
        echo "Error: $CONTAINER_RUNTIME compose is not installed or not working"
        exit 1
    fi

    if ! command -v nvidia-smi &> /dev/null; then
        echo "Warning: nvidia-smi not found. GPU may not be available."
    fi
}

deploy() {
    echo "Deploying GPU worker (Ollama + ComfyUI)..."
    $COMPOSE_COMMAND up -d
    echo "GPU worker deployed."
    echo "  Ollama API: http://localhost:11434"
    echo "  ComfyUI:    http://localhost:8188"
}

stop() {
    echo "Stopping GPU worker..."
    $COMPOSE_COMMAND down
}

status() {
    echo "GPU worker status:"
    $COMPOSE_COMMAND ps

    echo ""
    echo "GPU status:"
    nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits || echo "nvidia-smi failed"

    echo ""
    echo "ComfyUI status:"
    if curl -s http://localhost:8188/system_stats > /dev/null 2>&1; then
        echo "✓ ComfyUI API responding at http://localhost:8188"
    else
        echo "✗ ComfyUI API not responding"
    fi
}

logs() {
    $COMPOSE_COMMAND logs -f
}

update() {
    echo "Updating GPU worker..."
    $COMPOSE_COMMAND pull
    $COMPOSE_COMMAND up -d
}

pull_model() {
    MODEL="$1"
    if [ -z "$MODEL" ]; then
        echo "Error: Please specify a model name"
        exit 1
    fi
    echo "Pulling model: $MODEL"
    timeout 600 $COMPOSE_COMMAND exec ollama-gpu ollama pull "$MODEL"
}

list_models() {
    echo "Available GPU models:"
    $COMPOSE_COMMAND exec ollama-gpu ollama list
}

test() {
    echo "Testing GPU worker..."

    # Wait for service
    echo "Waiting for Ollama to start..."
    sleep 10

    # Test API
    echo "Testing Ollama API..."
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "✓ Ollama API responding"
    else
        echo "✗ Ollama API not responding"
    fi

    # Test GPU access
    echo "Testing GPU access..."
    if $COMPOSE_COMMAND exec ollama-gpu nvidia-smi > /dev/null 2>&1; then
        echo "✓ GPU accessible from container"
    else
        echo "✗ GPU not accessible from container"
    fi

    # Test inference
    echo "Testing inference..."
    if $COMPOSE_COMMAND exec ollama-gpu ollama run llama3.2 "Hello" --format json > /dev/null 2>&1; then
        echo "✓ Inference working"
    else
        echo "✗ Inference failed"
    fi
}

benchmark() {
    echo "Benchmarking GPU Ollama..."

    # Simple inference test
    echo "Running inference test..."
    # Capture output and check PIPESTATUS[0] for actual command exit code
    set +e  # Temporarily disable exit-on-error
    OUTPUT=$(timeout 60 $COMPOSE_COMMAND exec ollama-gpu ollama run llama3.2 "Write a short summary of artificial intelligence." 2>&1)
    RESULT=${PIPESTATUS[0]}
    set -e  # Re-enable exit-on-error

    if [ "$RESULT" -eq 0 ]; then
        echo "$OUTPUT" | head -10
        echo "✓ GPU Inference successful"
    else
        echo "✗ GPU Inference failed or timed out (exit code: $RESULT)"
    fi
}

comfyui_status() {
    echo "ComfyUI Status"
    echo "=============="

    # Check if container is running
    if $COMPOSE_COMMAND ps comfyui 2>/dev/null | grep -q "running"; then
        echo "✓ Container: Running"
    else
        echo "✗ Container: Not running"
        return 1
    fi

    # Check API
    if curl -s http://localhost:8188/system_stats > /dev/null 2>&1; then
        echo "✓ API: Responding"
        echo ""
        echo "System Info:"
        curl -s http://localhost:8188/system_stats | jq -r '
            "  GPU: \(.devices[0].name // "Unknown")",
            "  VRAM Total: \((.devices[0].vram_total // 0) / 1024 / 1024 / 1024 | floor)GB",
            "  VRAM Free: \((.devices[0].vram_free // 0) / 1024 / 1024 / 1024 | floor)GB"
        ' 2>/dev/null || echo "  (Unable to parse system stats)"
    else
        echo "✗ API: Not responding"
    fi

    # Check for checkpoint models
    DATA_PATH="${DATA_PATH:-/data}"
    echo ""
    echo "Checkpoint Models:"
    if [ -d "${DATA_PATH}/comfyui/models/checkpoints" ]; then
        find "${DATA_PATH}/comfyui/models/checkpoints" -name "*.safetensors" -o -name "*.ckpt" 2>/dev/null | while read -r model; do
            echo "  - $(basename "$model")"
        done
        if [ -z "$(find "${DATA_PATH}/comfyui/models/checkpoints" -name "*.safetensors" -o -name "*.ckpt" 2>/dev/null)" ]; then
            echo "  (No models found - download SDXL or SD1.5 checkpoint)"
        fi
    else
        echo "  (Directory not initialized)"
    fi
}

check_dependencies

case "$1" in
    deploy)
        deploy
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    update)
        update
        ;;
    pull-model)
        pull_model "$2"
        ;;
    list-models)
        list_models
        ;;
    test)
        test
        ;;
    benchmark)
        benchmark
        ;;
    comfyui-status)
        comfyui_status
        ;;
    *)
        usage
        ;;
esac