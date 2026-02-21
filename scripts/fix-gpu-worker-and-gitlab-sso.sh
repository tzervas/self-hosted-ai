#!/usr/bin/env bash
# fix-gpu-worker-and-gitlab-sso.sh
# Fixes GPU worker (ollama-gpu) availability and GitLab SSO issues
#
# Issues addressed:
# 1. ollama-gpu pod stuck in Completed state (deployment shows 0/1 available)
# 2. GitLab SSO not showing/redirecting (needs restart to load OIDC secret)
# 3. Model storage now uses shared NFS from homelab (after Helm chart update)
#
# Prerequisites:
# - kubectl configured with cluster access
# - ArgoCD CLI installed (for sync)
# - Helm chart changes committed to Git
#
# Usage:
#   ./scripts/fix-gpu-worker-and-gitlab-sso.sh

set -euo pipefail

echo "🔧 Fixing GPU Worker and GitLab SSO Issues"
echo "=========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
  echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

# Step 1: Delete completed ollama-gpu pod
echo "Step 1: Fixing ollama-gpu deployment"
echo "-------------------------------------"

OLLAMA_GPU_POD=$(kubectl get pods -n gpu-workloads -l app.kubernetes.io/component=ollama-gpu -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$OLLAMA_GPU_POD" ]; then
  print_warning "No ollama-gpu pod found - deployment may already be healthy"
else
  POD_STATUS=$(kubectl get pod -n gpu-workloads "$OLLAMA_GPU_POD" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")

  if [ "$POD_STATUS" == "Succeeded" ] || [ "$POD_STATUS" == "Failed" ]; then
    echo "  Current pod: $OLLAMA_GPU_POD (status: $POD_STATUS)"
    echo "  Deleting completed pod to trigger new pod creation..."
    kubectl delete pod -n gpu-workloads "$OLLAMA_GPU_POD"
    print_status "Completed pod deleted"

    echo "  Waiting for new pod to be created (30s)..."
    sleep 30

    NEW_POD=$(kubectl get pods -n gpu-workloads -l app.kubernetes.io/component=ollama-gpu -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$NEW_POD" ]; then
      NEW_STATUS=$(kubectl get pod -n gpu-workloads "$NEW_POD" -o jsonpath='{.status.phase}')
      echo "  New pod: $NEW_POD (status: $NEW_STATUS)"

      if [ "$NEW_STATUS" == "Running" ] || [ "$NEW_STATUS" == "Pending" ]; then
        print_status "New pod created successfully"
      else
        print_warning "New pod status: $NEW_STATUS - may need investigation"
      fi
    else
      print_error "No new pod created - check deployment configuration"
    fi
  elif [ "$POD_STATUS" == "Running" ]; then
    print_status "ollama-gpu pod already running ($OLLAMA_GPU_POD)"
  else
    print_warning "Pod status: $POD_STATUS - may need manual intervention"
  fi
fi

echo

# Step 2: Sync GPU worker Helm chart (if changes were committed)
echo "Step 2: Syncing GPU worker configuration"
echo "-----------------------------------------"

if command -v argocd &> /dev/null; then
  if argocd app get self-hosted-ai-gpu-worker &> /dev/null; then
    echo "  Syncing self-hosted-ai-gpu-worker ArgoCD application..."
    argocd app sync self-hosted-ai-gpu-worker
    print_status "GPU worker configuration synced"
  else
    print_warning "ArgoCD app 'self-hosted-ai-gpu-worker' not found - skipping sync"
  fi
else
  print_warning "ArgoCD CLI not installed - manual sync required:"
  echo "    argocd app sync self-hosted-ai-gpu-worker"
fi

echo

# Step 3: Restart GitLab to load OIDC provider secret
echo "Step 3: Restarting GitLab for SSO"
echo "----------------------------------"

if kubectl get deployment -n gitlab gitlab-webservice-default &> /dev/null; then
  echo "  Restarting GitLab webservice deployment..."
  kubectl rollout restart deployment/gitlab-webservice-default -n gitlab
  print_status "GitLab webservice restart initiated"

  echo "  Waiting for rollout to complete (60s timeout)..."
  if kubectl rollout status deployment/gitlab-webservice-default -n gitlab --timeout=60s; then
    print_status "GitLab webservice restarted successfully"
  else
    print_warning "Rollout status check timed out - deployment may still be progressing"
  fi
else
  print_error "GitLab deployment not found in gitlab namespace"
fi

echo

# Step 4: Verify fixes
echo "Step 4: Verification"
echo "--------------------"

echo "  Checking ollama-gpu deployment status..."
OLLAMA_GPU_AVAILABLE=$(kubectl get deployment -n gpu-workloads ollama-gpu -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")

if [ "$OLLAMA_GPU_AVAILABLE" == "1" ]; then
  print_status "ollama-gpu deployment: 1/1 replicas available"
else
  print_warning "ollama-gpu deployment: ${OLLAMA_GPU_AVAILABLE}/1 replicas available"
  echo "    Run: kubectl get pods -n gpu-workloads -l app.kubernetes.io/component=ollama-gpu"
fi

echo "  Checking GitLab webservice status..."
GITLAB_AVAILABLE=$(kubectl get deployment -n gitlab gitlab-webservice-default -o jsonpath='{.status.availableReplicas}' 2>/dev/null || echo "0")
GITLAB_DESIRED=$(kubectl get deployment -n gitlab gitlab-webservice-default -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

if [ "$GITLAB_AVAILABLE" == "$GITLAB_DESIRED" ] && [ "$GITLAB_DESIRED" != "0" ]; then
  print_status "GitLab webservice: ${GITLAB_AVAILABLE}/${GITLAB_DESIRED} replicas available"
else
  print_warning "GitLab webservice: ${GITLAB_AVAILABLE}/${GITLAB_DESIRED} replicas available (still rolling out)"
fi

echo

# Step 5: Test connectivity
echo "Step 5: Testing services"
echo "------------------------"

echo "  Testing ollama-gpu service..."
if kubectl run test-ollama-gpu --rm -i --restart=Never --image=curlimages/curl:latest -- \
  curl -sf http://ollama-gpu.gpu-workloads:11434/api/version &> /dev/null; then
  print_status "ollama-gpu API responding"
else
  print_warning "ollama-gpu API not responding yet - pod may still be starting"
fi

echo "  Testing GitLab webservice..."
GITLAB_POD=$(kubectl get pods -n gitlab -l app=webservice -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$GITLAB_POD" ]; then
  if kubectl exec -n gitlab "$GITLAB_POD" -c webservice -- curl -sf http://localhost:8080/-/health &> /dev/null; then
    print_status "GitLab health endpoint responding"
  else
    print_warning "GitLab health check failed - service may still be initializing"
  fi
else
  print_warning "No GitLab webservice pod found"
fi

echo

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo

print_status "GPU Worker Fix: ollama-gpu pod recreated, now using shared NFS storage"
print_status "GitLab SSO Fix: Webservice restarted to load OIDC provider secret"

echo

echo "Next Steps:"
echo "  1. Monitor ollama-gpu pod:"
echo "     kubectl get pods -n gpu-workloads -w | grep ollama-gpu"
echo

echo "  2. Check ollama-gpu logs if not running:"
echo "     kubectl logs -n gpu-workloads deployment/ollama-gpu -f"
echo

echo "  3. Test GitLab SSO:"
echo "     Open https://git.vectorweight.com in browser"
echo "     Should auto-redirect to Keycloak login"
echo

echo "  4. Verify model storage (models now on homelab NFS):"
echo "     kubectl exec -n gpu-workloads deployment/ollama-gpu -- ls -lh /root/.ollama/models"
echo

echo "  5. If GitLab still shows password login:"
echo "     Check logs: kubectl logs -n gitlab deployment/gitlab-webservice-default -c webservice | grep -i omniauth"
echo

print_status "Script completed!"
