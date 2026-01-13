#!/usr/bin/env bash
# comfyui-setup.sh - Setup ComfyUI workflows and models
# Downloads required models and validates workflow configurations
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_ROOT/config"
WORKFLOWS_DIR="$CONFIG_DIR/comfyui-workflows"
MANIFEST_FILE="$WORKFLOWS_DIR/manifest.yml"

# Default paths (can be overridden via environment)
COMFYUI_MODELS_PATH="${COMFYUI_MODELS_PATH:-/data/comfyui/models}"
GPU_WORKER_HOST="${GPU_WORKER_HOST:-192.168.1.99}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"

# Colors
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

# =============================================================================
# Workflow Functions
# =============================================================================

list_workflows() {
  log_header "Available ComfyUI Workflows"

  if [[ ! -f "$MANIFEST_FILE" ]]; then
    log_error "Manifest file not found: $MANIFEST_FILE"
    return 1
  fi

  if command -v yq &>/dev/null; then
    echo ""
    printf "%-25s %-35s %s\n" "ID" "NAME" "TAGS"
    printf "%-25s %-35s %s\n" "---" "----" "----"
    yq -r '.workflows | to_entries[] | "\(.key)|\(.value.name)|\(.value.tags | join(", "))"' "$MANIFEST_FILE" | while IFS='|' read -r id name tags; do
      printf "%-25s %-35s %s\n" "$id" "$name" "$tags"
    done
  else
    log_warn "yq not installed - showing raw workflow files"
    ls -1 "$WORKFLOWS_DIR"/*.json 2>/dev/null | xargs -I{} basename {} .json
  fi
}

show_workflow_info() {
  local workflow_id="$1"

  if [[ ! -f "$MANIFEST_FILE" ]]; then
    log_error "Manifest file not found"
    return 1
  fi

  if ! command -v yq &>/dev/null; then
    log_error "yq required for workflow info"
    return 1
  fi

  local workflow_data
  workflow_data=$(yq -r ".workflows[\"$workflow_id\"]" "$MANIFEST_FILE")

  if [[ "$workflow_data" == "null" ]]; then
    log_error "Workflow not found: $workflow_id"
    return 1
  fi

  log_header "Workflow: $workflow_id"
  yq -r ".workflows[\"$workflow_id\"] | \"
Name: \(.name)
Description: \(.description)
Priority: \(.priority)
Tags: \(.tags | join(\", \"))
VRAM Required: \(.requirements.vram_min_gb)GB
Models:\"" "$MANIFEST_FILE"

  yq -r ".workflows[\"$workflow_id\"].requirements.models[]? | \"  - \(.name) (\(.type))\"" "$MANIFEST_FILE"
}

check_model_exists() {
  local model_path="$1"
  local model_name="$2"
  local full_path="${COMFYUI_MODELS_PATH}/${model_path}${model_name}"

  if [[ -f "$full_path" ]]; then
    return 0
  fi
  return 1
}

download_model() {
  local url="$1"
  local dest="$2"
  local name="$3"

  log_info "Downloading: $name"
  log_info "  URL: $url"
  log_info "  Destination: $dest"

  mkdir -p "$(dirname "$dest")"

  if command -v aria2c &>/dev/null; then
    aria2c -x 16 -s 16 -d "$(dirname "$dest")" -o "$(basename "$dest")" "$url"
  elif command -v wget &>/dev/null; then
    wget --progress=bar:force -O "$dest" "$url"
  elif command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$dest" "$url"
  else
    log_error "No download tool available (aria2c, wget, or curl required)"
    return 1
  fi

  if [[ -f "$dest" ]]; then
    log_success "Downloaded: $name"
  else
    log_error "Failed to download: $name"
    return 1
  fi
}

setup_workflow() {
  local workflow_id="$1"
  local force="${2:-false}"

  if [[ ! -f "$MANIFEST_FILE" ]]; then
    log_error "Manifest file not found"
    return 1
  fi

  if ! command -v yq &>/dev/null; then
    log_error "yq required for workflow setup"
    return 1
  fi

  local workflow_data
  workflow_data=$(yq -r ".workflows[\"$workflow_id\"]" "$MANIFEST_FILE")

  if [[ "$workflow_data" == "null" ]]; then
    log_error "Workflow not found: $workflow_id"
    return 1
  fi

  local workflow_name
  workflow_name=$(yq -r ".workflows[\"$workflow_id\"].name" "$MANIFEST_FILE")
  log_header "Setting up: $workflow_name"

  # Check and download each required model
  local models_json
  models_json=$(yq -r ".workflows[\"$workflow_id\"].requirements.models // []" "$MANIFEST_FILE")

  if [[ "$models_json" == "[]" ]]; then
    log_info "No models required for this workflow"
    return 0
  fi

  yq -r ".workflows[\"$workflow_id\"].requirements.models[] | \"\(.name)|\(.path)|\(.url // \"\")|\(.size_gb // 0)\"" "$MANIFEST_FILE" | while IFS='|' read -r name path url size; do
    local full_path="${COMFYUI_MODELS_PATH}/${path}${name}"

    if [[ -f "$full_path" ]] && [[ "$force" != "true" ]]; then
      log_success "Model exists: $name"
    elif [[ -n "$url" ]]; then
      log_info "Model missing: $name (${size}GB)"
      read -rp "Download $name? [y/N] " answer
      if [[ "$answer" =~ ^[Yy]$ ]]; then
        download_model "$url" "$full_path" "$name"
      else
        log_warn "Skipped: $name"
      fi
    else
      log_warn "Model missing (no URL): $name"
      log_info "  Expected path: $full_path"
    fi
  done
}

setup_all_required() {
  log_header "Setting up required workflows"

  if ! command -v yq &>/dev/null; then
    log_error "yq required for workflow setup"
    return 1
  fi

  yq -r '.workflows | to_entries[] | select(.value.priority == "required") | .key' "$MANIFEST_FILE" | while read -r workflow_id; do
    setup_workflow "$workflow_id"
  done
}

validate_comfyui() {
  log_header "Validating ComfyUI Setup"

  # Check API connectivity
  local api_url="http://${GPU_WORKER_HOST}:${COMFYUI_PORT}"
  if curl -s --connect-timeout 5 "${api_url}/system_stats" &>/dev/null; then
    log_success "ComfyUI API: $api_url"
  else
    log_error "ComfyUI API not reachable: $api_url"
    return 1
  fi

  # Check models directory
  if [[ -d "$COMFYUI_MODELS_PATH" ]]; then
    log_success "Models directory: $COMFYUI_MODELS_PATH"
  else
    log_warn "Models directory not found: $COMFYUI_MODELS_PATH"
  fi

  # Count installed models
  local checkpoint_count=0
  local upscale_count=0

  if [[ -d "${COMFYUI_MODELS_PATH}/checkpoints" ]]; then
    checkpoint_count=$(find "${COMFYUI_MODELS_PATH}/checkpoints" -name "*.safetensors" -o -name "*.ckpt" 2>/dev/null | wc -l)
  fi
  if [[ -d "${COMFYUI_MODELS_PATH}/upscale_models" ]]; then
    upscale_count=$(find "${COMFYUI_MODELS_PATH}/upscale_models" -name "*.pth" 2>/dev/null | wc -l)
  fi

  echo ""
  echo "Installed Models:"
  echo "  Checkpoints: $checkpoint_count"
  echo "  Upscale Models: $upscale_count"
}

export_workflow() {
  local workflow_id="$1"
  local output="${2:-}"

  local workflow_file="${WORKFLOWS_DIR}/${workflow_id}.json"

  if [[ ! -f "$workflow_file" ]]; then
    # Try from manifest
    if command -v yq &>/dev/null && [[ -f "$MANIFEST_FILE" ]]; then
      local file
      file=$(yq -r ".workflows[\"$workflow_id\"].file // \"\"" "$MANIFEST_FILE")
      if [[ -n "$file" ]]; then
        workflow_file="${WORKFLOWS_DIR}/${file}"
      fi
    fi
  fi

  if [[ ! -f "$workflow_file" ]]; then
    log_error "Workflow file not found: $workflow_id"
    return 1
  fi

  # Remove _meta section for API export
  if command -v jq &>/dev/null; then
    local exported
    exported=$(jq 'del(._meta)' "$workflow_file")

    if [[ -n "$output" ]]; then
      echo "$exported" > "$output"
      log_success "Exported to: $output"
    else
      echo "$exported"
    fi
  else
    log_warn "jq not installed - exporting raw file"
    cat "$workflow_file"
  fi
}

# =============================================================================
# Usage
# =============================================================================
usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  list                    List all available workflows
  info <workflow-id>      Show detailed workflow information
  setup <workflow-id>     Setup a specific workflow (download models)
  setup-required          Setup all required workflows
  validate                Validate ComfyUI setup and connectivity
  export <workflow-id>    Export workflow JSON for API use

Environment Variables:
  COMFYUI_MODELS_PATH   Path to ComfyUI models (default: /data/comfyui/models)
  GPU_WORKER_HOST       GPU worker IP (default: 192.168.1.99)
  COMFYUI_PORT          ComfyUI port (default: 8188)

Examples:
  $(basename "$0") list
  $(basename "$0") info txt2img-sdxl
  $(basename "$0") setup txt2img-sdxl
  $(basename "$0") setup-required
  $(basename "$0") validate
  $(basename "$0") export txt2img-sdxl > workflow.json

EOF
}

# =============================================================================
# Main
# =============================================================================
main() {
  local command="${1:-help}"
  shift || true

  case "$command" in
    list)
      list_workflows
      ;;
    info)
      if [[ -z "${1:-}" ]]; then
        log_error "Workflow ID required"
        usage
        exit 1
      fi
      show_workflow_info "$1"
      ;;
    setup)
      if [[ -z "${1:-}" ]]; then
        log_error "Workflow ID required"
        usage
        exit 1
      fi
      setup_workflow "$1" "${2:-false}"
      ;;
    setup-required)
      setup_all_required
      ;;
    validate)
      validate_comfyui
      ;;
    export)
      if [[ -z "${1:-}" ]]; then
        log_error "Workflow ID required"
        usage
        exit 1
      fi
      export_workflow "$1" "${2:-}"
      ;;
    help|--help|-h)
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
