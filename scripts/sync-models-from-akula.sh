#!/usr/bin/env bash
# sync-models-from-akula.sh - Sync Ollama models from akula-prime to homelab
set -euo pipefail

SOURCE_HOST="${1:-192.168.1.99}"
SOURCE_PORT="${2:-11435}"
DEST_HOST="${3:-192.168.1.170}"
DEST_PORT="${4:-11434}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

# Get list of models from source
get_source_models() {
  log_info "Fetching models from akula-prime ($SOURCE_HOST:$SOURCE_PORT)..."
  curl -s "http://${SOURCE_HOST}:${SOURCE_PORT}/api/tags" | jq -r '.models[]? | .name' | sort
}

# Get list of models from destination
get_dest_models() {
  curl -s "http://${DEST_HOST}:${DEST_PORT}/api/tags" 2>/dev/null | jq -r '.models[]? | .name' | sort
}

# Pull model to destination
pull_model() {
  local model="$1"
  log_info "Pulling model: $model"
  
  # Use akula-prime as registry
  curl -X POST "http://${DEST_HOST}:${DEST_PORT}/api/pull" \
    -d "{\"name\": \"$model\", \"stream\": false}" \
    -H "Content-Type: application/json" \
    --max-time 600 2>&1 | jq -r '.status // empty' || true
}

# Copy model via export/import (more reliable for cross-host)
copy_model() {
  local model="$1"
  local model_safe="${model//[^a-zA-Z0-9._-]/_}"
  
  log_info "Copying model via export: $model"
  
  # Export from source
  log_info "  Exporting from akula-prime..."
  ssh kang@${SOURCE_HOST} "docker exec ollama-gpu-worker ollama show $model --modelfile" > "/tmp/${model_safe}.modelfile" 2>/dev/null || {
    log_warn "  Could not export modelfile for $model, trying direct pull..."
    return 1
  }
  
  # Check if model exists on destination
  if get_dest_models | grep -qx "$model"; then
    log_warn "  Model already exists on destination: $model"
    return 0
  fi
  
  # Pull to destination
  log_info "  Pulling to homelab..."
  docker exec ollama-cpu-server ollama pull "$model" || {
    log_error "  Failed to pull $model"
    return 1
  }
  
  log_success "  Copied: $model"
}

main() {
  log_header "Ollama Model Sync: akula-prime → homelab"
  
  echo ""
  echo "Source:      $SOURCE_HOST:$SOURCE_PORT (akula-prime/GPU worker)"
  echo "Destination: $DEST_HOST:$DEST_PORT (homelab server)"
  echo ""
  
  # Get models from both hosts
  local source_models
  source_models=$(get_source_models)
  
  if [[ -z "$source_models" ]]; then
    log_error "No models found on source or cannot connect"
    exit 1
  fi
  
  local dest_models
  dest_models=$(get_dest_models)
  
  # Find models to sync
  local to_sync=()
  while IFS= read -r model; do
    if ! echo "$dest_models" | grep -qx "$model"; then
      to_sync+=("$model")
    fi
  done <<< "$source_models"
  
  if [[ ${#to_sync[@]} -eq 0 ]]; then
    log_success "All models already synced!"
    exit 0
  fi
  
  log_header "Models to Sync (${#to_sync[@]})"
  printf '%s\n' "${to_sync[@]}" | sed 's/^/  • /'
  echo ""
  
  read -rp "Proceed with sync? [y/N] " answer
  if [[ ! "$answer" =~ ^[Yy]$ ]]; then
    log_info "Sync cancelled"
    exit 0
  fi
  
  # Sync each model
  local success=0
  local failed=0
  
  for model in "${to_sync[@]}"; do
    log_header "Syncing: $model"
    
    if docker exec ollama-cpu-server ollama pull "$model" 2>&1 | grep -q "success"; then
      ((success++))
      log_success "Synced: $model"
    else
      ((failed++))
      log_error "Failed: $model"
    fi
    
    echo ""
  done
  
  log_header "Sync Complete"
  echo ""
  echo "  Success: $success"
  echo "  Failed:  $failed"
  echo ""
  
  # Show final status
  log_info "Current models on homelab:"
  get_dest_models | sed 's/^/  • /'
}

main "$@"
