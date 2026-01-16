#!/usr/bin/env bash
# =============================================================================
# Self-Hosted AI Stack - DNS Configuration Script
# =============================================================================
# This script configures DNS for vectorweight.com, setting up both:
# 1. Local /etc/hosts entries for immediate access
# 2. CoreDNS ConfigMap for cluster-internal resolution
#
# Usage:
#   ./scripts/setup-dns.sh [--hosts-only] [--cluster-only]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
DOMAIN="vectorweight.com"
HOSTS_ONLY=false
CLUSTER_ONLY=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step() { echo -e "${CYAN}[STEP]${NC} $*"; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --hosts-only)
            HOSTS_ONLY=true
            shift
            ;;
        --cluster-only)
            CLUSTER_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--hosts-only] [--cluster-only]"
            echo ""
            echo "Options:"
            echo "  --hosts-only    Only update /etc/hosts"
            echo "  --cluster-only  Only update CoreDNS ConfigMap"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Detect Ingress IP
# =============================================================================

get_ingress_ip() {
    local ip=""
    
    # Try to get Traefik LoadBalancer IP
    if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null 2>&1; then
        ip=$(kubectl get svc -n traefik traefik -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
        
        if [[ -z "$ip" ]]; then
            # Try external IP
            ip=$(kubectl get svc -n traefik traefik -o jsonpath='{.spec.externalIPs[0]}' 2>/dev/null || true)
        fi
        
        if [[ -z "$ip" ]]; then
            # Try NodePort - get node IP
            ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null || true)
        fi
    fi
    
    # Fallback to environment or default
    if [[ -z "$ip" ]]; then
        ip="${SERVER_HOST:-192.168.1.170}"
    fi
    
    echo "$ip"
}

# =============================================================================
# DNS Entries
# =============================================================================

DNS_ENTRIES=(
    "ai"
    "llm"
    "search"
    "argocd"
    "traefik"
    "grafana"
    "prometheus"
    "n8n"
    "dify"
    "git"
    "ollama"
    "gpu"
)

# =============================================================================
# Update /etc/hosts
# =============================================================================

update_hosts_file() {
    local ip="$1"
    local hosts_file="/etc/hosts"
    local backup_file="/etc/hosts.backup.$(date +%Y%m%d%H%M%S)"
    
    log_step "Updating /etc/hosts with ${DOMAIN} entries..."
    
    # Check if we have sudo access
    if ! sudo -n true 2>/dev/null; then
        log_warn "sudo access required to update /etc/hosts"
        log_info "Please run with sudo or add these entries manually:"
        echo ""
        echo "# ${DOMAIN} - Self-Hosted AI Stack"
        echo "${ip} ${DOMAIN}"
        for entry in "${DNS_ENTRIES[@]}"; do
            echo "${ip} ${entry}.${DOMAIN}"
        done
        echo ""
        return 1
    fi
    
    # Backup existing hosts file
    sudo cp "$hosts_file" "$backup_file"
    log_info "Backed up hosts file to ${backup_file}"
    
    # Remove existing vectorweight.com entries
    sudo sed -i "/${DOMAIN}/d" "$hosts_file"
    
    # Add new entries
    {
        echo ""
        echo "# ${DOMAIN} - Self-Hosted AI Stack (auto-generated $(date +%Y-%m-%d))"
        echo "${ip} ${DOMAIN}"
        for entry in "${DNS_ENTRIES[@]}"; do
            echo "${ip} ${entry}.${DOMAIN}"
        done
    } | sudo tee -a "$hosts_file" > /dev/null
    
    log_success "Updated /etc/hosts with ${#DNS_ENTRIES[@]} entries"
}

# =============================================================================
# Update CoreDNS ConfigMap
# =============================================================================

update_coredns() {
    local ip="$1"
    
    log_step "Updating CoreDNS custom configuration..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Cannot update CoreDNS."
        return 1
    fi
    
    if ! kubectl cluster-info &> /dev/null 2>&1; then
        log_warn "Cannot connect to cluster. Skipping CoreDNS update."
        return 1
    fi
    
    # Update the Helm values with the detected IP
    local values_file="${PROJECT_ROOT}/helm/coredns-custom/values.yaml"
    if [[ -f "$values_file" ]]; then
        # Update the fallbackIP in values.yaml
        sed -i "s/fallbackIP: .*/fallbackIP: \"${ip}\"/" "$values_file"
        log_info "Updated CoreDNS values with IP: ${ip}"
    fi
    
    # Apply the ConfigMap directly for immediate effect
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns-custom
  namespace: kube-system
  labels:
    app.kubernetes.io/name: coredns-custom
    app.kubernetes.io/part-of: self-hosted-ai
data:
  vectorweight.server: |
    ${DOMAIN}:53 {
        errors
        log
        
        hosts {
            ${ip} ${DOMAIN}
$(for entry in "${DNS_ENTRIES[@]}"; do echo "            ${ip} ${entry}.${DOMAIN}"; done)
            fallthrough
        }
        
        forward . 8.8.8.8 8.8.4.4 {
            policy sequential
        }
        
        cache 30
    }
EOF
    
    # Restart CoreDNS to pick up changes
    log_info "Restarting CoreDNS..."
    kubectl rollout restart deployment/coredns -n kube-system 2>/dev/null || \
    kubectl delete pod -n kube-system -l k8s-app=kube-dns 2>/dev/null || true
    
    log_success "CoreDNS configuration updated"
}

# =============================================================================
# Generate Squarespace DNS Instructions
# =============================================================================

generate_squarespace_instructions() {
    local ip="$1"
    
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                     SQUARESPACE DNS CONFIGURATION                            │"
    echo "├─────────────────────────────────────────────────────────────────────────────┤"
    echo "│                                                                              │"
    echo "│ Add these DNS records in Squarespace Domains for ${DOMAIN}:          │"
    echo "│                                                                              │"
    echo "│ TYPE   HOST              POINTS TO            TTL                            │"
    echo "│ ────   ────              ─────────            ───                            │"
    echo "│ A      @                 ${ip}          3600                           │"
    echo "│ A      ai                ${ip}          3600                           │"
    echo "│ A      llm               ${ip}          3600                           │"
    echo "│ A      search            ${ip}          3600                           │"
    echo "│ A      n8n               ${ip}          3600                           │"
    echo "│ A      argocd            ${ip}          3600                           │"
    echo "│ A      traefik           ${ip}          3600                           │"
    echo "│ A      grafana           ${ip}          3600                           │"
    echo "│ A      prometheus        ${ip}          3600                           │"
    echo "│ A      dify              ${ip}          3600                           │"
    echo "│ A      git               ${ip}          3600                           │"
    echo "│                                                                              │"
    echo "│ Or use a wildcard record:                                                    │"
    echo "│ A      *                 ${ip}          3600                           │"
    echo "│                                                                              │"
    echo "│ Note: For Let's Encrypt HTTP-01 challenge to work, these records must        │"
    echo "│ point to your public IP if accessible from the internet, or use              │"
    echo "│ DNS-01 challenge for internal-only clusters.                                 │"
    echo "│                                                                              │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    log_info "Setting up DNS for ${DOMAIN}..."
    
    # Detect ingress IP
    INGRESS_IP=$(get_ingress_ip)
    log_info "Detected ingress IP: ${INGRESS_IP}"
    
    if [[ "$CLUSTER_ONLY" != "true" ]]; then
        update_hosts_file "$INGRESS_IP" || true
    fi
    
    if [[ "$HOSTS_ONLY" != "true" ]]; then
        update_coredns "$INGRESS_IP" || true
    fi
    
    # Always show Squarespace instructions
    generate_squarespace_instructions "$INGRESS_IP"
    
    log_success "DNS setup complete!"
    echo ""
    log_info "Test DNS resolution with:"
    echo "  nslookup ai.${DOMAIN}"
    echo "  curl -k https://ai.${DOMAIN}"
}

main "$@"
