#!/usr/bin/env bash
# deploy-full-stack.sh - Deploy complete self-hosted AI stack to remote hosts
# Handles both server and GPU worker deployment with validation
set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default hosts
SERVER_HOST="${SERVER_HOST:-192.168.1.170}"
SERVER_USER="${SERVER_USER:-kang}"
GPU_WORKER_HOST="${GPU_WORKER_HOST:-192.168.1.99}"
GPU_WORKER_USER="${GPU_WORKER_USER:-kang}"

# Remote paths
REMOTE_PROJECT_PATH="${REMOTE_PROJECT_PATH:-/home/kang/self-hosted-ai}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] COMMAND

Deploy the self-hosted AI stack to remote hosts.

Commands:
    all             Deploy to both server and GPU worker
    server          Deploy only to server node
    gpu-worker      Deploy only to GPU worker node
    sync            Sync code to both nodes (no restart)
    status          Check status of all services
    logs            View logs from services
    stop            Stop all services

Options:
    -h, --help          Show this help message
    --server-host HOST  Server host (default: ${SERVER_HOST})
    --gpu-host HOST     GPU worker host (default: ${GPU_WORKER_HOST})
    --profile PROFILE   Docker compose profile (default: basic)
    -y, --yes           Skip confirmation prompts

Environment Variables:
    SERVER_HOST         Server IP address
    GPU_WORKER_HOST     GPU worker IP address

Examples:
    $(basename "$0") all                    # Deploy everything
    $(basename "$0") server --profile full  # Deploy server with full profile
    $(basename "$0") sync                   # Just sync code
    $(basename "$0") status                 # Check all services
EOF
    exit 0
}

# Check SSH connectivity
check_ssh() {
    local host="$1"
    local user="$2"
    
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${user}@${host}" "echo ok" &>/dev/null; then
        log_error "Cannot connect to ${user}@${host}"
        return 1
    fi
    return 0
}

# Execute command on remote host (always uses bash to avoid nushell issues)
remote_exec() {
    local host="$1"
    local user="$2"
    shift 2
    
    ssh -o ConnectTimeout=10 "${user}@${host}" bash << REMOTECMD
$*
REMOTECMD
}

# Sync project to remote host
sync_to_host() {
    local host="$1"
    local user="$2"
    
    log_step "Syncing project to ${user}@${host}..."
    
    # Create remote directory if needed
    remote_exec "$host" "$user" "mkdir -p ${REMOTE_PROJECT_PATH}"
    
    # Sync project (excluding build artifacts and local data)
    rsync -avz --progress \
        --exclude '.git' \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude 'node_modules' \
        --exclude 'target' \
        --exclude '.env' \
        --exclude 'data/' \
        "${PROJECT_ROOT}/" "${user}@${host}:${REMOTE_PROJECT_PATH}/"
    
    log_success "Synced to ${host}"
}

# Deploy server services
deploy_server() {
    local profile="${1:-basic}"
    
    log_step "Deploying server services with profile: ${profile}"
    
    # Check SSH
    if ! check_ssh "$SERVER_HOST" "$SERVER_USER"; then
        return 1
    fi
    
    # Sync code
    sync_to_host "$SERVER_HOST" "$SERVER_USER"
    
    # Create data directories (only chown our specific dirs, not all of /data)
    remote_exec "$SERVER_HOST" "$SERVER_USER" "
        sudo mkdir -p /data/{open-webui,ollama-cpu,redis,prometheus,grafana,ingest,documents,searxng}
        sudo chown -R \$USER:\$USER /data/open-webui /data/ollama-cpu /data/redis /data/prometheus /data/grafana /data/ingest /data/documents /data/searxng
    "
    
    # Copy SearXNG config
    remote_exec "$SERVER_HOST" "$SERVER_USER" "
        mkdir -p /data/searxng
        cp -r ${REMOTE_PROJECT_PATH}/config/searxng/* /data/searxng/ 2>/dev/null || true
    "
    
    # Setup .env if not exists
    remote_exec "$SERVER_HOST" "$SERVER_USER" "
        cd ${REMOTE_PROJECT_PATH}/server
        if [ ! -f .env ]; then
            cp .env.example .env 2>/dev/null || cat > .env << 'ENVFILE'
WEBUI_PORT=3000
OLLAMA_PORT=11434
REDIS_PORT=6379
SEARXNG_PORT=8080
DATA_PATH=/data
GPU_WORKER_HOST=${GPU_WORKER_HOST}
WEBUI_SECRET_KEY=\$(openssl rand -hex 32)
WEBUI_NAME=Self-Hosted AI
ENABLE_SIGNUP=true
ENABLE_RAG_WEB_SEARCH=true
SEARXNG_SECRET_KEY=\$(openssl rand -hex 32)
ENVFILE
        fi
    "
    
    # Pull images and start services
    remote_exec "$SERVER_HOST" "$SERVER_USER" "
        cd ${REMOTE_PROJECT_PATH}/server
        docker compose pull
        docker compose --profile ${profile} up -d
    "
    
    log_success "Server deployed successfully"
}

# Deploy GPU worker services
deploy_gpu_worker() {
    log_step "Deploying GPU worker services"
    
    # Check SSH
    if ! check_ssh "$GPU_WORKER_HOST" "$GPU_WORKER_USER"; then
        return 1
    fi
    
    # Verify NVIDIA driver
    log_info "Checking NVIDIA GPU..."
    if ! remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "nvidia-smi" &>/dev/null; then
        log_error "NVIDIA GPU not detected on ${GPU_WORKER_HOST}"
        log_info "Please install NVIDIA drivers and nvidia-container-toolkit"
        return 1
    fi
    
    # Sync code
    sync_to_host "$GPU_WORKER_HOST" "$GPU_WORKER_USER"
    
    # Create data directories (only chown our specific dirs, not all of /data)
    remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
        sudo mkdir -p /data/{ollama-gpu,comfyui,automatic1111,models,whisper}
        sudo mkdir -p /data/comfyui/{models,output,input,custom_nodes,workflows}
        sudo mkdir -p /data/models/{checkpoints,loras,vae,embeddings,upscale_models}
        sudo chown -R \$USER:\$USER /data/ollama-gpu /data/comfyui /data/automatic1111 /data/models /data/whisper
    "
    
    # Copy workflow configs
    remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
        cp -r ${REMOTE_PROJECT_PATH}/config/comfyui-workflows/* /data/comfyui/workflows/ 2>/dev/null || true
    "
    
    # Setup .env if not exists
    remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
        cd ${REMOTE_PROJECT_PATH}/gpu-worker
        if [ ! -f .env ]; then
            cat > .env << 'ENVFILE'
OLLAMA_PORT=11434
COMFYUI_PORT=8188
AUTOMATIC1111_PORT=7860
WHISPER_PORT=9000
GPU_MANAGER_PORT=8100
DATA_PATH=/data
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=30m
OLLAMA_GPU_LAYERS=99
WHISPER_MODEL=large-v3
ENVFILE
        fi
    "
    
    # Build and start services
    remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
        cd ${REMOTE_PROJECT_PATH}/gpu-worker
        docker compose pull
        docker compose build --no-cache gpu-manager 2>/dev/null || true
        docker compose up -d
    "
    
    log_success "GPU worker deployed successfully"
}

# Check status of all services
check_status() {
    log_step "Checking service status..."
    
    echo
    log_info "=== Server Node (${SERVER_HOST}) ==="
    
    if check_ssh "$SERVER_HOST" "$SERVER_USER"; then
        remote_exec "$SERVER_HOST" "$SERVER_USER" "
            cd ${REMOTE_PROJECT_PATH}/server 2>/dev/null && docker compose ps 2>/dev/null || echo 'Not deployed'
        "
        
        echo
        log_info "Health checks:"
        for endpoint in "3000" "11434/api/tags" "8080/healthz"; do
            port="${endpoint%%/*}"
            path="${endpoint#*/}"
            [[ "$path" == "$port" ]] && path=""
            status=$(curl -s -o /dev/null -w "%{http_code}" "http://${SERVER_HOST}:${port}/${path}" 2>/dev/null || echo "000")
            if [[ "$status" == "200" ]]; then
                echo -e "  ${GREEN}✓${NC} :${port} - OK"
            else
                echo -e "  ${RED}✗${NC} :${port} - ${status}"
            fi
        done
    else
        echo -e "  ${RED}Cannot connect${NC}"
    fi
    
    echo
    log_info "=== GPU Worker Node (${GPU_WORKER_HOST}) ==="
    
    if check_ssh "$GPU_WORKER_HOST" "$GPU_WORKER_USER"; then
        remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
            cd ${REMOTE_PROJECT_PATH}/gpu-worker 2>/dev/null && docker compose ps 2>/dev/null || echo 'Not deployed'
        "
        
        echo
        log_info "Health checks:"
        for endpoint in "11434/api/tags" "8188/system_stats" "7860" "9000/health" "8100/health"; do
            port="${endpoint%%/*}"
            path="${endpoint#*/}"
            [[ "$path" == "$port" ]] && path=""
            status=$(curl -s -o /dev/null -w "%{http_code}" "http://${GPU_WORKER_HOST}:${port}/${path}" 2>/dev/null || echo "000")
            if [[ "$status" == "200" ]]; then
                echo -e "  ${GREEN}✓${NC} :${port} - OK"
            else
                echo -e "  ${RED}✗${NC} :${port} - ${status}"
            fi
        done
        
        echo
        log_info "GPU Status:"
        remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader" 2>/dev/null || echo "  GPU info unavailable"
    else
        echo -e "  ${RED}Cannot connect${NC}"
    fi
}

# View logs
view_logs() {
    local service="${1:-}"
    local host="${2:-server}"
    
    if [[ "$host" == "server" ]]; then
        remote_exec "$SERVER_HOST" "$SERVER_USER" "
            cd ${REMOTE_PROJECT_PATH}/server
            docker compose logs -f ${service} --tail=100
        "
    else
        remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
            cd ${REMOTE_PROJECT_PATH}/gpu-worker
            docker compose logs -f ${service} --tail=100
        "
    fi
}

# Stop all services
stop_all() {
    log_step "Stopping all services..."
    
    if check_ssh "$SERVER_HOST" "$SERVER_USER"; then
        log_info "Stopping server services..."
        remote_exec "$SERVER_HOST" "$SERVER_USER" "
            cd ${REMOTE_PROJECT_PATH}/server 2>/dev/null && docker compose down 2>/dev/null || true
        "
    fi
    
    if check_ssh "$GPU_WORKER_HOST" "$GPU_WORKER_USER"; then
        log_info "Stopping GPU worker services..."
        remote_exec "$GPU_WORKER_HOST" "$GPU_WORKER_USER" "
            cd ${REMOTE_PROJECT_PATH}/gpu-worker 2>/dev/null && docker compose down 2>/dev/null || true
        "
    fi
    
    log_success "All services stopped"
}

# =============================================================================
# Main
# =============================================================================
main() {
    local profile="basic"
    local skip_confirm=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                ;;
            --server-host)
                SERVER_HOST="$2"
                shift 2
                ;;
            --gpu-host)
                GPU_WORKER_HOST="$2"
                shift 2
                ;;
            --profile)
                profile="$2"
                shift 2
                ;;
            -y|--yes)
                skip_confirm=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    
    local command="${1:-all}"
    shift || true
    
    case "$command" in
        all)
            log_step "Deploying full stack..."
            echo
            log_info "Server:     ${SERVER_USER}@${SERVER_HOST}"
            log_info "GPU Worker: ${GPU_WORKER_USER}@${GPU_WORKER_HOST}"
            log_info "Profile:    ${profile}"
            echo
            
            if [[ "$skip_confirm" != "true" ]]; then
                read -p "Continue? [y/N] " -n 1 -r
                echo
                [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
            fi
            
            deploy_server "$profile"
            echo
            deploy_gpu_worker
            echo
            
            log_success "Full stack deployed!"
            echo
            check_status
            ;;
        server)
            deploy_server "$profile"
            ;;
        gpu-worker)
            deploy_gpu_worker
            ;;
        sync)
            sync_to_host "$SERVER_HOST" "$SERVER_USER"
            sync_to_host "$GPU_WORKER_HOST" "$GPU_WORKER_USER"
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs "$@"
            ;;
        stop)
            stop_all
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            ;;
    esac
}

main "$@"
