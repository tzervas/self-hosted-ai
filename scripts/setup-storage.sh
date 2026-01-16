#!/usr/bin/env bash
# =============================================================================
# setup-storage.sh - Configure btrfs storage foundation for Longhorn
# =============================================================================
# This script prepares the host filesystem for Longhorn storage:
#   1. Creates btrfs subvolume @longhorn if not exists
#   2. Mounts with optimal options for NVMe/SSD
#   3. Verifies compression is enabled
#
# Prerequisites:
#   - Root/sudo access
#   - Existing btrfs filesystem at /mnt/storage or similar
#   - The storage device should be NVMe or SSD for best performance
#
# Usage:
#   sudo ./scripts/setup-storage.sh [--device /dev/nvme0n1p2] [--mount-point /mnt/storage]
# =============================================================================

set -euo pipefail

# Configuration defaults
BTRFS_DEVICE="${BTRFS_DEVICE:-}"
BTRFS_MOUNT="${BTRFS_MOUNT:-/mnt/storage}"
LONGHORN_SUBVOL="@longhorn"
LONGHORN_PATH="/var/lib/longhorn"
COMPRESSION="zstd:1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --device)
            BTRFS_DEVICE="$2"
            shift 2
            ;;
        --mount-point)
            BTRFS_MOUNT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--device /dev/nvme0n1p2] [--mount-point /mnt/storage]"
            echo ""
            echo "Options:"
            echo "  --device       The btrfs block device (e.g., /dev/nvme0n1p2)"
            echo "  --mount-point  Where the main btrfs filesystem is mounted"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (or with sudo)"
    exit 1
fi

# =============================================================================
# Step 1: Detect btrfs filesystem
# =============================================================================
log_info "Detecting btrfs filesystem..."

if [[ -n "$BTRFS_DEVICE" ]]; then
    # User specified device
    if [[ ! -b "$BTRFS_DEVICE" ]]; then
        log_error "Device $BTRFS_DEVICE does not exist"
        exit 1
    fi
    BTRFS_UUID=$(blkid -s UUID -o value "$BTRFS_DEVICE" 2>/dev/null || true)
else
    # Try to detect from mount point
    if mountpoint -q "$BTRFS_MOUNT" 2>/dev/null; then
        BTRFS_DEVICE=$(findmnt -n -o SOURCE "$BTRFS_MOUNT" | head -1)
        BTRFS_UUID=$(findmnt -n -o UUID "$BTRFS_MOUNT" | head -1)
    else
        # Try common locations
        for dev in /dev/nvme0n1p2 /dev/sda2 /dev/vda2; do
            if [[ -b "$dev" ]] && blkid "$dev" | grep -q btrfs; then
                BTRFS_DEVICE="$dev"
                BTRFS_UUID=$(blkid -s UUID -o value "$dev")
                break
            fi
        done
    fi
fi

if [[ -z "$BTRFS_DEVICE" || -z "$BTRFS_UUID" ]]; then
    log_error "Could not detect btrfs filesystem. Please specify --device"
    exit 1
fi

log_success "Found btrfs device: $BTRFS_DEVICE (UUID: $BTRFS_UUID)"

# =============================================================================
# Step 2: Ensure base mount exists
# =============================================================================
log_info "Checking base mount point..."

if ! mountpoint -q "$BTRFS_MOUNT" 2>/dev/null; then
    log_warn "Base mount $BTRFS_MOUNT not mounted, attempting to mount..."
    mkdir -p "$BTRFS_MOUNT"
    mount -t btrfs -o subvol=/,noatime,compress=zstd:1,space_cache=v2 "$BTRFS_DEVICE" "$BTRFS_MOUNT"
fi

log_success "Base mount available at $BTRFS_MOUNT"

# =============================================================================
# Step 3: Create @longhorn subvolume
# =============================================================================
log_info "Checking for @longhorn subvolume..."

SUBVOL_PATH="$BTRFS_MOUNT/$LONGHORN_SUBVOL"

if btrfs subvolume show "$SUBVOL_PATH" &>/dev/null; then
    log_success "Subvolume @longhorn already exists"
else
    log_info "Creating @longhorn subvolume..."
    btrfs subvolume create "$SUBVOL_PATH"
    log_success "Created subvolume @longhorn"
fi

# =============================================================================
# Step 4: Create mount point and mount
# =============================================================================
log_info "Setting up Longhorn mount point..."

mkdir -p "$LONGHORN_PATH"

if mountpoint -q "$LONGHORN_PATH" 2>/dev/null; then
    log_success "Longhorn path already mounted at $LONGHORN_PATH"
else
    log_info "Mounting @longhorn subvolume..."
    mount -t btrfs -o "subvol=$LONGHORN_SUBVOL,noatime,compress=$COMPRESSION,space_cache=v2,discard=async" \
        "$BTRFS_DEVICE" "$LONGHORN_PATH"
    log_success "Mounted @longhorn at $LONGHORN_PATH"
fi

# =============================================================================
# Step 5: Verify compression
# =============================================================================
log_info "Verifying compression settings..."

COMPRESSION_STATUS=$(btrfs property get "$LONGHORN_PATH" compression 2>/dev/null || echo "not set")
if [[ "$COMPRESSION_STATUS" != *"zstd"* ]]; then
    log_info "Setting compression property..."
    btrfs property set "$LONGHORN_PATH" compression zstd
fi

log_success "Compression enabled: $(btrfs property get "$LONGHORN_PATH" compression)"

# =============================================================================
# Step 6: Generate fstab entry
# =============================================================================
log_info "Generating fstab entry..."

FSTAB_ENTRY="UUID=$BTRFS_UUID $LONGHORN_PATH btrfs subvol=$LONGHORN_SUBVOL,noatime,compress=$COMPRESSION,space_cache=v2,discard=async 0 0"

if grep -q "$LONGHORN_PATH" /etc/fstab; then
    log_warn "Entry for $LONGHORN_PATH already exists in /etc/fstab"
    log_info "Existing entry:"
    grep "$LONGHORN_PATH" /etc/fstab
else
    log_info "Add this line to /etc/fstab:"
    echo ""
    echo "$FSTAB_ENTRY"
    echo ""

    read -p "Add to /etc/fstab now? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "# Longhorn storage (managed by self-hosted-ai)" >> /etc/fstab
        echo "$FSTAB_ENTRY" >> /etc/fstab
        log_success "Added to /etc/fstab"
    fi
fi

# =============================================================================
# Step 7: Display summary
# =============================================================================
echo ""
echo "============================================================================="
echo "                    STORAGE SETUP COMPLETE"
echo "============================================================================="
echo ""
echo "Longhorn storage configuration:"
echo "  Device:       $BTRFS_DEVICE"
echo "  UUID:         $BTRFS_UUID"
echo "  Subvolume:    $LONGHORN_SUBVOL"
echo "  Mount path:   $LONGHORN_PATH"
echo "  Compression:  $COMPRESSION"
echo ""
echo "Verify with:"
echo "  btrfs subvolume list $BTRFS_MOUNT"
echo "  btrfs filesystem usage $LONGHORN_PATH"
echo "  mount | grep longhorn"
echo ""
echo "Next steps:"
echo "  1. Run this script on all cluster nodes"
echo "  2. Install Longhorn via ArgoCD: kubectl apply -f argocd/applications/longhorn.yaml"
echo "  3. Verify StorageClasses: kubectl get sc"
echo ""
echo "============================================================================="
