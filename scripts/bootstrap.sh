#!/usr/bin/env bash
# bootstrap.sh - Initialize self-hosted-ai stack
# Installs pre-commit hooks, verifies connectivity, syncs models
set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"
MANIFEST_FILE="$CONFIG_DIR/models-manifest.yml"

# Default hosts (can be overridden via environment)
GPU_WORKER_HOST="${GPU_WORKER_HOST:-192.168.1.99}"
GPU_WORKER_PORT="${GPU_WORKER_PORT:-11434}"
CPU_SERVER_HOST="${CPU_SERVER_HOST:-192.168.1.170}"
CPU_SERVER_PORT="${CPU_SERVER_PORT:-11434}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_command() {
  if ! command -v "$1" &>/dev/null; then
    log_error "Required command not found: $1"
    return 1
  fi
}

# Check if Ollama endpoint is reachable
check_ollama() {
  local host="$1"
  local port="$2"
  local url="http://${host}:${port}"

  if curl -s --connect-timeout 5 "${url}/" &>/dev/null; then
    log_success "Ollama reachable at ${url}"
    return 0
  else
    log_error "Cannot reach Ollama at ${url}"
    return 1
  fi
}

# Get list of models on an Ollama instance
get_models() {
  local host="$1"
  local port="$2"
  curl -s "http://${host}:${port}/api/tags" 2>/dev/null | jq -r '.models[].name // empty' 2>/dev/null || echo ""
}

# Check if a specific model exists on Ollama instance
model_exists() {
  local host="$1"
  local port="$2"
  local model="$3"
  local models

  models=$(get_models "$host" "$port")

  # Check exact match or base name match (model:tag vs model:latest)
  local base_model="${model%%:*}"
  if echo "$models" | grep -qE "^${model}$|^${base_model}:"; then
    return 0
  fi
  return 1
}

# Pull a model to an Ollama instance
pull_model() {
  local host="$1"
  local port="$2"
  local model="$3"

  log_info "Pulling ${model} to ${host}:${port}..."
  if curl -s "http://${host}:${port}/api/pull" -d "{\"name\": \"${model}\"}" | while read -r line; do
    local status
    status=$(echo "$line" | jq -r '.status // empty' 2>/dev/null)
    if [[ -n "$status" ]]; then
      printf "\r  %s" "$status"
    fi
  done; then
    echo ""
    log_success "Pulled ${model}"
    return 0
  else
    echo ""
    log_error "Failed to pull ${model}"
    return 1
  fi
}

# Parse models from manifest for a given target (gpu_worker or cpu_server)
get_manifest_models() {
  local target="$1"
  local priority="${2:-all}" # all, required, optional

  if [[ ! -f "$MANIFEST_FILE" ]]; then
    log_error "Manifest file not found: $MANIFEST_FILE"
    return 1
  fi

  # Use yq if available, otherwise fall back to grep/awk
  if command -v yq &>/dev/null; then
    if [[ "$priority" == "all" ]]; then
      yq -r ".${target}.models[].name" "$MANIFEST_FILE" 2>/dev/null
    else
      yq -r ".${target}.models[] | select(.priority == \"${priority}\") | .name" "$MANIFEST_FILE" 2>/dev/null
    fi
  else
    # Fallback: simple grep for model names under target section
    local in_target=false
    local in_models=false
    while IFS= read -r line; do
      if [[ "$line" =~ ^${target}: ]]; then
        in_target=true
        continue
      fi
      if [[ "$in_target" == true && "$line" =~ ^[a-z_]+: && ! "$line" =~ ^[[:space:]] ]]; then
        in_target=false
        continue
      fi
      if [[ "$in_target" == true && "$line" =~ models: ]]; then
        in_models=true
        continue
      fi
      if [[ "$in_models" == true && "$line" =~ ^[[:space:]]*-[[:space:]]*name:[[:space:]]*(.+) ]]; then
        echo "${BASH_REMATCH[1]}"
      fi
    done <"$MANIFEST_FILE"
  fi
}

# =============================================================================
# Pre-commit Setup
# =============================================================================
setup_precommit() {
  log_info "Setting up pre-commit hooks..."

  if ! check_command pre-commit; then
    log_warn "pre-commit not installed. Installing via pip..."
    pip install --user pre-commit || {
      log_error "Failed to install pre-commit"
      return 1
    }
  fi

  cd "$PROJECT_ROOT"

  if [[ -f ".pre-commit-config.yaml" ]]; then
    pre-commit install --install-hooks
    pre-commit install --hook-type commit-msg
    log_success "Pre-commit hooks installed"
  else
    log_warn "No .pre-commit-config.yaml found"
  fi
}

# =============================================================================
# Model Sync
# =============================================================================
sync_models() {
  local mode="${1:-interactive}" # interactive or all
  local target="${2:-both}"      # gpu, cpu, or both

  log_info "Syncing models (mode: ${mode}, target: ${target})..."

  # Check connectivity first
  local gpu_ok=false
  local cpu_ok=false

  if [[ "$target" == "both" || "$target" == "gpu" ]]; then
    if check_ollama "$GPU_WORKER_HOST" "$GPU_WORKER_PORT"; then
      gpu_ok=true
    fi
  fi

  if [[ "$target" == "both" || "$target" == "cpu" ]]; then
    if check_ollama "$CPU_SERVER_HOST" "$CPU_SERVER_PORT"; then
      cpu_ok=true
    fi
  fi

  # Sync GPU worker models
  if [[ "$gpu_ok" == true ]]; then
    log_info "Checking GPU worker models..."
    local gpu_models
    gpu_models=$(get_manifest_models "gpu_worker")

    while IFS= read -r model; do
      [[ -z "$model" ]] && continue

      if model_exists "$GPU_WORKER_HOST" "$GPU_WORKER_PORT" "$model"; then
        log_success "Model exists: ${model} (GPU)"
      else
        if [[ "$mode" == "all" ]]; then
          pull_model "$GPU_WORKER_HOST" "$GPU_WORKER_PORT" "$model"
        else
          read -rp "Pull ${model} to GPU worker? [y/N] " answer
          if [[ "$answer" =~ ^[Yy]$ ]]; then
            pull_model "$GPU_WORKER_HOST" "$GPU_WORKER_PORT" "$model"
          else
            log_warn "Skipped: ${model}"
          fi
        fi
      fi
    done <<<"$gpu_models"
  fi

  # Sync CPU server models
  if [[ "$cpu_ok" == true ]]; then
    log_info "Checking CPU server models..."
    local cpu_models
    cpu_models=$(get_manifest_models "cpu_server")

    while IFS= read -r model; do
      [[ -z "$model" ]] && continue

      if model_exists "$CPU_SERVER_HOST" "$CPU_SERVER_PORT" "$model"; then
        log_success "Model exists: ${model} (CPU)"
      else
        if [[ "$mode" == "all" ]]; then
          pull_model "$CPU_SERVER_HOST" "$CPU_SERVER_PORT" "$model"
        else
          read -rp "Pull ${model} to CPU server? [y/N] " answer
          if [[ "$answer" =~ ^[Yy]$ ]]; then
            pull_model "$CPU_SERVER_HOST" "$CPU_SERVER_PORT" "$model"
          else
            log_warn "Skipped: ${model}"
          fi
        fi
      fi
    done <<<"$cpu_models"
  fi
}

# =============================================================================
# Status Check
# =============================================================================
show_status() {
  log_info "=== Self-Hosted AI Stack Status ==="
  echo ""

  # GPU Worker
  echo -e "${BLUE}GPU Worker (${GPU_WORKER_HOST}:${GPU_WORKER_PORT})${NC}"
  if check_ollama "$GPU_WORKER_HOST" "$GPU_WORKER_PORT" 2>/dev/null; then
    echo "  Models:"
    get_models "$GPU_WORKER_HOST" "$GPU_WORKER_PORT" | while read -r model; do
      echo "    - $model"
    done
  fi
  echo ""

  # CPU Server
  echo -e "${BLUE}CPU Server (${CPU_SERVER_HOST}:${CPU_SERVER_PORT})${NC}"
  if check_ollama "$CPU_SERVER_HOST" "$CPU_SERVER_PORT" 2>/dev/null; then
    echo "  Models:"
    get_models "$CPU_SERVER_HOST" "$CPU_SERVER_PORT" | while read -r model; do
      echo "    - $model"
    done
  fi
  echo ""

  # Open WebUI
  local webui_url="http://${CPU_SERVER_HOST}:3001"
  echo -e "${BLUE}Open WebUI${NC}"
  if curl -s --connect-timeout 5 "${webui_url}/health" &>/dev/null; then
    log_success "Open WebUI: ${webui_url}"
  else
    log_error "Open WebUI not reachable: ${webui_url}"
  fi
}

# =============================================================================
# Usage
# =============================================================================
usage() {
  cat <<EOF
Usage: $(basename "$0") [command] [options]

Commands:
  setup       Install pre-commit hooks and validate environment
  sync        Sync models from manifest (interactive by default)
  status      Show stack status and available models
  help        Show this help message

Options:
  --all       Sync all missing models without prompting
  --gpu       Only sync GPU worker models
  --cpu       Only sync CPU server models

Environment Variables:
  GPU_WORKER_HOST   GPU worker IP (default: 192.168.1.99)
  GPU_WORKER_PORT   GPU worker port (default: 11434)
  CPU_SERVER_HOST   CPU server IP (default: 192.168.1.170)
  CPU_SERVER_PORT   CPU server port (default: 11434)

Examples:
  $(basename "$0") setup              # Install pre-commit hooks
  $(basename "$0") sync               # Interactive model sync
  $(basename "$0") sync --all         # Sync all missing models
  $(basename "$0") sync --all --gpu   # Sync only GPU models
  $(basename "$0") status             # Show current status

EOF
}

# =============================================================================
# Main
# =============================================================================
main() {
  local command="${1:-help}"
  shift || true

  # Parse options
  local mode="interactive"
  local target="both"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all)
        mode="all"
        shift
        ;;
      --gpu)
        target="gpu"
        shift
        ;;
      --cpu)
        target="cpu"
        shift
        ;;
      *)
        log_error "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
  done

  case "$command" in
    setup)
      setup_precommit
      ;;
    sync)
      sync_models "$mode" "$target"
      ;;
    status)
      show_status
      ;;
    help | --help | -h)
      usage
      ;;
    *)
      log_error "Unknown command: $command"
      usage
      exit 1
      ;;
  esac
}

main "$@"
