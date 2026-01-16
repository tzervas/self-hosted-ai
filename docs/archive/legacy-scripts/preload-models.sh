#!/usr/bin/env bash
# =============================================================================
# Self-Hosted AI Stack - Model Preload Script
# =============================================================================
# This script preloads all required models from models-manifest.yml onto
# both GPU and CPU Ollama instances. It reads the manifest, checks existing
# models, and pulls only those not yet downloaded.
#
# Usage:
#   ./scripts/preload-models.sh [--gpu-only] [--cpu-only] [--required-only] [--all]
#
# Prerequisites:
#   - yq (YAML processor): brew install yq / apt install yq
#   - kubectl with cluster access
#   - Ollama pods running
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_FILE="${PROJECT_ROOT}/config/models-manifest.yml"

# Configuration
GPU_ONLY=false
CPU_ONLY=false
REQUIRED_ONLY=true  # Default: only required models
PARALLEL_PULLS=1     # Ollama handles one pull at a time per instance
DRY_RUN=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step() { echo -e "${CYAN}[STEP]${NC} $*"; }
log_model() { echo -e "${MAGENTA}[MODEL]${NC} $*"; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu-only)
            GPU_ONLY=true
            CPU_ONLY=false
            shift
            ;;
        --cpu-only)
            CPU_ONLY=true
            GPU_ONLY=false
            shift
            ;;
        --required-only)
            REQUIRED_ONLY=true
            shift
            ;;
        --all)
            REQUIRED_ONLY=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--gpu-only] [--cpu-only] [--required-only] [--all] [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --gpu-only       Only preload models on GPU Ollama"
            echo "  --cpu-only       Only preload models on CPU Ollama"
            echo "  --required-only  Only preload 'required' priority models (default)"
            echo "  --all            Preload all models including 'optional'"
            echo "  --dry-run        Show what would be pulled without pulling"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Preflight Checks
# =============================================================================

log_step "Running preflight checks..."

# Check yq
if ! command -v yq &> /dev/null; then
    log_error "yq not found. Install with: brew install yq (macOS) or apt install yq (Linux)"
    exit 1
fi

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl first."
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    exit 1
fi

# Check manifest file
if [[ ! -f "$MANIFEST_FILE" ]]; then
    log_error "Manifest file not found: $MANIFEST_FILE"
    exit 1
fi

log_success "Preflight checks passed!"

# =============================================================================
# Helper Functions
# =============================================================================

# Get Ollama pod name
get_ollama_pod() {
    local namespace="$1"
    local label="$2"
    kubectl get pods -n "$namespace" -l "$label" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true
}

# Get list of models already downloaded
get_existing_models() {
    local namespace="$1"
    local pod="$2"
    kubectl exec -n "$namespace" "$pod" -- ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' || true
}

# Pull a model
pull_model() {
    local namespace="$1"
    local pod="$2"
    local model="$3"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_model "[DRY-RUN] Would pull: $model"
        return 0
    fi
    
    log_model "Pulling: $model (this may take a while)..."
    
    # Pull with progress
    if kubectl exec -n "$namespace" "$pod" -- ollama pull "$model"; then
        log_success "Successfully pulled: $model"
        return 0
    else
        log_error "Failed to pull: $model"
        return 1
    fi
}

# Parse models from manifest
get_models_from_manifest() {
    local section="$1"  # gpu_worker or cpu_server
    local priority_filter="$2"  # required or all
    
    if [[ "$priority_filter" == "required" ]]; then
        yq eval ".${section}.models[] | select(.priority == \"required\") | .name" "$MANIFEST_FILE"
    else
        yq eval ".${section}.models[].name" "$MANIFEST_FILE"
    fi
}

# Get model info
get_model_info() {
    local section="$1"
    local model="$2"
    yq eval ".${section}.models[] | select(.name == \"${model}\") | .size + \" - \" + .purpose" "$MANIFEST_FILE"
}

# =============================================================================
# GPU Worker Model Preloading
# =============================================================================

preload_gpu_models() {
    log_step "Preloading GPU worker models..."
    
    local namespace="gpu-workloads"
    local pod
    
    # Find Ollama GPU pod
    pod=$(get_ollama_pod "$namespace" "app.kubernetes.io/name=ollama")
    
    if [[ -z "$pod" ]]; then
        # Try alternative label
        pod=$(get_ollama_pod "$namespace" "app=ollama-gpu")
    fi
    
    if [[ -z "$pod" ]]; then
        log_warn "No Ollama GPU pod found in namespace: $namespace"
        log_info "Checking gpu-worker namespace..."
        namespace="gpu-worker"
        pod=$(get_ollama_pod "$namespace" "app.kubernetes.io/name=ollama")
    fi
    
    if [[ -z "$pod" ]]; then
        log_error "Cannot find Ollama GPU pod. Make sure it's deployed."
        return 1
    fi
    
    log_info "Found Ollama GPU pod: $pod in namespace: $namespace"
    
    # Get existing models
    local existing_models
    existing_models=$(get_existing_models "$namespace" "$pod")
    log_info "Existing GPU models: $(echo "$existing_models" | wc -l | tr -d ' ')"
    
    # Get models to pull
    local priority_filter="required"
    [[ "$REQUIRED_ONLY" == "false" ]] && priority_filter="all"
    
    local models_to_pull
    models_to_pull=$(get_models_from_manifest "gpu_worker" "$priority_filter")
    
    local total=0
    local pulled=0
    local skipped=0
    local failed=0
    
    while IFS= read -r model; do
        [[ -z "$model" ]] && continue
        ((total++))
        
        local info
        info=$(get_model_info "gpu_worker" "$model")
        
        # Check if model already exists
        if echo "$existing_models" | grep -q "^${model}$"; then
            log_info "Skipping (already exists): $model"
            ((skipped++))
            continue
        fi
        
        log_model "GPU Model: $model ($info)"
        
        if pull_model "$namespace" "$pod" "$model"; then
            ((pulled++))
        else
            ((failed++))
        fi
        
    done <<< "$models_to_pull"
    
    echo ""
    log_info "GPU Models Summary: Total=$total, Pulled=$pulled, Skipped=$skipped, Failed=$failed"
}

# =============================================================================
# CPU Server Model Preloading
# =============================================================================

preload_cpu_models() {
    log_step "Preloading CPU server models..."
    
    local namespace="ai-services"
    local pod
    
    # Find Ollama CPU pod
    pod=$(get_ollama_pod "$namespace" "app.kubernetes.io/name=ollama")
    
    if [[ -z "$pod" ]]; then
        # Try alternative label
        pod=$(get_ollama_pod "$namespace" "app=ollama")
    fi
    
    if [[ -z "$pod" ]]; then
        log_warn "No Ollama CPU pod found in namespace: $namespace"
        log_info "Checking ollama namespace..."
        namespace="ollama"
        pod=$(get_ollama_pod "$namespace" "app.kubernetes.io/name=ollama")
    fi
    
    if [[ -z "$pod" ]]; then
        log_error "Cannot find Ollama CPU pod. Make sure it's deployed."
        return 1
    fi
    
    log_info "Found Ollama CPU pod: $pod in namespace: $namespace"
    
    # Get existing models
    local existing_models
    existing_models=$(get_existing_models "$namespace" "$pod")
    log_info "Existing CPU models: $(echo "$existing_models" | wc -l | tr -d ' ')"
    
    # Get models to pull
    local priority_filter="required"
    [[ "$REQUIRED_ONLY" == "false" ]] && priority_filter="all"
    
    local models_to_pull
    models_to_pull=$(get_models_from_manifest "cpu_server" "$priority_filter")
    
    local total=0
    local pulled=0
    local skipped=0
    local failed=0
    
    while IFS= read -r model; do
        [[ -z "$model" ]] && continue
        ((total++))
        
        local info
        info=$(get_model_info "cpu_server" "$model")
        
        # Check if model already exists
        if echo "$existing_models" | grep -q "^${model}$"; then
            log_info "Skipping (already exists): $model"
            ((skipped++))
            continue
        fi
        
        log_model "CPU Model: $model ($info)"
        
        if pull_model "$namespace" "$pod" "$model"; then
            ((pulled++))
        else
            ((failed++))
        fi
        
    done <<< "$models_to_pull"
    
    echo ""
    log_info "CPU Models Summary: Total=$total, Pulled=$pulled, Skipped=$skipped, Failed=$failed"
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                    SELF-HOSTED AI - MODEL PRELOADER                          │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    echo ""
    
    local mode="both"
    [[ "$GPU_ONLY" == "true" ]] && mode="GPU only"
    [[ "$CPU_ONLY" == "true" ]] && mode="CPU only"
    
    local priority="required"
    [[ "$REQUIRED_ONLY" == "false" ]] && priority="all"
    
    log_info "Mode: $mode | Priority: $priority | Dry-run: $DRY_RUN"
    log_info "Manifest: $MANIFEST_FILE"
    echo ""
    
    local gpu_success=true
    local cpu_success=true
    
    # Preload GPU models
    if [[ "$CPU_ONLY" != "true" ]]; then
        if ! preload_gpu_models; then
            gpu_success=false
        fi
        echo ""
    fi
    
    # Preload CPU models
    if [[ "$GPU_ONLY" != "true" ]]; then
        if ! preload_cpu_models; then
            cpu_success=false
        fi
        echo ""
    fi
    
    # Final summary
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                           PRELOAD COMPLETE                                   │"
    echo "├─────────────────────────────────────────────────────────────────────────────┤"
    if [[ "$CPU_ONLY" != "true" ]]; then
        if [[ "$gpu_success" == "true" ]]; then
            echo "│  GPU Models:  ✅ Success                                                     │"
        else
            echo "│  GPU Models:  ⚠️  Partial/Failed                                              │"
        fi
    fi
    if [[ "$GPU_ONLY" != "true" ]]; then
        if [[ "$cpu_success" == "true" ]]; then
            echo "│  CPU Models:  ✅ Success                                                     │"
        else
            echo "│  CPU Models:  ⚠️  Partial/Failed                                              │"
        fi
    fi
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    echo ""
    
    if [[ "$gpu_success" == "false" || "$cpu_success" == "false" ]]; then
        exit 1
    fi
}

main "$@"
