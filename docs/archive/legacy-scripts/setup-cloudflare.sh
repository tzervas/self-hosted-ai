#!/usr/bin/env bash
# =============================================================================
# Cloudflare Integration Setup Script
# =============================================================================
# This script configures Cloudflare API credentials for cert-manager
# DNS-01 challenges and optional Origin CA certificates.
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - Cloudflare account with vectorweight.com domain
#   - API credentials stored in ~/Documents/.secret/
#
# Cloudflare Credentials Required:
#   - cf-global-api-key: Global API Key (for DNS management)
#   - cf-origin-ca-key: Origin CA Key (for Origin CA certificates)
#
# Usage:
#   ./scripts/setup-cloudflare.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
CLOUDFLARE_EMAIL="${CLOUDFLARE_EMAIL:-tzervas@vectorweight.com}"
SECRET_DIR="${SECRET_DIR:-$HOME/Documents/.secret}"
CERT_MANAGER_NAMESPACE="cert-manager"
DOMAIN="vectorweight.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step() { echo -e "${CYAN}[STEP]${NC} $*"; }

# =============================================================================
# Validation
# =============================================================================

log_info "Validating Cloudflare credentials..."

# Check for required files
GLOBAL_API_KEY_FILE="${SECRET_DIR}/cf-global-api-key"
ORIGIN_CA_KEY_FILE="${SECRET_DIR}/cf-origin-ca-key"

# Try alternate naming (typo in original: cpi vs api)
if [[ ! -f "$GLOBAL_API_KEY_FILE" ]]; then
    GLOBAL_API_KEY_FILE="${SECRET_DIR}/cf-global-api-key"
fi

if [[ ! -f "$GLOBAL_API_KEY_FILE" ]]; then
    log_error "Cloudflare Global API key not found!"
    log_error "Expected at: ${SECRET_DIR}/cf-global-api-key"
    log_error ""
    log_error "To get your Global API Key:"
    log_error "1. Go to https://dash.cloudflare.com/profile/api-tokens"
    log_error "2. Find 'Global API Key' and click 'View'"
    log_error "3. Save to: ${SECRET_DIR}/cf-global-api-key"
    exit 1
fi

if [[ ! -f "$ORIGIN_CA_KEY_FILE" ]]; then
    log_warn "Cloudflare Origin CA key not found at: ${ORIGIN_CA_KEY_FILE}"
    log_warn "Origin CA certificates will not be available."
    log_warn ""
    log_warn "To get your Origin CA Key:"
    log_warn "1. Go to https://dash.cloudflare.com/profile/api-tokens"
    log_warn "2. Find 'Origin CA Key' and click 'View'"
    log_warn "3. Save to: ${SECRET_DIR}/cf-origin-ca-key"
    ORIGIN_CA_AVAILABLE=false
else
    ORIGIN_CA_AVAILABLE=true
fi

# Read credentials
CLOUDFLARE_GLOBAL_API_KEY=$(cat "$GLOBAL_API_KEY_FILE" | tr -d '\n')

if [[ "$ORIGIN_CA_AVAILABLE" == "true" ]]; then
    CLOUDFLARE_ORIGIN_CA_KEY=$(cat "$ORIGIN_CA_KEY_FILE" | tr -d '\n')
fi

log_success "Cloudflare credentials validated!"

# =============================================================================
# Create cert-manager namespace if needed
# =============================================================================

log_step "Ensuring cert-manager namespace exists..."

kubectl create namespace "$CERT_MANAGER_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# =============================================================================
# Create Cloudflare API Credentials Secret
# =============================================================================

log_step "Creating Cloudflare API credentials secret..."

# The secret contains the Global API Key for DNS-01 challenges
# cert-manager uses this to create DNS TXT records for validation
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-api-credentials
  namespace: ${CERT_MANAGER_NAMESPACE}
  labels:
    app.kubernetes.io/name: cloudflare-credentials
    app.kubernetes.io/component: cert-manager
    app.kubernetes.io/part-of: self-hosted-ai
type: Opaque
stringData:
  # Global API Key - used for DNS-01 challenges
  api-key: "${CLOUDFLARE_GLOBAL_API_KEY}"
  # API Token format (same key, different name for compatibility)
  api-token: "${CLOUDFLARE_GLOBAL_API_KEY}"
  # Email associated with the Cloudflare account
  email: "${CLOUDFLARE_EMAIL}"
EOF

log_success "Cloudflare API credentials secret created!"

# =============================================================================
# Create Origin CA Key Secret (if available)
# =============================================================================

if [[ "$ORIGIN_CA_AVAILABLE" == "true" ]]; then
    log_step "Creating Cloudflare Origin CA key secret..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-origin-ca-key
  namespace: ${CERT_MANAGER_NAMESPACE}
  labels:
    app.kubernetes.io/name: cloudflare-origin-ca
    app.kubernetes.io/component: cert-manager
    app.kubernetes.io/part-of: self-hosted-ai
type: Opaque
stringData:
  # Origin CA Key - for issuing Cloudflare Origin CA certificates
  origin-ca-key: "${CLOUDFLARE_ORIGIN_CA_KEY}"
EOF

    log_success "Cloudflare Origin CA key secret created!"
fi

# =============================================================================
# Verify Cloudflare API Connection
# =============================================================================

log_step "Verifying Cloudflare API connection..."

# Test the API key by fetching zone information
ZONE_CHECK=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=${DOMAIN}" \
    -H "X-Auth-Email: ${CLOUDFLARE_EMAIL}" \
    -H "X-Auth-Key: ${CLOUDFLARE_GLOBAL_API_KEY}" \
    -H "Content-Type: application/json" 2>/dev/null || echo '{"success":false}')

if echo "$ZONE_CHECK" | grep -q '"success":true'; then
    ZONE_ID=$(echo "$ZONE_CHECK" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    ZONE_STATUS=$(echo "$ZONE_CHECK" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    log_success "Cloudflare API connection verified!"
    log_info "Zone ID: ${ZONE_ID}"
    log_info "Zone Status: ${ZONE_STATUS}"
    
    # Save zone ID for reference
    echo "$ZONE_ID" > "${PROJECT_ROOT}/.cloudflare-zone-id"
else
    log_warn "Could not verify Cloudflare API connection."
    log_warn "This might be due to:"
    log_warn "  - Invalid API key"
    log_warn "  - Domain not yet configured in Cloudflare"
    log_warn "  - Network issues"
    log_warn ""
    log_warn "cert-manager will retry during certificate issuance."
fi

# =============================================================================
# Create ClusterIssuer test certificate request
# =============================================================================

log_step "Creating test certificate request..."

# This will test the full flow
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cloudflare-test-cert
  namespace: ${CERT_MANAGER_NAMESPACE}
spec:
  secretName: cloudflare-test-cert-tls
  issuerRef:
    name: letsencrypt-cloudflare
    kind: ClusterIssuer
  dnsNames:
    - test.${DOMAIN}
  duration: 2160h # 90 days
  renewBefore: 360h # 15 days
EOF

log_info "Test certificate request created."
log_info "Check status with: kubectl get certificate -n ${CERT_MANAGER_NAMESPACE} cloudflare-test-cert"

# =============================================================================
# Output Summary
# =============================================================================

echo ""
echo "============================================================================="
echo "                  CLOUDFLARE INTEGRATION COMPLETE"
echo "============================================================================="
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ Configuration Summary                                                    │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ Domain:              ${DOMAIN}"
echo "│ Cloudflare Email:    ${CLOUDFLARE_EMAIL}"
echo "│ API Credentials:     cloudflare-api-credentials (in ${CERT_MANAGER_NAMESPACE})"
if [[ "$ORIGIN_CA_AVAILABLE" == "true" ]]; then
echo "│ Origin CA Key:       cloudflare-origin-ca-key (in ${CERT_MANAGER_NAMESPACE})"
fi
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ Available ClusterIssuers                                                 │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ letsencrypt-cloudflare         - Production (DNS-01 via Cloudflare)     │"
echo "│ letsencrypt-cloudflare-staging - Staging (for testing)                  │"
echo "│ letsencrypt-production         - Backup (HTTP-01 via Traefik)           │"
echo "│ self-signed                    - Self-signed (internal use)             │"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ Next Steps                                                               │"
echo "├─────────────────────────────────────────────────────────────────────────┤"
echo "│ 1. Verify ClusterIssuers are ready:                                     │"
echo "│    kubectl get clusterissuers                                           │"
echo "│                                                                         │"
echo "│ 2. Check certificate status:                                            │"
echo "│    kubectl get certificates -A                                          │"
echo "│                                                                         │"
echo "│ 3. Watch certificate issuance:                                          │"
echo "│    kubectl describe certificate -n cert-manager cloudflare-test-cert    │"
echo "│                                                                         │"
echo "│ 4. Troubleshoot if needed:                                              │"
echo "│    kubectl logs -n cert-manager -l app=cert-manager                     │"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""

# =============================================================================
# Cleanup test cert after verification
# =============================================================================

log_info "The test certificate will be automatically managed by cert-manager."
log_info "You can delete it after verification: kubectl delete certificate -n ${CERT_MANAGER_NAMESPACE} cloudflare-test-cert"
