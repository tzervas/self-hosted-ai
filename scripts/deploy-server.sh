#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVER_DIR="$PROJECT_DIR/server"

cd "$SERVER_DIR"

usage() {
    echo "Usage: $0 {deploy [profile]|stop|status|logs|update|pull-model <model> [cpu|gpu]|list-models|check-gpu|benchmark}"
    echo "Profiles: basic (default), full, monitoring"
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
}

generate_secret_key() {
    if grep -q "your-secure-secret-key-here-change-this" .env; then
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i "s/your-secure-secret-key-here-change-this/$SECRET_KEY/" .env
        echo "Generated new WEBUI_SECRET_KEY: $SECRET_KEY"
    fi
}

deploy() {
    PROFILE="${1:-basic}"
    echo "Deploying server stack with profile: $PROFILE"

    case "$PROFILE" in
        basic)
            COMPOSE_PROFILES=""
            ;;
        full)
            COMPOSE_PROFILES="basic,full"
            ;;
        monitoring)
            COMPOSE_PROFILES="basic,monitoring"
            ;;
        *)
            echo "Invalid profile: $PROFILE"
            usage
            ;;
    esac

    generate_secret_key
    COMPOSE_PROFILES="$COMPOSE_PROFILES" docker compose up -d
    echo "Server stack deployed with profile $PROFILE. Access at http://localhost:3000"
    if [[ "$PROFILE" == *"monitoring"* ]]; then
        echo "Monitoring: Grafana at http://localhost:3001, Prometheus at http://localhost:9090"
    fi
}

stop() {
    echo "Stopping server stack..."
    docker compose down
}

status() {
    echo "Server stack status:"
    docker compose ps
}

logs() {
    docker compose logs -f
}

update() {
    echo "Updating server stack..."
    docker compose pull
    docker compose up -d
}

pull_model() {
    MODEL="$1"
    TARGET="${2:-cpu}"

    if [ -z "$MODEL" ]; then
        echo "Error: Please specify a model name"
        exit 1
    fi

    case "$TARGET" in
        cpu)
            SERVICE="ollama-cpu"
            ;;
        gpu)
            echo "Error: GPU models must be pulled on the GPU worker machine"
            exit 1
            ;;
        *)
            echo "Error: Invalid target. Use 'cpu' or 'gpu'"
            exit 1
            ;;
    esac

    echo "Pulling model $MODEL to $TARGET Ollama"
    timeout 600 docker compose exec "$SERVICE" ollama pull "$MODEL"
}

list_models() {
    echo "CPU models:"
    docker compose exec ollama-cpu ollama list 2>/dev/null || echo "CPU Ollama not running"
}

check_gpu() {
    echo "Checking GPU worker connectivity..."
    GPU_IP="${GPU_IP:-192.168.1.99}"
    if curl -s "http://$GPU_IP:11434/api/tags" > /dev/null; then
        echo "✓ GPU worker responding at $GPU_IP:11434"
        echo "Available GPU models:"
        curl -s "http://$GPU_IP:11434/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "No models listed"
    else
        echo "✗ GPU worker not responding at $GPU_IP:11434"
    fi
}

benchmark() {
    echo "Benchmarking server CPU Ollama..."

    # Simple inference test
    echo "Running inference test..."
    timeout 120 docker compose exec ollama-cpu ollama run llama3.2 "Write a short summary of artificial intelligence." 2>/dev/null | head -10
    if [ $? -eq 0 ]; then
        echo "✓ CPU Inference successful"
    else
        echo "✗ CPU Inference failed or timed out"
    fi
}

check_dependencies

case "$1" in
    deploy)
        deploy "$2"
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
        pull_model "$2" "$3"
        ;;
    list-models)
        list_models
        ;;
    check-gpu)
        check_gpu
        ;;
    benchmark)
        benchmark
        ;;
    *)
        usage
        ;;
esac