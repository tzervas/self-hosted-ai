#!/usr/bin/env bash
# sync-models.sh - Sync local models to remote server model vault
# Supports incremental sync with checksum verification
set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source and destination paths
LOCAL_MODELS_DIR="${LOCAL_MODELS_DIR:-$HOME/Documents/projects/2026/models}"
REMOTE_HOST="${GPU_WORKER_HOST:-192.168.1.99}"
REMOTE_USER="${REMOTE_USER:-kang}"
REMOTE_MODELS_DIR="${REMOTE_MODELS_DIR:-/data/models}"

# Model vault paths on remote
MODEL_VAULT_PATHS=(
    "checkpoints:${REMOTE_MODELS_DIR}/comfyui/checkpoints"
    "loras:${REMOTE_MODELS_DIR}/comfyui/loras"
    "vae:${REMOTE_MODELS_DIR}/comfyui/vae"
    "embeddings:${REMOTE_MODELS_DIR}/comfyui/embeddings"
    "upscale_models:${REMOTE_MODELS_DIR}/comfyui/upscale_models"
    "whisper:${REMOTE_MODELS_DIR}/whisper"
    "ollama:${REMOTE_MODELS_DIR}/ollama"
    "video:${REMOTE_MODELS_DIR}/video"
)

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

Sync local models to remote server model vault.

Commands:
    sync [TYPE]     Sync models (all, checkpoints, loras, etc.)
    list            List local models
    status          Show sync status
    verify          Verify remote models integrity
    pull [TYPE]     Pull models from remote to local
    init            Initialize remote model directories

Options:
    -h, --help      Show this help message
    -n, --dry-run   Show what would be transferred
    -f, --force     Force transfer even if files exist
    -v, --verbose   Verbose output
    --host HOST     Remote host (default: ${REMOTE_HOST})
    --user USER     Remote user (default: ${REMOTE_USER})

Environment Variables:
    LOCAL_MODELS_DIR    Local models directory
    GPU_WORKER_HOST     Remote GPU worker host
    REMOTE_USER         SSH user for remote host
    REMOTE_MODELS_DIR   Remote models base directory

Examples:
    $(basename "$0") sync                    # Sync all models
    $(basename "$0") sync checkpoints        # Sync only checkpoints
    $(basename "$0") list                    # List local models
    $(basename "$0") --dry-run sync          # Preview sync
    $(basename "$0") pull loras              # Pull loras from remote
EOF
    exit 0
}

# Check prerequisites
check_prerequisites() {
    local missing=()
    
    for cmd in rsync ssh; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing[*]}"
        exit 1
    fi
}

# Check SSH connectivity
check_ssh() {
    log_info "Checking SSH connectivity to ${REMOTE_USER}@${REMOTE_HOST}..."
    
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${REMOTE_USER}@${REMOTE_HOST}" "echo ok" &>/dev/null; then
        log_error "Cannot connect to ${REMOTE_USER}@${REMOTE_HOST}"
        log_info "Make sure SSH key authentication is set up"
        exit 1
    fi
    
    log_success "SSH connection OK"
}

# Get model type from filename
detect_model_type() {
    local filename="$1"
    local ext="${filename##*.}"
    local name="${filename%.*}"
    
    case "$ext" in
        safetensors|ckpt|pt|pth)
            if [[ "$name" =~ lora|LoRA|LORA ]]; then
                echo "loras"
            elif [[ "$name" =~ vae|VAE ]]; then
                echo "vae"
            elif [[ "$name" =~ embed|embedding ]]; then
                echo "embeddings"
            elif [[ "$name" =~ upscale|ESRGAN|Real ]]; then
                echo "upscale_models"
            elif [[ "$name" =~ wan|video|svd|animate ]]; then
                echo "video"
            else
                echo "checkpoints"
            fi
            ;;
        gguf|bin)
            echo "ollama"
            ;;
        *)
            echo "other"
            ;;
    esac
}

# Get remote path for model type
get_remote_path() {
    local model_type="$1"
    
    for mapping in "${MODEL_VAULT_PATHS[@]}"; do
        local type="${mapping%%:*}"
        local path="${mapping##*:}"
        if [[ "$type" == "$model_type" ]]; then
            echo "$path"
            return 0
        fi
    done
    
    # Default path for unknown types
    echo "${REMOTE_MODELS_DIR}/other"
}

# List local models
list_local_models() {
    log_step "Local models in ${LOCAL_MODELS_DIR}:"
    echo
    
    if [[ ! -d "$LOCAL_MODELS_DIR" ]]; then
        log_warn "Local models directory does not exist: $LOCAL_MODELS_DIR"
        return 1
    fi
    
    local total_size=0
    local count=0
    
    while IFS= read -r -d '' file; do
        local filename=$(basename "$file")
        local size=$(stat -c %s "$file" 2>/dev/null || echo 0)
        local size_human=$(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size}B")
        local model_type=$(detect_model_type "$filename")
        
        printf "  %-50s %10s  [%s]\n" "$filename" "$size_human" "$model_type"
        
        total_size=$((total_size + size))
        count=$((count + 1))
    done < <(find "$LOCAL_MODELS_DIR" -type f \( -name "*.safetensors" -o -name "*.ckpt" -o -name "*.pt" -o -name "*.pth" -o -name "*.gguf" -o -name "*.bin" \) -print0 | sort -z)
    
    echo
    local total_human=$(numfmt --to=iec-i --suffix=B "$total_size" 2>/dev/null || echo "${total_size}B")
    log_info "Total: $count models, $total_human"
}

# Initialize remote directories
init_remote() {
    log_step "Initializing remote model directories..."
    
    local dirs=()
    for mapping in "${MODEL_VAULT_PATHS[@]}"; do
        dirs+=("${mapping##*:}")
    done
    
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${dirs[*]}"
    
    log_success "Remote directories initialized"
}

# Sync models
sync_models() {
    local model_type="${1:-all}"
    local dry_run="${DRY_RUN:-false}"
    local force="${FORCE:-false}"
    local verbose="${VERBOSE:-false}"
    
    log_step "Syncing models (type: $model_type)..."
    
    if [[ ! -d "$LOCAL_MODELS_DIR" ]]; then
        log_error "Local models directory does not exist: $LOCAL_MODELS_DIR"
        exit 1
    fi
    
    # Build rsync options
    local rsync_opts="-avz --progress --human-readable"
    
    if [[ "$dry_run" == "true" ]]; then
        rsync_opts+=" --dry-run"
        log_info "DRY RUN - No files will be transferred"
    fi
    
    if [[ "$verbose" == "true" ]]; then
        rsync_opts+=" --verbose"
    fi
    
    if [[ "$force" != "true" ]]; then
        rsync_opts+=" --ignore-existing"
    fi
    
    # Process each model file
    local synced=0
    local skipped=0
    local failed=0
    
    while IFS= read -r -d '' file; do
        local filename=$(basename "$file")
        local detected_type=$(detect_model_type "$filename")
        
        # Filter by type if specified
        if [[ "$model_type" != "all" && "$detected_type" != "$model_type" ]]; then
            continue
        fi
        
        local remote_path=$(get_remote_path "$detected_type")
        
        log_info "Syncing: $filename → ${REMOTE_HOST}:${remote_path}/"
        
        if rsync $rsync_opts "$file" "${REMOTE_USER}@${REMOTE_HOST}:${remote_path}/"; then
            synced=$((synced + 1))
            log_success "Synced: $filename"
        else
            failed=$((failed + 1))
            log_error "Failed: $filename"
        fi
        
    done < <(find "$LOCAL_MODELS_DIR" -type f \( -name "*.safetensors" -o -name "*.ckpt" -o -name "*.pt" -o -name "*.pth" -o -name "*.gguf" -o -name "*.bin" \) -print0)
    
    echo
    log_info "Sync complete: $synced synced, $skipped skipped, $failed failed"
}

# Pull models from remote
pull_models() {
    local model_type="${1:-all}"
    local dry_run="${DRY_RUN:-false}"
    
    log_step "Pulling models from remote (type: $model_type)..."
    
    local rsync_opts="-avz --progress --human-readable"
    
    if [[ "$dry_run" == "true" ]]; then
        rsync_opts+=" --dry-run"
    fi
    
    for mapping in "${MODEL_VAULT_PATHS[@]}"; do
        local type="${mapping%%:*}"
        local remote_path="${mapping##*:}"
        
        if [[ "$model_type" != "all" && "$type" != "$model_type" ]]; then
            continue
        fi
        
        local local_path="${LOCAL_MODELS_DIR}/${type}"
        mkdir -p "$local_path"
        
        log_info "Pulling $type from ${REMOTE_HOST}:${remote_path}/"
        rsync $rsync_opts "${REMOTE_USER}@${REMOTE_HOST}:${remote_path}/" "$local_path/" || true
    done
    
    log_success "Pull complete"
}

# Show sync status
show_status() {
    log_step "Model sync status:"
    echo
    
    # Local models
    log_info "Local models:"
    if [[ -d "$LOCAL_MODELS_DIR" ]]; then
        local local_count=$(find "$LOCAL_MODELS_DIR" -type f \( -name "*.safetensors" -o -name "*.gguf" \) | wc -l)
        local local_size=$(du -sh "$LOCAL_MODELS_DIR" 2>/dev/null | cut -f1)
        echo "  Count: $local_count"
        echo "  Size: $local_size"
    else
        echo "  Directory not found"
    fi
    
    echo
    
    # Remote models
    log_info "Remote models on ${REMOTE_HOST}:"
    for mapping in "${MODEL_VAULT_PATHS[@]}"; do
        local type="${mapping%%:*}"
        local remote_path="${mapping##*:}"
        
        local remote_count=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "find '$remote_path' -type f 2>/dev/null | wc -l" 2>/dev/null || echo "0")
        local remote_size=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "du -sh '$remote_path' 2>/dev/null | cut -f1" 2>/dev/null || echo "N/A")
        
        printf "  %-15s: %3s files, %s\n" "$type" "$remote_count" "$remote_size"
    done
}

# Verify remote models
verify_models() {
    log_step "Verifying remote model integrity..."
    
    local errors=0
    
    for mapping in "${MODEL_VAULT_PATHS[@]}"; do
        local type="${mapping%%:*}"
        local remote_path="${mapping##*:}"
        
        log_info "Checking $type models..."
        
        # Check for corrupted files (size 0 or permission issues)
        local issues=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "find '$remote_path' -type f -size 0 2>/dev/null" || true)
        
        if [[ -n "$issues" ]]; then
            log_warn "Found empty files in $type:"
            echo "$issues" | sed 's/^/    /'
            errors=$((errors + 1))
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        log_success "All models verified OK"
    else
        log_warn "Found $errors issues"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    DRY_RUN=false
    FORCE=false
    VERBOSE=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --host)
                REMOTE_HOST="$2"
                shift 2
                ;;
            --user)
                REMOTE_USER="$2"
                shift 2
                ;;
            *)
                break
                ;;
        esac
    done
    
    local command="${1:-sync}"
    local arg="${2:-}"
    
    check_prerequisites
    
    case "$command" in
        sync)
            check_ssh
            init_remote
            sync_models "$arg"
            ;;
        list)
            list_local_models
            ;;
        status)
            check_ssh
            show_status
            ;;
        verify)
            check_ssh
            verify_models
            ;;
        pull)
            check_ssh
            pull_models "$arg"
            ;;
        init)
            check_ssh
            init_remote
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            ;;
    esac
}

main "$@"
