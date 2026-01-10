#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GPU_WORKER_DIR="$PROJECT_DIR/gpu-worker"

cd "$GPU_WORKER_DIR"

usage() {
    echo "Usage: $0 {deploy|stop|status|logs|update|pull-model <model>|list-models|test|benchmark}"
    exit 1
}

check_dependencies() {
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed"
        exit 1
    fi

    if ! command -v docker compose &> /dev/null; then
        echo "Error: Docker Compose is not installed"
        exit 1
    fi

    if ! command -v nvidia-smi &> /dev/null; then
        echo "Warning: nvidia-smi not found. GPU may not be available."
    fi
}

deploy() {
    echo "Deploying GPU worker..."
    docker compose up -d
    echo "GPU worker deployed. API available at http://localhost:11434"
}

stop() {
    echo "Stopping GPU worker..."
    docker compose down
}

status() {
    echo "GPU worker status:"
    docker compose ps

    echo ""
    echo "GPU status:"
    nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits || echo "nvidia-smi failed"
}

logs() {
    docker compose logs -f
}

update() {
    echo "Updating GPU worker..."
    docker compose pull
    docker compose up -d
}

pull_model() {
    MODEL="$1"
    if [ -z "$MODEL" ]; then
        echo "Error: Please specify a model name"
        exit 1
    fi
    echo "Pulling model: $MODEL"
    timeout 600 docker compose exec ollama-gpu ollama pull "$MODEL"
}

list_models() {
    echo "Available GPU models:"
    docker compose exec ollama-gpu ollama list
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
    if docker compose exec ollama-gpu nvidia-smi > /dev/null 2>&1; then
        echo "✓ GPU accessible from container"
    else
        echo "✗ GPU not accessible from container"
    fi

    # Test inference
    echo "Testing inference..."
    if docker compose exec ollama-gpu ollama run llama3.2 "Hello" --format json > /dev/null 2>&1; then
        echo "✓ Inference working"
    else
        echo "✗ Inference failed"
    fi
}

benchmark() {
    echo "Benchmarking GPU Ollama..."

    # Simple inference test
    echo "Running inference test..."
    timeout 60 docker compose exec ollama-gpu ollama run llama3.2 "Write a short summary of artificial intelligence." 2>/dev/null | head -10
    if [ $? -eq 0 ]; then
        echo "✓ GPU Inference successful"
    else
        echo "✗ GPU Inference failed or timed out"
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
    *)
        usage
        ;;
esac