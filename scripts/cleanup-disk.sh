#!/usr/bin/env bash
set -euo pipefail

# cleanup-disk.sh
# Cleans up and migrates bloat off root (/) to /data or /var.
#
# Root partition: 92G at 100% — CRITICAL (590MB free)
# Target: move non-essential items off root, symlink back.
#
# Usage:
#   sudo bash scripts/cleanup-disk.sh --dry-run   # Preview only
#   sudo bash scripts/cleanup-disk.sh              # Execute

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
section() { echo -e "\n${CYAN}══════ $* ══════${NC}"; }

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true && warn "DRY RUN — no changes will be made\n"

MIGRATE_BASE="/data/system-overflow"

# Print before state
section "BEFORE"
df -h / /var /home 2>/dev/null

# ────────────────────────────────────────────────────────────
section "1. REMOVE NIX (46G) — not needed on this workstation"
# ────────────────────────────────────────────────────────────

if [ -d /nix ]; then
    NIX_SIZE=$(du -sh /nix 2>/dev/null | awk '{print $1}')
    info "Found /nix ($NIX_SIZE)"

    if [ "$DRY_RUN" = false ]; then
        # Stop nix services
        systemctl stop nix-daemon.service 2>/dev/null || true
        systemctl stop nix-daemon.socket 2>/dev/null || true
        systemctl disable nix-daemon.service 2>/dev/null || true
        systemctl disable nix-daemon.socket 2>/dev/null || true

        # Remove the store
        rm -rf /nix
        info "  Removed /nix"

        # Clean up system integration
        rm -f /etc/profile.d/nix.sh /etc/profile.d/nix-daemon.sh
        rm -rf /etc/nix
        rm -f /etc/bash.bashrc.backup-before-nix
        rm -f /etc/bashrc.backup-before-nix

        # Remove nix build users
        for i in $(seq 1 32); do
            userdel "nixbld$i" 2>/dev/null || true
        done
        groupdel nixbld 2>/dev/null || true

        # Clean up user-level nix files
        rm -rf /home/kang/.nix-profile /home/kang/.nix-defexpr /home/kang/.nix-channels
        rm -rf /root/.nix-profile /root/.nix-defexpr /root/.nix-channels

        info "  Cleaned up Nix services, users, and config"
    else
        warn "  WOULD REMOVE: /nix ($NIX_SIZE)"
        warn "  WOULD REMOVE: Nix daemon, users (nixbld*), /etc/nix"
    fi
else
    info "/nix not found, already clean"
fi

# ────────────────────────────────────────────────────────────
section "2. MIGRATE CUDA TO /data (10G total on root)"
# ────────────────────────────────────────────────────────────

# Layout: /usr/local/cuda -> /etc/alternatives/cuda -> cuda-12.4
# cuda-12.6 is unused (active is 12.4), cuda-13.1 is newest
# Move everything to /data, symlink back

CUDA_DEST="$MIGRATE_BASE/cuda"
info "Active CUDA: $(readlink -f /etc/alternatives/cuda 2>/dev/null || echo 'none')"
info "CUDA dirs on root:"
ls -d /usr/local/cuda-* 2>/dev/null | while read d; do
    echo "  $d ($(du -sh "$d" 2>/dev/null | awk '{print $1}'))"
done

if [ "$DRY_RUN" = false ]; then
    mkdir -p "$CUDA_DEST"

    # Only migrate cuda-13.1 — cuda-12.6 stays on root
    for cuda_dir in /usr/local/cuda-13.1; do
        if [ -d "$cuda_dir" ] && [ ! -L "$cuda_dir" ]; then
            dirname=$(basename "$cuda_dir")
            info "  Moving $cuda_dir -> $CUDA_DEST/$dirname"
            mv "$cuda_dir" "$CUDA_DEST/$dirname"
            ln -sf "$CUDA_DEST/$dirname" "$cuda_dir"
            info "  Symlinked $cuda_dir -> $CUDA_DEST/$dirname"
        fi
    done

    # Fix cuda-12 and cuda-13 symlinks if they exist
    for link in /usr/local/cuda-12 /usr/local/cuda-13; do
        if [ -L "$link" ]; then
            target=$(readlink "$link")
            if [ ! -e "$target" ] && [ -e "$CUDA_DEST/$(basename "$target")" ]; then
                ln -sf "$CUDA_DEST/$(basename "$target")" "$link"
                info "  Fixed symlink: $link -> $CUDA_DEST/$(basename "$target")"
            fi
        fi
    done
else
    warn "  WOULD MOVE: /usr/local/cuda-13.1 -> $CUDA_DEST/cuda-13.1 (cuda-12.6 stays)"
    warn "  WOULD SYMLINK: originals back to /data"
fi

# ────────────────────────────────────────────────────────────
section "3. MIGRATE /opt/nvidia TO /data (4.3G)"
# ────────────────────────────────────────────────────────────

NVIDIA_DEST="$MIGRATE_BASE/nvidia"
if [ -d /opt/nvidia ] && [ ! -L /opt/nvidia ]; then
    NVIDIA_SIZE=$(du -sh /opt/nvidia 2>/dev/null | awk '{print $1}')
    info "Found /opt/nvidia ($NVIDIA_SIZE)"

    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$NVIDIA_DEST"
        mv /opt/nvidia "$NVIDIA_DEST/nvidia"
        ln -sf "$NVIDIA_DEST/nvidia" /opt/nvidia
        info "  Moved to $NVIDIA_DEST/nvidia, symlinked back"
    else
        warn "  WOULD MOVE: /opt/nvidia ($NVIDIA_SIZE) -> $NVIDIA_DEST/nvidia"
    fi
else
    info "/opt/nvidia already symlinked or not found"
fi

# ────────────────────────────────────────────────────────────
section "4. CLEAN SNAP CACHE"
# ────────────────────────────────────────────────────────────

# Snap keeps old revisions — remove all but current
if command -v snap &>/dev/null; then
    SNAP_BEFORE=$(du -sh /snap 2>/dev/null | awk '{print $1}')
    info "Snap cache: $SNAP_BEFORE"

    if [ "$DRY_RUN" = false ]; then
        snap list --all 2>/dev/null | awk '/disabled/{print $1, $3}' | while read name rev; do
            snap remove "$name" --revision="$rev" 2>/dev/null || true
            info "  Removed snap $name rev $rev"
        done
    else
        DISABLED=$(snap list --all 2>/dev/null | awk '/disabled/' | wc -l)
        warn "  WOULD REMOVE: $DISABLED disabled snap revisions"
    fi
fi

# ────────────────────────────────────────────────────────────
section "5. CLEAN PACKAGE CACHES AND JOURNALS"
# ────────────────────────────────────────────────────────────

if [ "$DRY_RUN" = false ]; then
    # APT cache
    apt-get clean -y 2>/dev/null && info "  Cleaned apt cache" || true
    apt-get autoremove -y 2>/dev/null && info "  Removed unused packages" || true

    # Journal
    journalctl --vacuum-size=50M 2>/dev/null && info "  Trimmed journal to 50MB" || true

    # Thumbnail cache on root (if any)
    rm -rf /root/.cache/thumbnails 2>/dev/null || true
else
    APT_CACHE=$(du -sh /var/cache/apt/archives 2>/dev/null | awk '{print $1}')
    warn "  WOULD CLEAN: apt cache ($APT_CACHE)"
    warn "  WOULD TRIM: systemd journal to 50MB"
fi

# ────────────────────────────────────────────────────────────
section "6. CLEAN UNUSED LOCALES (~900MB)"
# ────────────────────────────────────────────────────────────

if [ -d /usr/share/locale ]; then
    LOCALE_BEFORE=$(du -sh /usr/share/locale 2>/dev/null | awk '{print $1}')
    info "Locale data: $LOCALE_BEFORE"

    if [ "$DRY_RUN" = false ]; then
        # Keep only English and base locales
        find /usr/share/locale -maxdepth 1 -type d \
            ! -name 'en' ! -name 'en_US' ! -name 'en_US.UTF-8' \
            ! -name 'en_GB' ! -name 'locale' ! -name '.' \
            -exec rm -rf {} + 2>/dev/null || true
        LOCALE_AFTER=$(du -sh /usr/share/locale 2>/dev/null | awk '{print $1}')
        info "  Cleaned: $LOCALE_BEFORE -> $LOCALE_AFTER"
    else
        warn "  WOULD REMOVE: non-English locales (~900MB)"
    fi
fi

# ────────────────────────────────────────────────────────────
section "7. FIND REMAINING LARGE DIRS ON ROOT"
# ────────────────────────────────────────────────────────────

info "Top space consumers remaining on root (/):"
du -hx --max-depth=2 / 2>/dev/null | sort -rh | head -15

# ────────────────────────────────────────────────────────────
section "AFTER"
# ────────────────────────────────────────────────────────────

df -h / /var /home 2>/dev/null

if [ "$DRY_RUN" = true ]; then
    echo
    warn "DRY RUN complete. To execute: sudo bash scripts/cleanup-disk.sh"
else
    echo
    info "Cleanup complete! Verify nothing is broken:"
    info "  nvcc --version         # CUDA still works"
    info "  nvidia-smi             # GPU driver still works"
    info "  ls -la /usr/local/cuda # Symlink intact"
fi
