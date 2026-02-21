#!/usr/bin/env bash
# seal-oidc-secrets.sh
# Converts existing OIDC K8s secrets to SealedSecrets for GitOps storage
#
# Prerequisites:
# - kubeseal CLI installed (brew install kubeseal OR https://github.com/bitnami-labs/sealed-secrets/releases)
# - kubectl configured with cluster access
# - sealed-secrets-controller deployed in kube-system namespace (should already exist per sync wave -2)
# - OIDC secrets created via scripts/setup-keycloak-realm.sh
#
# Usage:
#   ./scripts/seal-oidc-secrets.sh
#
# Output:
#   argocd/sealed-secrets/*-oidc-secret.yaml (committed to Git)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SEALED_SECRETS_DIR="$PROJECT_ROOT/argocd/sealed-secrets"

echo "🔐 Sealing OIDC secrets for GitOps storage..."
echo

# Ensure sealed-secrets directory exists
mkdir -p "$SEALED_SECRETS_DIR"

# List of OIDC secrets to seal (namespace:secret-name)
SECRETS=(
  "ai-services:keycloak-oidc-secret"
  "monitoring:grafana-oidc-secret"
  "gitlab:gitlab-oidc-secret"
  "gitlab:gitlab-oidc-provider"
  "automation:n8n-oidc-secret"
  "ai-services:searxng-oidc-secret"
  "ai-services:litellm-oidc-secret"
  "traefik:traefik-oidc-secret"
  "dify:dify-oidc-secret"
  "monitoring:prometheus-oidc-secret"
  "longhorn-system:longhorn-oidc-secret"
  "ana:ana-oidc-secret"
  "argocd:argocd-oidc-secret"
)

# Seal each secret
for SECRET_REF in "${SECRETS[@]}"; do
  NAMESPACE="${SECRET_REF%%:*}"
  SECRET_NAME="${SECRET_REF##*:}"
  OUTPUT_FILE="$SEALED_SECRETS_DIR/${SECRET_NAME}.yaml"

  echo "📦 Sealing $NAMESPACE/$SECRET_NAME..."

  # Check if secret exists
  if ! kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" &>/dev/null; then
    echo "  ⚠️  Secret does not exist, skipping (run setup-keycloak-realm.sh first)"
    continue
  fi

  # Get the secret and seal it
  kubectl get secret "$SECRET_NAME" -n "$NAMESPACE" -o yaml \
    | kubeseal -o yaml \
    > "$OUTPUT_FILE"

  echo "  ✅ Sealed → $OUTPUT_FILE"
done

echo
echo "✅ All OIDC secrets sealed successfully!"
echo
echo "Next steps:"
echo "  1. Review sealed secrets: ls -lh $SEALED_SECRETS_DIR/*-oidc-secret.yaml"
echo "  2. Commit to Git: git add argocd/sealed-secrets/ && git commit -m 'feat(sso): seal OIDC secrets for GitOps'"
echo "  3. Push to trigger ArgoCD sync: git push origin dev"
echo
echo "Note: Sealed secrets are encrypted with the cluster's public key."
echo "Only the sealed-secrets-controller in your cluster can decrypt them."
echo "Safe to commit to public repositories."
