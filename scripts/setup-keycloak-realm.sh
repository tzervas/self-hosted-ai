#!/usr/bin/env bash
# =============================================================================
# Keycloak Realm & OIDC Client Setup
# =============================================================================
# Creates the 'vectorweight' realm and OIDC clients for all services.
# Run AFTER Keycloak is up and accessible with the admin password.
#
# Prerequisites:
#   - Keycloak running at https://auth.vectorweight.com
#   - Admin password set (Phase B dev password or production secret)
#   - jq and curl installed
#
# Usage:
#   ./scripts/setup-keycloak-realm.sh
#   ./scripts/setup-keycloak-realm.sh --password <admin-password>
# =============================================================================

set -euo pipefail

KEYCLOAK_URL="https://auth.vectorweight.com"
ADMIN_USER="admin"
ADMIN_PASSWORD="${1:-ChangeMe123}"
REALM="vectorweight"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --password)
      ADMIN_PASSWORD="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

echo "=============================================="
echo "  Keycloak Realm & OIDC Client Setup"
echo "=============================================="
echo "  Keycloak: $KEYCLOAK_URL"
echo "  Realm:    $REALM"
echo ""

# 1. Get admin token
echo "[1/6] Authenticating as admin..."
TOKEN=$(curl -sf -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" \
  -d "username=${ADMIN_USER}" \
  -d "password=${ADMIN_PASSWORD}" \
  -d "grant_type=password" \
  | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "ERROR: Failed to authenticate. Is Keycloak running and password correct?"
  exit 1
fi
echo "  Authenticated successfully."

# 2. Create realm
echo "[2/6] Creating realm '${REALM}'..."
REALM_EXISTS=$(curl -sf -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}")

if [ "$REALM_EXISTS" = "200" ]; then
  echo "  Realm already exists, skipping."
else
  curl -sf -X POST "${KEYCLOAK_URL}/admin/realms" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "realm": "'"${REALM}"'",
      "enabled": true,
      "displayName": "VectorWeight",
      "registrationAllowed": false,
      "loginWithEmailAllowed": true,
      "duplicateEmailsAllowed": false,
      "resetPasswordAllowed": true,
      "editUsernameAllowed": false,
      "bruteForceProtected": true,
      "sslRequired": "external",
      "accessTokenLifespan": 300,
      "ssoSessionIdleTimeout": 1800,
      "ssoSessionMaxLifespan": 36000
    }'
  echo "  Realm created."
fi

# Helper function to create OIDC client
create_oidc_client() {
  local CLIENT_ID="$1"
  local REDIRECT_URI="$2"
  local CLIENT_NAME="$3"

  echo "  Creating client '${CLIENT_ID}'..."

  # Check if client exists
  EXISTING=$(curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" \
    | jq 'length')

  if [ "$EXISTING" -gt 0 ]; then
    echo "    Client already exists, skipping."
    return
  fi

  curl -sf -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "clientId": "'"${CLIENT_ID}"'",
      "name": "'"${CLIENT_NAME}"'",
      "enabled": true,
      "protocol": "openid-connect",
      "publicClient": false,
      "clientAuthenticatorType": "client-secret",
      "standardFlowEnabled": true,
      "directAccessGrantsEnabled": false,
      "serviceAccountsEnabled": false,
      "redirectUris": ["'"${REDIRECT_URI}"'"],
      "webOrigins": ["+"],
      "attributes": {
        "post.logout.redirect.uris": "+"
      }
    }'
  echo "    Created."
}

# 3. Create OIDC clients
echo "[3/6] Creating OIDC clients..."
create_oidc_client "open-webui" "https://ai.vectorweight.com/oauth/oidc/callback" "Open WebUI"
create_oidc_client "grafana" "https://grafana.vectorweight.com/login/generic_oauth" "Grafana"
create_oidc_client "gitlab" "https://git.vectorweight.com/users/auth/openid_connect/callback" "GitLab"
create_oidc_client "n8n" "https://n8n.vectorweight.com/oauth2/callback" "n8n (oauth2-proxy)"
create_oidc_client "searxng" "https://search.vectorweight.com/oauth2/callback" "SearXNG (oauth2-proxy)"
create_oidc_client "litellm" "https://llm.vectorweight.com/oauth2/callback" "LiteLLM (oauth2-proxy)"
create_oidc_client "traefik" "https://traefik.vectorweight.com/oauth2/callback" "Traefik (oauth2-proxy)"
create_oidc_client "dify" "https://dify.vectorweight.com/oauth2/callback" "Dify (oauth2-proxy)"
create_oidc_client "prometheus" "https://prometheus.vectorweight.com/oauth2/callback" "Prometheus (oauth2-proxy)"
create_oidc_client "longhorn" "https://longhorn.vectorweight.com/oauth2/callback" "Longhorn (oauth2-proxy)"
create_oidc_client "ana-agent" "https://ana.vectorweight.com/auth/keycloak/callback" "aNa Agent"

# 4. Retrieve client secrets
echo "[4/6] Retrieving client secrets..."

get_client_secret() {
  local CLIENT_ID="$1"
  local INTERNAL_ID
  INTERNAL_ID=$(curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" \
    | jq -r '.[0].id')

  curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/clients/${INTERNAL_ID}/client-secret" \
    | jq -r '.value'
}

OPENWEBUI_SECRET=$(get_client_secret "open-webui")
GRAFANA_SECRET=$(get_client_secret "grafana")
GITLAB_SECRET=$(get_client_secret "gitlab")
N8N_SECRET=$(get_client_secret "n8n")
SEARXNG_SECRET=$(get_client_secret "searxng")
LITELLM_SECRET=$(get_client_secret "litellm")
TRAEFIK_SECRET=$(get_client_secret "traefik")
DIFY_SECRET=$(get_client_secret "dify")
PROMETHEUS_SECRET=$(get_client_secret "prometheus")
LONGHORN_SECRET=$(get_client_secret "longhorn")
ANA_AGENT_SECRET=$(get_client_secret "ana-agent")

# 5. Create admin user in realm
echo "[5/6] Creating admin user 'kang' in '${REALM}' realm..."
USER_EXISTS=$(curl -sf \
  -H "Authorization: Bearer $TOKEN" \
  "${KEYCLOAK_URL}/admin/realms/${REALM}/users?username=kang" \
  | jq 'length')

if [ "$USER_EXISTS" -gt 0 ]; then
  echo "  User 'kang' already exists, skipping."
else
  curl -sf -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/users" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "kang",
      "email": "tz-dev@vectorweight.com",
      "emailVerified": true,
      "enabled": true,
      "firstName": "Kang",
      "lastName": "",
      "credentials": [{
        "type": "password",
        "value": "ChangeMe123",
        "temporary": true
      }]
    }'
  echo "  User 'kang' created (password: 'ChangeMe123', must change on first login)."

  # Assign admin realm role for Grafana/service role mapping
  USER_ID=$(curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/users?username=kang" \
    | jq -r '.[0].id')
  ADMIN_ROLE=$(curl -sf \
    -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/roles/admin")
  curl -sf -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "${KEYCLOAK_URL}/admin/realms/${REALM}/users/${USER_ID}/role-mappings/realm" \
    -d "[${ADMIN_ROLE}]"
  echo "  Assigned 'admin' realm role to kang."
fi

# 6. Create K8s secrets in service namespaces
echo "[6/6] Creating K8s OIDC secrets in service namespaces..."

kubectl create secret generic keycloak-oidc-secret -n ai-services \
  --from-literal=client-id=open-webui \
  --from-literal=client-secret="$OPENWEBUI_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic grafana-oidc-secret -n monitoring \
  --from-literal=client-id=grafana \
  --from-literal=client-secret="$GRAFANA_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic gitlab-oidc-secret -n gitlab \
  --from-literal=client-id=gitlab \
  --from-literal=client-secret="$GITLAB_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic n8n-oidc-secret -n automation \
  --from-literal=client-id=n8n \
  --from-literal=client-secret="$N8N_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic searxng-oidc-secret -n ai-services \
  --from-literal=client-id=searxng \
  --from-literal=client-secret="$SEARXNG_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic litellm-oidc-secret -n ai-services \
  --from-literal=client-id=litellm \
  --from-literal=client-secret="$LITELLM_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic traefik-oidc-secret -n traefik \
  --from-literal=client-id=traefik \
  --from-literal=client-secret="$TRAEFIK_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic dify-oidc-secret -n dify \
  --from-literal=client-id=dify \
  --from-literal=client-secret="$DIFY_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic prometheus-oidc-secret -n monitoring \
  --from-literal=client-id=prometheus \
  --from-literal=client-secret="$PROMETHEUS_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic longhorn-oidc-secret -n longhorn-system \
  --from-literal=client-id=longhorn \
  --from-literal=client-secret="$LONGHORN_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic ana-oidc-secret -n ana \
  --from-literal=client-id=ana-agent \
  --from-literal=client-secret="$ANA_AGENT_SECRET" \
  --from-literal=redirect-uri="https://ana.vectorweight.com/auth/keycloak/callback" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "Client secrets created in cluster:"
echo "  - keycloak-oidc-secret   (ai-services)"
echo "  - grafana-oidc-secret    (monitoring)"
echo "  - gitlab-oidc-secret     (gitlab)"
echo "  - n8n-oidc-secret        (automation)"
echo "  - searxng-oidc-secret    (ai-services)"
echo "  - litellm-oidc-secret    (ai-services)"
echo "  - traefik-oidc-secret    (traefik)"
echo "  - dify-oidc-secret       (dify)"
echo "  - prometheus-oidc-secret  (monitoring)"
echo "  - longhorn-oidc-secret   (longhorn-system)"
echo "  - ana-oidc-secret        (ana)"
echo ""
echo "OIDC Discovery URL:"
echo "  ${KEYCLOAK_URL}/realms/${REALM}/.well-known/openid-configuration"
echo ""
echo "Next steps:"
echo "  1. Verify OIDC discovery: curl ${KEYCLOAK_URL}/realms/${REALM}/.well-known/openid-configuration"
echo "  2. Commit Grafana/GitLab SSO config changes"
echo "  3. Seal secrets for git persistence: kubeseal"
echo "  4. Test login flows for each service"
