#!/usr/bin/env bash
# =============================================================================
# Keycloak SSO Secret Setup Script
# =============================================================================
# This script generates and applies all secrets needed for Keycloak SSO.
# Run this BEFORE deploying Keycloak via ArgoCD.
#
# Usage:
#   ./scripts/setup-keycloak-secrets.sh
#   ./scripts/setup-keycloak-secrets.sh --dry-run  # Preview only
#   ./scripts/setup-keycloak-secrets.sh --output   # Save to local file
# =============================================================================

set -euo pipefail

DRY_RUN=false
OUTPUT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --output)
      OUTPUT_FILE="KEYCLOAK_CREDENTIALS.local.md"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=============================================="
echo "  Keycloak SSO Secret Generator"
echo "=============================================="
echo ""

# Generate all passwords
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 24)
KEYCLOAK_DB_PASSWORD=$(openssl rand -hex 16)
KEYCLOAK_DB_USER_PASSWORD=$(openssl rand -hex 16)

# OAuth Client Secrets
OPENWEBUI_CLIENT_SECRET=$(openssl rand -hex 32)
N8N_CLIENT_SECRET=$(openssl rand -hex 32)
ARGOCD_CLIENT_SECRET=$(openssl rand -hex 32)
GRAFANA_CLIENT_SECRET=$(openssl rand -hex 32)

echo "Generated credentials:"
echo "  - Keycloak Admin Password: ${KEYCLOAK_ADMIN_PASSWORD:0:8}..."
echo "  - Database Password: ${KEYCLOAK_DB_PASSWORD:0:8}..."
echo "  - OAuth Client Secrets: 4 clients configured"
echo ""

if [ "$OUTPUT_FILE" != "" ]; then
  cat > "$OUTPUT_FILE" << EOF
# Keycloak SSO Credentials
# Generated: $(date -Iseconds)
# WARNING: Store securely and delete after setup!

## Keycloak Admin
- URL: https://auth.vectorweight.com
- Username: admin
- Password: $KEYCLOAK_ADMIN_PASSWORD

## OAuth Client Secrets
These are configured in Keycloak and referenced by each service.

### Open WebUI
- Client ID: open-webui
- Client Secret: $OPENWEBUI_CLIENT_SECRET

### n8n
- Client ID: n8n
- Client Secret: $N8N_CLIENT_SECRET

### ArgoCD
- Client ID: argocd
- Client Secret: $ARGOCD_CLIENT_SECRET

### Grafana
- Client ID: grafana
- Client Secret: $GRAFANA_CLIENT_SECRET

## Database (Internal)
- Host: keycloak-postgresql.auth.svc:5432
- Database: keycloak
- Password: $KEYCLOAK_DB_PASSWORD
EOF
  echo "Credentials saved to: $OUTPUT_FILE"
  echo "WARNING: Add this file to .gitignore and store securely!"
  echo ""
fi

if [ "$DRY_RUN" = true ]; then
  echo "[DRY RUN] Would create the following secrets:"
  echo ""
fi

# Create namespace
echo "Creating namespace 'auth'..."
if [ "$DRY_RUN" = false ]; then
  kubectl create namespace auth 2>/dev/null || echo "  Namespace already exists"
fi

# 1. Keycloak Admin Secret
echo "Creating keycloak-admin-secret..."
if [ "$DRY_RUN" = false ]; then
  kubectl create secret generic keycloak-admin-secret -n auth \
    --from-literal=admin-password="$KEYCLOAK_ADMIN_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

# 2. Keycloak Database Secret
echo "Creating keycloak-db-secret..."
if [ "$DRY_RUN" = false ]; then
  kubectl create secret generic keycloak-db-secret -n auth \
    --from-literal=postgres-password="$KEYCLOAK_DB_PASSWORD" \
    --from-literal=password="$KEYCLOAK_DB_USER_PASSWORD" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

# 3. OAuth Client Secrets
echo "Creating keycloak-client-secrets..."
if [ "$DRY_RUN" = false ]; then
  kubectl create secret generic keycloak-client-secrets -n auth \
    --from-literal=open-webui="$OPENWEBUI_CLIENT_SECRET" \
    --from-literal=n8n="$N8N_CLIENT_SECRET" \
    --from-literal=argocd="$ARGOCD_CLIENT_SECRET" \
    --from-literal=grafana="$GRAFANA_CLIENT_SECRET" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

# 4. Copy client secrets to service namespaces for their use
echo "Copying OAuth secrets to service namespaces..."

if [ "$DRY_RUN" = false ]; then
  # Open WebUI OAuth secret
  kubectl create secret generic openwebui-oauth -n ai-services \
    --from-literal=client-id="open-webui" \
    --from-literal=client-secret="$OPENWEBUI_CLIENT_SECRET" \
    --dry-run=client -o yaml | kubectl apply -f -

  # n8n OAuth secret
  kubectl create secret generic n8n-oauth -n automation \
    --from-literal=client-id="n8n" \
    --from-literal=client-secret="$N8N_CLIENT_SECRET" \
    --dry-run=client -o yaml | kubectl apply -f -

  # ArgoCD OAuth secret (ArgoCD uses its own secret format)
  kubectl create secret generic argocd-oauth -n argocd \
    --from-literal=client-id="argocd" \
    --from-literal=client-secret="$ARGOCD_CLIENT_SECRET" \
    --dry-run=client -o yaml | kubectl apply -f -
fi

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Deploy Keycloak via ArgoCD (will auto-sync)"
echo "  2. Access https://auth.vectorweight.com"
echo "  3. Login with admin / <password from above>"
echo "  4. Create your first user in the 'homelab' realm"
echo "  5. Update service Helm values to enable OAuth"
echo ""

if [ "$OUTPUT_FILE" != "" ]; then
  echo "Credentials saved to: $OUTPUT_FILE"
  echo "Store this file securely and delete after noting credentials!"
fi
