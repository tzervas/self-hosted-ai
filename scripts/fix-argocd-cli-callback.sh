#!/usr/bin/env bash
set -euo pipefail

# Fix ArgoCD CLI SSO Callback
# Adds http://localhost:8085/auth/callback to ArgoCD client redirect URIs

KEYCLOAK_POD=$(kubectl get pod -n auth -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')

echo "Adding ArgoCD CLI callback URI to Keycloak client..."

# Get admin credentials
ADMIN_PASSWORD=$(kubectl get secret keycloak-admin-secret -n auth -o jsonpath='{.data.admin-password}' | base64 -d)

# Configure kcadm
kubectl exec -n auth "$KEYCLOAK_POD" -- /opt/bitnami/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password "$ADMIN_PASSWORD"

# Get current ArgoCD client ID
CLIENT_ID=$(kubectl exec -n auth "$KEYCLOAK_POD" -- /opt/bitnami/keycloak/bin/kcadm.sh get clients \
  -r vectorweight \
  -q clientId=argocd \
  --fields id \
  | grep '"id"' | cut -d'"' -f4)

echo "ArgoCD client ID: $CLIENT_ID"

# Get current redirect URIs
echo "Current redirect URIs:"
kubectl exec -n auth "$KEYCLOAK_POD" -- /opt/bitnami/keycloak/bin/kcadm.sh get clients/"$CLIENT_ID" \
  -r vectorweight \
  --fields redirectUris

# Update redirect URIs to include localhost callback
kubectl exec -n auth "$KEYCLOAK_POD" -- /opt/bitnami/keycloak/bin/kcadm.sh update clients/"$CLIENT_ID" \
  -r vectorweight \
  -s 'redirectUris=["https://argocd.vectorweight.com/auth/callback","http://localhost:8085/auth/callback"]'

echo "✓ Added http://localhost:8085/auth/callback to ArgoCD client"

# Verify
echo ""
echo "Updated redirect URIs:"
kubectl exec -n auth "$KEYCLOAK_POD" -- /opt/bitnami/keycloak/bin/kcadm.sh get clients/"$CLIENT_ID" \
  -r vectorweight \
  --fields redirectUris

echo ""
echo "✓ Fix complete!"
echo ""
echo "Now you can retry ArgoCD login:"
echo "  argocd login argocd.vectorweight.com --sso"
