#!/usr/bin/env bash
# =============================================================================
# Self-Hosted AI Stack - ArgoCD Bootstrap Script
# =============================================================================
# This script bootstraps ArgoCD and deploys the entire self-hosted AI stack
# using GitOps patterns with the App-of-Apps approach.
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - helm v3.x installed
#   - kubeseal (optional, for sealing secrets)
#
# Usage:
#   ./scripts/bootstrap-argocd.sh [--skip-argocd] [--skip-secrets]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
ARGOCD_NAMESPACE="argocd"
ARGOCD_VERSION="7.7.7"
GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/tzervas/self-hosted-ai.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"

# Flags
SKIP_ARGOCD=false
SKIP_SECRETS=false
INSTALL_SEALED_SECRETS=true

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
        --skip-argocd)
            SKIP_ARGOCD=true
            shift
            ;;
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        --no-sealed-secrets)
            INSTALL_SEALED_SECRETS=false
            shift
            ;;
        --repo)
            GIT_REPO_URL="$2"
            shift 2
            ;;
        --branch)
            GIT_BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--skip-argocd] [--skip-secrets] [--no-sealed-secrets] [--repo <url>] [--branch <branch>]"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Preflight Checks
# =============================================================================

log_step "Running preflight checks..."

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl first."
    exit 1
fi

# Check helm
if ! command -v helm &> /dev/null; then
    log_error "helm not found. Please install helm first."
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    exit 1
fi

log_success "Preflight checks passed!"

# =============================================================================
# Install ArgoCD
# =============================================================================

if [[ "$SKIP_ARGOCD" == "false" ]]; then
    log_step "Installing ArgoCD..."
    
    # Add ArgoCD helm repo
    helm repo add argo https://argoproj.github.io/argo-helm 2>/dev/null || true
    helm repo update
    
    # Create namespace
    kubectl create namespace "$ARGOCD_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Install ArgoCD
    helm upgrade --install argocd argo/argo-cd \
        --namespace "$ARGOCD_NAMESPACE" \
        --version "$ARGOCD_VERSION" \
        --set server.ingress.enabled=true \
        --set server.ingress.ingressClassName=traefik \
        --set server.ingress.hosts[0]=argocd.homelab.local \
        --set server.ingress.tls[0].hosts[0]=argocd.homelab.local \
        --set server.ingress.tls[0].secretName=argocd-tls \
        --set configs.params.server\\.insecure=true \
        --set redis.resources.requests.cpu=100m \
        --set redis.resources.requests.memory=128Mi \
        --set server.resources.requests.cpu=100m \
        --set server.resources.requests.memory=256Mi \
        --set controller.resources.requests.cpu=250m \
        --set controller.resources.requests.memory=512Mi \
        --set repoServer.resources.requests.cpu=100m \
        --set repoServer.resources.requests.memory=256Mi \
        --wait --timeout 10m
    
    log_success "ArgoCD installed!"
    
    # Wait for ArgoCD to be ready
    log_info "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available deployment/argocd-server \
        -n "$ARGOCD_NAMESPACE" --timeout=300s
    
    # Get initial admin password
    ARGOCD_PASSWORD=$(kubectl -n "$ARGOCD_NAMESPACE" get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
    log_success "ArgoCD is ready!"
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────────────┐"
    echo "│ ArgoCD Admin Credentials                                                │"
    echo "├─────────────────────────────────────────────────────────────────────────┤"
    echo "│ URL:      https://argocd.homelab.local (or port-forward below)          │"
    echo "│ Username: admin                                                          │"
    echo "│ Password: ${ARGOCD_PASSWORD}"
    echo "│                                                                          │"
    echo "│ Port-forward: kubectl port-forward svc/argocd-server -n argocd 8080:443  │"
    echo "└─────────────────────────────────────────────────────────────────────────┘"
    echo ""
else
    log_info "Skipping ArgoCD installation (--skip-argocd)"
fi

# =============================================================================
# Install SealedSecrets Controller
# =============================================================================

if [[ "$INSTALL_SEALED_SECRETS" == "true" ]]; then
    log_step "Installing SealedSecrets controller..."
    
    helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets 2>/dev/null || true
    helm repo update
    
    helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
        --namespace kube-system \
        --set fullnameOverride=sealed-secrets-controller \
        --set resources.requests.cpu=50m \
        --set resources.requests.memory=64Mi \
        --wait --timeout 5m
    
    log_success "SealedSecrets controller installed!"
    
    # Wait for controller to be ready
    kubectl wait --for=condition=available deployment/sealed-secrets-controller \
        -n kube-system --timeout=120s
fi

# =============================================================================
# Generate and Apply Secrets
# =============================================================================

if [[ "$SKIP_SECRETS" == "false" ]]; then
    log_step "Generating and applying secrets..."
    
    # Run the secrets generation script
    "${SCRIPT_DIR}/generate-secrets.sh"
    
    log_success "Secrets generated and applied!"
else
    log_info "Skipping secrets generation (--skip-secrets)"
fi

# =============================================================================
# Deploy App-of-Apps Root Application
# =============================================================================

log_step "Deploying App-of-Apps root application..."

# Create the root application
cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-apps
  namespace: ${ARGOCD_NAMESPACE}
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: ${GIT_REPO_URL}
    targetRevision: ${GIT_BRANCH}
    path: argocd/applications
    directory:
      recurse: false
      include: '*.yaml'
  destination:
    server: https://kubernetes.default.svc
    namespace: ${ARGOCD_NAMESPACE}
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
EOF

log_success "App-of-Apps root application deployed!"

# =============================================================================
# Final Summary
# =============================================================================

echo ""
echo "============================================================================="
echo "                   SELF-HOSTED AI STACK BOOTSTRAP COMPLETE"
echo "============================================================================="
echo ""
echo "ArgoCD will now automatically sync and deploy all applications in order:"
echo ""
echo "  Wave -2: SealedSecrets (secret infrastructure)"
echo "  Wave  0: PostgreSQL, Redis (databases)"
echo "  Wave  1: GPU Operator, Traefik (infrastructure)"
echo "  Wave  2: Prometheus stack (monitoring)"
echo "  Wave  3: GitLab (source control)"
echo "  Wave  4: Dify, SearXNG (AI platforms)"
echo "  Wave  5: Ollama, LiteLLM (AI inference)"
echo "  Wave  6: Open WebUI, n8n (user applications)"
echo ""
echo "Monitor deployment progress:"
echo "  kubectl get applications -n argocd"
echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo ""
echo "============================================================================="
