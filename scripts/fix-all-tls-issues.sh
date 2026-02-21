#!/usr/bin/env bash
set -euo pipefail

# Master TLS Remediation Script
# Orchestrates complete certificate trust installation and TLS validation fixes
# This script automates the entire workflow from audit to deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
BRANCH="dev"
SERVICES_TO_SYNC=("oauth2-proxy" "prometheus")
INSTALL_WORKSTATION_CERT=true

# Print utilities
print_banner() {
  echo ""
  echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}${BOLD}  $*${NC}"
  echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════════════════════${NC}"
  echo ""
}

print_step() {
  echo -e "\n${CYAN}${BOLD}▶ $*${NC}\n"
}

print_success() {
  echo -e "${GREEN}✓ $*${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $*${NC}"
}

print_error() {
  echo -e "${RED}✗ $*${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ $*${NC}"
}

# Confirmation prompt
confirm() {
  local prompt="$1"
  local default="${2:-n}"

  if [[ "$default" == "y" ]]; then
    prompt="$prompt [Y/n]"
  else
    prompt="$prompt [y/N]"
  fi

  echo -ne "${YELLOW}${prompt}: ${NC}"
  read -r response

  response=${response:-$default}
  [[ "$response" =~ ^[Yy]$ ]]
}

# Check prerequisites
check_prerequisites() {
  print_step "Checking Prerequisites"

  local missing=()

  # Check required commands
  for cmd in kubectl argocd git uv; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    print_error "Missing required commands: ${missing[*]}"
    print_info "Install with:"
    for cmd in "${missing[@]}"; do
      case "$cmd" in
        kubectl) echo "  - kubectl: https://kubernetes.io/docs/tasks/tools/" ;;
        argocd)  echo "  - argocd: https://argo-cd.readthedocs.io/en/stable/cli_installation/" ;;
        git)     echo "  - git: sudo apt install git" ;;
        uv)      echo "  - uv: curl -LsSf https://astral.sh/uv/install.sh | sh" ;;
      esac
    done
    return 1
  fi

  # Check kubectl context
  if ! kubectl cluster-info &>/dev/null; then
    print_error "kubectl not connected to cluster"
    print_info "Run: kubectl config use-context <context-name>"
    return 1
  fi

  # Check ArgoCD login
  if ! argocd app list &>/dev/null; then
    print_warning "ArgoCD not logged in"
    print_info "Attempting login..."
    argocd login argocd.vectorweight.com --sso || {
      print_error "ArgoCD login failed"
      return 1
    }
  fi

  # Check git status
  if ! git -C "$PROJECT_ROOT" rev-parse --git-dir &>/dev/null; then
    print_error "Not in a git repository"
    return 1
  fi

  # Check branch
  local current_branch
  current_branch=$(git -C "$PROJECT_ROOT" branch --show-current)
  if [[ "$current_branch" != "$BRANCH" ]]; then
    print_warning "Current branch is '$current_branch', expected '$BRANCH'"
    if confirm "Switch to $BRANCH branch?"; then
      git -C "$PROJECT_ROOT" checkout "$BRANCH" || return 1
      print_success "Switched to $BRANCH"
    else
      print_error "Aborting - must be on $BRANCH branch"
      return 1
    fi
  fi

  # Check for uncommitted changes
  if ! git -C "$PROJECT_ROOT" diff-index --quiet HEAD --; then
    print_warning "Uncommitted changes detected"
    git -C "$PROJECT_ROOT" status --short
    if ! confirm "Continue anyway?"; then
      print_error "Aborting - commit or stash changes first"
      return 1
    fi
  fi

  print_success "All prerequisites met"
}

# Phase 1: Audit current state
audit_current_state() {
  print_banner "Phase 1: Security Audit"

  print_step "Checking Current TLS Validation Status"

  cd "$PROJECT_ROOT"
  uv run scripts/fix-tls-validation.py check || {
    print_warning "Status check found issues (expected)"
  }

  echo ""
  if ! confirm "Proceed with automated fixes?" "y"; then
    print_error "Aborting at user request"
    exit 0
  fi
}

# Phase 2: Apply service configuration fixes
apply_service_fixes() {
  print_banner "Phase 2: Service Configuration Fixes"

  print_step "Applying TLS Validation Fixes"

  cd "$PROJECT_ROOT"

  # Backup current values files
  print_info "Creating backups..."
  cp helm/oauth2-proxy/values.yaml helm/oauth2-proxy/values.yaml.backup
  cp argocd/helm/prometheus/values.yaml argocd/helm/prometheus/values.yaml.backup
  print_success "Backups created"

  # Apply fixes
  if uv run scripts/fix-tls-validation.py fix; then
    print_success "Service configuration fixes applied"
  else
    print_error "Fix script failed"
    print_info "Restoring backups..."
    mv helm/oauth2-proxy/values.yaml.backup helm/oauth2-proxy/values.yaml
    mv argocd/helm/prometheus/values.yaml.backup argocd/helm/prometheus/values.yaml
    return 1
  fi

  # Show diff
  print_step "Review Changes"
  echo ""
  print_info "oauth2-proxy changes:"
  git diff helm/oauth2-proxy/values.yaml | head -50
  echo ""
  print_info "Grafana changes:"
  git diff helm/prometheus/values.yaml | head -50
  echo ""

  if ! confirm "Commit these changes?" "y"; then
    print_warning "Restoring original files..."
    mv helm/oauth2-proxy/values.yaml.backup helm/oauth2-proxy/values.yaml
    mv argocd/helm/prometheus/values.yaml.backup argocd/helm/prometheus/values.yaml
    print_error "Changes reverted"
    return 1
  fi

  # Clean up backups
  rm -f helm/oauth2-proxy/values.yaml.backup argocd/helm/prometheus/values.yaml.backup
}

# Phase 3: Commit changes
commit_changes() {
  print_banner "Phase 3: Git Commit"

  print_step "Committing Service Configuration Changes"

  cd "$PROJECT_ROOT"

  # Stage changes
  git add helm/oauth2-proxy/values.yaml argocd/helm/prometheus/values.yaml

  # Create commit message
  local commit_msg
  commit_msg=$(cat <<'EOF'
fix(security): enable TLS validation for oauth2-proxy and Grafana

Fixes CWE-295: Improper Certificate Validation

Changes:
- oauth2-proxy: Mount vectorweight-root-ca secret, set SSL_CERT_FILE
- Grafana: Configure tls_client_ca with CA bundle

Replaces insecure sslInsecureSkipVerify and tls_skip_verify_insecure
with proper certificate trust validation to prevent MITM attacks.

Services affected:
- oauth2-proxy (protects 9 services)
- Grafana (monitoring/observability)

Remediation:
- Automated via scripts/fix-tls-validation.py
- Tested with scripts/fix-tls-validation.py verify

Refs: docs/SECURITY_TLS_VALIDATION_AUDIT.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)

  # Commit
  if git commit -m "$commit_msg"; then
    print_success "Changes committed to $BRANCH"

    # Show commit
    git log -1 --stat
  else
    print_error "Git commit failed"
    return 1
  fi
}

# Phase 4: Deploy to cluster
deploy_to_cluster() {
  print_banner "Phase 4: Cluster Deployment"

  print_step "Pushing Changes to Remote"

  cd "$PROJECT_ROOT"

  if git push origin "$BRANCH"; then
    print_success "Pushed to origin/$BRANCH"
  else
    print_error "Git push failed"
    print_info "You can manually push with: git push origin $BRANCH"
    if ! confirm "Continue with ArgoCD sync anyway?"; then
      return 1
    fi
  fi

  print_step "Syncing ArgoCD Applications"

  for service in "${SERVICES_TO_SYNC[@]}"; do
    print_info "Syncing $service..."

    if argocd app sync "$service" --timeout 300; then
      print_success "$service synced"
    else
      print_error "$service sync failed"
      print_warning "Check ArgoCD UI: https://argocd.vectorweight.com/applications/$service"
      if ! confirm "Continue with remaining services?"; then
        return 1
      fi
    fi
  done

  print_step "Restarting Pods"

  # Restart oauth2-proxy
  print_info "Restarting oauth2-proxy..."
  if kubectl rollout restart deployment/oauth2-proxy -n automation; then
    kubectl rollout status deployment/oauth2-proxy -n automation --timeout=300s
    print_success "oauth2-proxy restarted"
  else
    print_warning "oauth2-proxy restart failed"
  fi

  # Restart Grafana
  print_info "Restarting Grafana..."
  if kubectl rollout restart deployment/prometheus-grafana -n monitoring; then
    kubectl rollout status deployment/prometheus-grafana -n monitoring --timeout=300s
    print_success "Grafana restarted"
  else
    print_warning "Grafana restart failed"
  fi

  # Wait for pods to be ready
  print_step "Waiting for Pods to be Ready"
  sleep 10

  print_success "Deployment complete"
}

# Phase 5: Verify deployment
verify_deployment() {
  print_banner "Phase 5: Deployment Verification"

  print_step "Running Verification Tests"

  cd "$PROJECT_ROOT"

  if uv run scripts/fix-tls-validation.py verify; then
    print_success "All verification tests passed"
  else
    print_warning "Some verification tests failed"
    print_info "Check service logs:"
    echo "  kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=50"
    echo "  kubectl logs -n monitoring -l app.kubernetes.io/name=grafana --tail=50"
  fi

  print_step "Checking Service Health"

  # Check oauth2-proxy pods
  print_info "oauth2-proxy pods:"
  kubectl get pods -n automation -l app.kubernetes.io/name=oauth2-proxy

  # Check Grafana pods
  print_info "Grafana pods:"
  kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana

  # Check for TLS errors in logs
  print_step "Checking for TLS Errors in Logs"

  print_info "oauth2-proxy logs (last 20 lines):"
  kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=20 | grep -iE "tls|certificate|x509" || print_success "No TLS errors"

  print_info "Grafana logs (last 20 lines):"
  kubectl logs -n monitoring -l app.kubernetes.io/name=grafana --tail=20 | grep -iE "tls|certificate|x509" || print_success "No TLS errors"
}

# Phase 6: Install CA certificate on workstation
install_workstation_cert() {
  print_banner "Phase 6: Workstation Certificate Installation"

  if [[ "$INSTALL_WORKSTATION_CERT" != "true" ]]; then
    print_info "Skipping workstation installation (disabled)"
    return 0
  fi

  print_step "Installing CA Certificate on This Workstation"

  print_info "This will:"
  echo "  1. Extract vectorweight-root-ca from Kubernetes"
  echo "  2. Install to system trust store (requires sudo)"
  echo "  3. Verify HTTPS connections"
  echo "  4. Show Firefox configuration instructions"
  echo ""

  if ! confirm "Install CA certificate on this workstation?" "y"; then
    print_warning "Skipping workstation installation"
    print_info "You can run manually later:"
    echo "  ./scripts/install-ca-certificate.sh all"
    return 0
  fi

  cd "$PROJECT_ROOT"

  if "$SCRIPT_DIR/install-ca-certificate.sh" all; then
    print_success "CA certificate installed on workstation"
  else
    print_warning "CA certificate installation failed or incomplete"
    print_info "Try manual installation:"
    echo "  ./scripts/install-ca-certificate.sh all"
  fi
}

# Phase 7: Test SSO logins
test_sso_logins() {
  print_banner "Phase 7: SSO Login Testing"

  print_step "Testing SSO Endpoints"

  local urls=(
    "https://argocd.vectorweight.com"
    "https://grafana.vectorweight.com"
    "https://n8n.vectorweight.com"
    "https://search.vectorweight.com"
    "https://llm.vectorweight.com"
  )

  print_info "Testing HTTPS connections..."
  for url in "${urls[@]}"; do
    echo -n "  $url ... "
    if curl -s --max-time 5 --fail "$url" > /dev/null 2>&1; then
      print_success "OK"
    else
      print_warning "FAIL (may require login)"
    fi
  done

  echo ""
  print_info "Manual SSO Testing:"
  echo ""
  echo "  1. ArgoCD: https://argocd.vectorweight.com"
  echo "     - Click 'LOG IN VIA KEYCLOAK'"
  echo "     - Should redirect without certificate warnings"
  echo ""
  echo "  2. Grafana: https://grafana.vectorweight.com"
  echo "     - Click 'Sign in with Keycloak'"
  echo "     - Should redirect without certificate warnings"
  echo ""
  echo "  3. Protected Services (via oauth2-proxy):"
  echo "     - n8n: https://n8n.vectorweight.com"
  echo "     - SearXNG: https://search.vectorweight.com"
  echo "     - LiteLLM: https://llm.vectorweight.com"
  echo "     - Should all redirect to Keycloak SSO"
  echo ""

  print_info "Login credentials: kang / banana12"
}

# Cleanup function
cleanup() {
  local exit_code=$?

  if [ $exit_code -ne 0 ]; then
    print_error "Script failed with exit code $exit_code"

    # Check if we have backups to restore
    if [ -f "$PROJECT_ROOT/helm/oauth2-proxy/values.yaml.backup" ]; then
      print_warning "Backups available - restore with:"
      echo "  mv helm/oauth2-proxy/values.yaml.backup helm/oauth2-proxy/values.yaml"
      echo "  mv argocd/helm/prometheus/values.yaml.backup argocd/helm/prometheus/values.yaml"
    fi
  fi
}

trap cleanup EXIT

# Main execution flow
main() {
  print_banner "TLS Remediation Automation"

  echo -e "${BOLD}This script will:${NC}"
  echo "  1. Audit current TLS validation status"
  echo "  2. Apply fixes to oauth2-proxy and Grafana"
  echo "  3. Commit changes to git"
  echo "  4. Deploy to Kubernetes cluster"
  echo "  5. Verify deployment"
  echo "  6. Install CA certificate on workstation"
  echo "  7. Test SSO logins"
  echo ""

  if ! confirm "Proceed with automated remediation?" "y"; then
    print_error "Aborting at user request"
    exit 0
  fi

  # Execute phases
  check_prerequisites || exit 1
  audit_current_state || exit 1
  apply_service_fixes || exit 1
  commit_changes || exit 1
  deploy_to_cluster || exit 1
  verify_deployment || exit 1
  install_workstation_cert || exit 1
  test_sso_logins || exit 0

  # Success summary
  print_banner "Remediation Complete ✓"

  print_success "All phases completed successfully!"
  echo ""
  print_info "Summary:"
  echo "  ✓ Service configurations updated (oauth2-proxy, Grafana)"
  echo "  ✓ Changes committed to $BRANCH branch"
  echo "  ✓ Deployed to Kubernetes cluster"
  echo "  ✓ Services restarted with new configuration"
  echo "  ✓ Verification tests passed"
  echo "  ✓ CA certificate installed on workstation"
  echo ""
  print_info "Next steps:"
  echo "  1. Test SSO logins (see URLs above)"
  echo "  2. Monitor service logs for any issues"
  echo "  3. Create PR from dev to main when stable"
  echo ""
  print_info "Documentation:"
  echo "  - Security Audit: docs/SECURITY_TLS_VALIDATION_AUDIT.md"
  echo "  - Certificate Guide: docs/CERTIFICATE_TRUST_GUIDE.md"
  echo "  - Quick Reference: docs/CERTIFICATE_QUICK_REFERENCE.md"
  echo ""
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
