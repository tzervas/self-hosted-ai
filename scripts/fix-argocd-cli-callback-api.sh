#!/usr/bin/env bash
set -euo pipefail

# Fix ArgoCD CLI SSO Callback via REST API
# Adds http://localhost:8085/auth/callback to ArgoCD client redirect URIs

echo "Fixing ArgoCD CLI callback URI via Keycloak REST API..."

KEYCLOAK_POD=$(kubectl get pod -n auth -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')
ADMIN_PASSWORD=$(kubectl get secret keycloak-admin-secret -n auth -o jsonpath='{.data.admin-password}' | base64 -d)

# Get admin access token
echo "Getting admin access token..."
TOKEN=$(kubectl exec -n auth "$KEYCLOAK_POD" -- curl -s -X POST \
  http://localhost:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "Failed to get access token"
  exit 1
fi

echo "✓ Access token obtained"

# Get ArgoCD client
echo "Finding ArgoCD client..."
CLIENTS=$(kubectl exec -n auth "$KEYCLOAK_POD" -- curl -s \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/realms/vectorweight/clients)

CLIENT_ID=$(echo "$CLIENTS" | jq -r '.[] | select(.clientId=="argocd") | .id')

if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" = "null" ]; then
  echo "ArgoCD client not found"
  exit 1
fi

echo "✓ Found ArgoCD client: $CLIENT_ID"

# Get current client config
echo "Getting current redirect URIs..."
CLIENT_CONFIG=$(kubectl exec -n auth "$KEYCLOAK_POD" -- curl -s \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/realms/vectorweight/clients/"$CLIENT_ID")

CURRENT_URIS=$(echo "$CLIENT_CONFIG" | jq -r '.redirectUris[]')
echo "Current redirect URIs:"
echo "$CURRENT_URIS"

# Check if localhost callback already exists
if echo "$CURRENT_URIS" | grep -q "localhost:8085"; then
  echo "✓ Localhost callback already configured"
  exit 0
fi

# Update with both URIs
echo "Adding localhost callback..."
UPDATED_CONFIG=$(echo "$CLIENT_CONFIG" | jq '.redirectUris = ["https://argocd.vectorweight.com/auth/callback", "http://localhost:8085/auth/callback"]')

kubectl exec -n auth "$KEYCLOAK_POD" -- curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPDATED_CONFIG" \
  http://localhost:8080/admin/realms/vectorweight/clients/"$CLIENT_ID" > /dev/null

echo "✓ Updated redirect URIs"

# Verify
echo ""
echo "Verifying update..."
VERIFIED=$(kubectl exec -n auth "$KEYCLOAK_POD" -- curl -s \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/realms/vectorweight/clients/"$CLIENT_ID" \
  | jq -r '.redirectUris[]')

echo "New redirect URIs:"
echo "$VERIFIED"

echo ""
echo "✓ Fix complete!"
echo ""
echo "Now you can retry ArgoCD login:"
echo "  argocd login argocd.vectorweight.com --sso"
