#!/usr/bin/env bash
set -euo pipefail

# cleanup-home.sh
# Cleans up /home/kang — targets build artifacts, caches, and stale data.
# Run as your user (not root): bash scripts/cleanup-home.sh
#
# Usage:
#   bash scripts/cleanup-home.sh --dry-run   # Preview
#   bash scripts/cleanup-home.sh              # Execute

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
section() { echo -e "\n${CYAN}══════ $* ══════${NC}"; }

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true && warn "DRY RUN — no changes will be made\n"

TOTAL_FREED=0
HOME_DIR="/home/kang"

freed() {
    local size_bytes
    size_bytes=$(du -sb "$1" 2>/dev/null | awk '{print $1}' || echo 0)
    TOTAL_FREED=$((TOTAL_FREED + size_bytes))
    echo "$size_bytes"
}

human() { numfmt --to=iec-i --suffix=B "$1" 2>/dev/null || echo "${1}B"; }

safe_rm() {
    local path="$1"
    local desc="$2"
    if [ ! -e "$path" ]; then return; fi
    local hsize
    hsize=$(du -sh "$path" 2>/dev/null | awk '{print $1}')
    if [ "$DRY_RUN" = true ]; then
        warn "  WOULD DELETE: $path ($hsize) — $desc"
        freed "$path" > /dev/null
    else
        freed "$path" > /dev/null
        if rm -rf "$path" 2>/dev/null; then
            info "  Deleted: $path ($hsize) — $desc"
        else
            warn "  PARTIAL DELETE: $path — some files are root-owned, run: sudo rm -rf $path"
        fi
    fi
}

section "BEFORE"
df -h /home 2>/dev/null

# ────────────────────────────────────────────────────────────
section "1. RUST target/ DIRECTORIES (~142G) — build artifacts, always regenerable"
# ────────────────────────────────────────────────────────────

while IFS= read -r target_dir; do
    safe_rm "$target_dir" "Rust build artifacts (cargo build recreates)"
done < <(find "$HOME_DIR/Documents/projects" -maxdepth 4 -name "target" -type d 2>/dev/null)

# Also clean aNa target specifically (deeper nesting)
safe_rm "$HOME_DIR/Documents/projects/github/homelab-cluster/aNa/target" "aNa Rust build artifacts"

# ────────────────────────────────────────────────────────────
section "2. PRESENT-DEMO MODEL CACHES (~290G) — local model copies"
# ────────────────────────────────────────────────────────────

# Nuke the entire present-demo project (293G — models, quantized outputs, venvs)
safe_rm "$HOME_DIR/Documents/projects/github/present-demo" "Entire present-demo project (stale)"

# ────────────────────────────────────────────────────────────
section "3. PYTHON .venv DIRECTORIES — recreatable with uv/pip"
# ────────────────────────────────────────────────────────────

while IFS= read -r venv_dir; do
    safe_rm "$venv_dir" "Python virtualenv (uv sync recreates)"
done < <(find "$HOME_DIR/Documents/projects" -maxdepth 4 -name ".venv" -type d 2>/dev/null)

# ────────────────────────────────────────────────────────────
section "4. PACKAGE MANAGER CACHES (~120G)"
# ────────────────────────────────────────────────────────────

# uv cache (66G) — all cached Python packages
if command -v uv &>/dev/null; then
    if [ "$DRY_RUN" = true ]; then
        UV_SIZE=$(du -sh "$HOME_DIR/.cache/uv" 2>/dev/null | awk '{print $1}')
        warn "  WOULD RUN: uv cache clean ($UV_SIZE)"
        freed "$HOME_DIR/.cache/uv" > /dev/null
    else
        UV_SIZE=$(du -sh "$HOME_DIR/.cache/uv" 2>/dev/null | awk '{print $1}')
        uv cache clean 2>/dev/null || rm -rf "$HOME_DIR/.cache/uv"
        info "  Cleaned uv cache ($UV_SIZE)"
    fi
fi

# Hugging Face cache (41G) — downloaded models
safe_rm "$HOME_DIR/.cache/huggingface" "HuggingFace model cache (re-downloadable)"

# pip cache (4.1G)
safe_rm "$HOME_DIR/.cache/pip" "pip download cache"

# selfdev cache (7G)
safe_rm "$HOME_DIR/.cache/selfdev" "selfdev cache"

# Playwright browsers (622M)
safe_rm "$HOME_DIR/.cache/ms-playwright" "Playwright test browsers"

# Nix cache (78M) — nix is being removed from system
safe_rm "$HOME_DIR/.cache/nix" "Nix cache (nix removed from system)"

# mypy caches
while IFS= read -r mypy_dir; do
    safe_rm "$mypy_dir" "mypy type checking cache"
done < <(find "$HOME_DIR/Documents/projects" -maxdepth 4 -name ".mypy_cache" -type d 2>/dev/null)

# ────────────────────────────────────────────────────────────
section "5. TEST DATA AND JUNK"
# ────────────────────────────────────────────────────────────

# large_test_20gb (38G) — synthetic test files from Jan 11
safe_rm "$HOME_DIR/large_test_20gb" "Synthetic test data (benchmark junk)"

# cuda_test (2.6G)
safe_rm "$HOME_DIR/cuda_test" "CUDA test leftovers"

# rust-ai/runs (14G) — old training run outputs
safe_rm "$HOME_DIR/Documents/projects/rust-ai/runs" "Old training run outputs"

# ────────────────────────────────────────────────────────────
section "6. CONTAINER IMAGE CACHE (41G)"
# ────────────────────────────────────────────────────────────

if [ -d "$HOME_DIR/.local/share/containers" ]; then
    CONTAINER_SIZE=$(du -sh "$HOME_DIR/.local/share/containers" 2>/dev/null | awk '{print $1}')
    if command -v podman &>/dev/null; then
        if [ "$DRY_RUN" = true ]; then
            warn "  WOULD RUN: podman system prune -a -f ($CONTAINER_SIZE)"
            freed "$HOME_DIR/.local/share/containers" > /dev/null
        else
            podman system prune -a -f 2>/dev/null || true
            info "  Pruned podman images ($CONTAINER_SIZE before)"
        fi
    else
        safe_rm "$HOME_DIR/.local/share/containers" "Orphaned container storage (no podman)"
    fi
fi

# ────────────────────────────────────────────────────────────
section "7. STALE OLLAMA MODEL STORES (~182G)"
# ────────────────────────────────────────────────────────────

# These are pre-k3s standalone Ollama stores. The cluster now uses
# NFS-backed shared-models at /data/models/ — these local copies are stale.
# Models should live on the homelab server, not this workstation.
safe_rm "/home/data/ollama-cpu" "Stale CPU Ollama store (k3s uses NFS shared-models)"
safe_rm "/home/data/ollama-gpu" "Stale GPU Ollama store (k3s uses NFS shared-models)"

# ────────────────────────────────────────────────────────────
section "SUMMARY"
# ────────────────────────────────────────────────────────────

echo
info "Total freed: $(human $TOTAL_FREED)"
echo

if [ "$DRY_RUN" = true ]; then
    warn "DRY RUN complete. To execute: bash scripts/cleanup-home.sh"
else
    section "AFTER"
    df -h /home 2>/dev/null
    echo
    info "Cleanup complete!"
    info "Rebuild Rust projects with: cargo build"
    info "Rebuild Python venvs with: uv sync"
fi
