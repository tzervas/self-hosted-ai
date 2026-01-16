#!/usr/bin/env bash
# =============================================================================
# Self-Hosted AI Stack - Secret Generation and Sealing Script
# =============================================================================
# This script generates all required secrets for the stack and optionally
# seals them using Bitnami SealedSecrets for GitOps-safe storage.
#
# Prerequisites:
#   - kubeseal CLI (for sealing): brew install kubeseal
#   - kubectl configured with cluster access
#   - SealedSecrets controller deployed in kube-system namespace
#
# Usage:
#   ./scripts/generate-secrets.sh [--seal] [--output-dir <dir>]
#
# Options:
#   --seal        Seal secrets using kubeseal (requires running cluster)
#   --output-dir  Output directory for sealed secrets (default: argocd/secrets)
#   --dry-run     Generate secrets without applying or sealing
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/argocd/secrets"
SEAL_SECRETS=false
DRY_RUN=false
NAMESPACE="ai-services"
N8N_NAMESPACE="automation"
MONITORING_NAMESPACE="monitoring"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --seal)
            SEAL_SECRETS=true
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--seal] [--output-dir <dir>] [--dry-run] [--namespace <ns>]"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Generate random secrets
generate_secret() {
    openssl rand -hex 32
}

generate_password() {
    openssl rand -base64 24 | tr -d '/+=' | cut -c1-20
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

log_info "Generating secrets for Self-Hosted AI stack..."

# =============================================================================
# Secret Values Generation
# =============================================================================

# Web UI Secrets
WEBUI_SECRET_KEY=$(generate_secret)
WEBUI_ADMIN_EMAIL="admin@homelab.local"
WEBUI_ADMIN_PASSWORD=$(generate_password)

# LiteLLM Secrets
LITELLM_MASTER_KEY="sk-$(generate_secret)"

# PostgreSQL Secrets
POSTGRES_PASSWORD=$(generate_password)
POSTGRES_ADMIN_PASSWORD=$(generate_password)
LITELLM_DATABASE_URL="postgresql://litellm:${POSTGRES_PASSWORD}@postgresql:5432/litellm"

# Redis Secrets
REDIS_PASSWORD=$(generate_password)

# N8N Secrets
N8N_ENCRYPTION_KEY=$(generate_secret)
N8N_BASIC_AUTH_USER="admin"
N8N_BASIC_AUTH_PASSWORD=$(generate_password)

# SearXNG Secrets
SEARXNG_SECRET_KEY=$(generate_secret)

# Grafana Secrets
GRAFANA_ADMIN_PASSWORD=$(generate_password)

log_info "Creating Kubernetes secret manifests..."

# =============================================================================
# Secret Manifests (Raw - NOT for Git!)
# =============================================================================

# WebUI Secret
cat > "${OUTPUT_DIR}/webui-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: webui-secret
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  secret-key: "${WEBUI_SECRET_KEY}"
  admin-email: "${WEBUI_ADMIN_EMAIL}"
  admin-password: "${WEBUI_ADMIN_PASSWORD}"
EOF

# LiteLLM Secret
cat > "${OUTPUT_DIR}/litellm-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: litellm-secret
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  master-key: "${LITELLM_MASTER_KEY}"
  database-url: "${LITELLM_DATABASE_URL}"
EOF

# PostgreSQL Secret
cat > "${OUTPUT_DIR}/postgresql-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-secret
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  postgres-password: "${POSTGRES_ADMIN_PASSWORD}"
  password: "${POSTGRES_PASSWORD}"
EOF

# Redis Secret
cat > "${OUTPUT_DIR}/redis-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: redis-secret
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  redis-password: "${REDIS_PASSWORD}"
EOF

# N8N Secret (automation namespace)
cat > "${OUTPUT_DIR}/n8n-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: n8n-secret
  namespace: ${N8N_NAMESPACE}
type: Opaque
stringData:
  N8N_ENCRYPTION_KEY: "${N8N_ENCRYPTION_KEY}"
  N8N_BASIC_AUTH_USER: "${N8N_BASIC_AUTH_USER}"
  N8N_BASIC_AUTH_PASSWORD: "${N8N_BASIC_AUTH_PASSWORD}"
EOF

# SearXNG Secret
cat > "${OUTPUT_DIR}/searxng-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: searxng-secret
  namespace: ${NAMESPACE}
type: Opaque
stringData:
  secret-key: "${SEARXNG_SECRET_KEY}"
EOF

# Grafana Secret (monitoring namespace)
cat > "${OUTPUT_DIR}/grafana-secret.yaml" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: grafana-secret
  namespace: ${MONITORING_NAMESPACE}
type: Opaque
stringData:
  admin-password: "${GRAFANA_ADMIN_PASSWORD}"
EOF

log_success "Secret manifests generated in ${OUTPUT_DIR}/"

# =============================================================================
# Seal Secrets (if requested)
# =============================================================================

if [[ "$SEAL_SECRETS" == "true" ]]; then
    log_info "Sealing secrets with kubeseal..."
    
    if ! command -v kubeseal &> /dev/null; then
        log_error "kubeseal not found. Install with: brew install kubeseal"
        exit 1
    fi
    
    SEALED_DIR="${OUTPUT_DIR}/sealed"
    mkdir -p "$SEALED_DIR"
    
    for secret_file in "${OUTPUT_DIR}"/*.yaml; do
        if [[ -f "$secret_file" && ! -d "$secret_file" ]]; then
            filename=$(basename "$secret_file")
            sealed_filename="sealed-${filename}"
            
            log_info "Sealing ${filename}..."
            kubeseal --format yaml < "$secret_file" > "${SEALED_DIR}/${sealed_filename}"
            log_success "Created ${SEALED_DIR}/${sealed_filename}"
        fi
    done
    
    log_success "All secrets sealed! Safe to commit files in ${SEALED_DIR}/"
    log_warn "DO NOT commit files in ${OUTPUT_DIR}/ (raw secrets)"
fi

# =============================================================================
# Apply Secrets (if not dry-run)
# =============================================================================

if [[ "$DRY_RUN" == "false" ]]; then
    log_info "Applying secrets to cluster..."
    
    # Create namespaces if needed
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace "$N8N_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace "$MONITORING_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    for secret_file in "${OUTPUT_DIR}"/*.yaml; do
        if [[ -f "$secret_file" && ! -d "$secret_file" ]]; then
            kubectl apply -f "$secret_file"
        fi
    done
    
    log_success "Secrets applied to cluster!"
fi

# =============================================================================
# Output Summary
# =============================================================================

echo ""
echo "============================================================================="
echo "                     GENERATED SECRETS SUMMARY"
echo "============================================================================="
echo ""
echo "IMPORTANT: Store these credentials securely! They won't be shown again."
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ Open WebUI Admin                                                         │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Email:    ${WEBUI_ADMIN_EMAIL}"
echo "│ Password: ${WEBUI_ADMIN_PASSWORD}"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ LiteLLM API                                                              │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Master Key: ${LITELLM_MASTER_KEY}"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ N8N Admin                                                                │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Username: ${N8N_BASIC_AUTH_USER}"
echo "│ Password: ${N8N_BASIC_AUTH_PASSWORD}"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ Grafana Admin                                                            │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Username: admin"
echo "│ Password: ${GRAFANA_ADMIN_PASSWORD}"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ PostgreSQL                                                               │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Admin Password:   ${POSTGRES_ADMIN_PASSWORD}"
echo "│ LiteLLM Password: ${POSTGRES_PASSWORD}"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ Redis                                                                    │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Password: ${REDIS_PASSWORD}"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "============================================================================="
echo ""

if [[ "$SEAL_SECRETS" == "true" ]]; then
    log_success "Sealed secrets are safe to commit: ${OUTPUT_DIR}/sealed/"
fi

log_warn "Raw secret files in ${OUTPUT_DIR}/ should NOT be committed to git!"
log_info "Add to .gitignore: argocd/secrets/*.yaml"
