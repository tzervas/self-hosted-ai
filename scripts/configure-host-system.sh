#!/usr/bin/env bash
# configure-host-system.sh - Configure host system settings for self-hosted AI stack
# Run with sudo on both server and GPU worker nodes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
  fi
}

# =============================================================================
# inotify Configuration (for Ingest Service file watching)
# =============================================================================
configure_inotify() {
  log_info "Configuring inotify settings..."

  local current_watches
  current_watches=$(cat /proc/sys/fs/inotify/max_user_watches)
  local target_watches=524288

  if [[ $current_watches -lt $target_watches ]]; then
    # Apply immediately
    sysctl -w fs.inotify.max_user_watches=$target_watches
    sysctl -w fs.inotify.max_queued_events=32768
    sysctl -w fs.inotify.max_user_instances=1024

    # Persist across reboots
    cat > /etc/sysctl.d/99-self-hosted-ai.conf <<EOF
# Self-Hosted AI Stack - inotify settings for file watching
# Required by ingest-service for document monitoring
fs.inotify.max_user_watches = $target_watches
fs.inotify.max_queued_events = 32768
fs.inotify.max_user_instances = 1024
EOF

    log_success "inotify limits increased to $target_watches watches"
  else
    log_success "inotify already configured ($current_watches watches)"
  fi
}

# =============================================================================
# Virtual Memory Configuration (for large models)
# =============================================================================
configure_vm() {
  log_info "Configuring virtual memory settings..."

  # Reduce swappiness for better performance with large models
  local current_swappiness
  current_swappiness=$(cat /proc/sys/vm/swappiness)

  if [[ $current_swappiness -gt 10 ]]; then
    sysctl -w vm.swappiness=10
    echo "vm.swappiness = 10" >> /etc/sysctl.d/99-self-hosted-ai.conf
    log_success "Reduced swappiness to 10 (was $current_swappiness)"
  else
    log_success "Swappiness already configured ($current_swappiness)"
  fi

  # Increase max memory map areas (helps with large models)
  local current_map_count
  current_map_count=$(cat /proc/sys/vm/max_map_count)

  if [[ $current_map_count -lt 262144 ]]; then
    sysctl -w vm.max_map_count=262144
    echo "vm.max_map_count = 262144" >> /etc/sysctl.d/99-self-hosted-ai.conf
    log_success "Increased max_map_count to 262144"
  else
    log_success "max_map_count already configured ($current_map_count)"
  fi
}

# =============================================================================
# Network Configuration (for container communication)
# =============================================================================
configure_network() {
  log_info "Configuring network settings..."

  # Enable IP forwarding for container networking
  sysctl -w net.ipv4.ip_forward=1

  # Increase connection tracking limits
  if [[ -f /proc/sys/net/netfilter/nf_conntrack_max ]]; then
    local current_conntrack
    current_conntrack=$(cat /proc/sys/net/netfilter/nf_conntrack_max)
    if [[ $current_conntrack -lt 262144 ]]; then
      sysctl -w net.netfilter.nf_conntrack_max=262144
      echo "net.netfilter.nf_conntrack_max = 262144" >> /etc/sysctl.d/99-self-hosted-ai.conf
      log_success "Increased conntrack max to 262144"
    fi
  fi

  # Increase local port range for many connections
  echo "net.ipv4.ip_local_port_range = 1024 65535" >> /etc/sysctl.d/99-self-hosted-ai.conf

  log_success "Network settings configured"
}

# =============================================================================
# File Descriptor Limits
# =============================================================================
configure_limits() {
  log_info "Configuring file descriptor limits..."

  # Check current limits
  local current_limit
  current_limit=$(ulimit -n)

  if [[ $current_limit -lt 65535 ]]; then
    # Configure system-wide limits
    cat > /etc/security/limits.d/99-self-hosted-ai.conf <<EOF
# Self-Hosted AI Stack - File descriptor limits
* soft nofile 65535
* hard nofile 65535
root soft nofile 65535
root hard nofile 65535
EOF

    log_success "File descriptor limits configured (requires re-login to take effect)"
  else
    log_success "File descriptor limits already adequate ($current_limit)"
  fi
}

# =============================================================================
# Data Directory Setup
# =============================================================================
configure_data_dirs() {
  local data_path="${DATA_PATH:-/data}"
  log_info "Configuring data directories at $data_path..."

  # Create required directories
  local dirs=(
    "$data_path/comfyui/models/checkpoints"
    "$data_path/comfyui/models/upscale_models"
    "$data_path/comfyui/models/vae"
    "$data_path/comfyui/models/loras"
    "$data_path/comfyui/models/clip"
    "$data_path/comfyui/output"
    "$data_path/comfyui/input"
    "$data_path/comfyui/custom_nodes"
    "$data_path/comfyui/workflows"
    "$data_path/whisper"
    "$data_path/ingest"
    "$data_path/documents"
    "$data_path/n8n"
    "$data_path/traefik/certs"
    "$data_path/traefik/config"
  )

  for dir in "${dirs[@]}"; do
    mkdir -p "$dir"
  done

  # Set permissions for n8n (runs as uid 1000)
  chown -R 1000:1000 "$data_path/n8n"

  log_success "Data directories created"
}

# =============================================================================
# GPU Configuration (for GPU worker node)
# =============================================================================
configure_gpu() {
  log_info "Checking GPU configuration..."

  if command -v nvidia-smi &>/dev/null; then
    # Enable persistence mode for faster GPU initialization
    nvidia-smi -pm 1 2>/dev/null || log_warn "Could not enable persistence mode"

    # Display GPU info
    log_success "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  else
    log_warn "nvidia-smi not found - skipping GPU configuration"
  fi
}

# =============================================================================
# Main
# =============================================================================
main() {
  check_root

  echo ""
  echo "=============================================="
  echo "  Self-Hosted AI Stack - System Configuration"
  echo "=============================================="
  echo ""

  configure_inotify
  configure_vm
  configure_network
  configure_limits
  configure_data_dirs
  configure_gpu

  echo ""
  log_success "System configuration complete!"
  echo ""
  echo "Next steps:"
  echo "  1. Log out and back in for ulimit changes to take effect"
  echo "  2. Restart Docker: sudo systemctl restart docker"
  echo "  3. Deploy services with: docker compose up -d"
  echo ""
}

main "$@"
