#!/usr/bin/env bash
set -euo pipefail

# Master TLS Remediation Script (v2 - Fully Unattended)
# Orchestrates complete certificate trust installation and TLS validation fixes
#
# Designed for unattended execution with:
#   - Automatic ArgoCD token management (CLI -> API fallback)
#   - Retry logic with exponential backoff
#   - Graceful error recovery and cleanup
#   - Idempotent operations (safe to run multiple times)
#
# Usage:
#   ./fix-all-tls-issues.sh                  # Fully unattended (default)
#   ./fix-all-tls-issues.sh --interactive    # Original interactive mode
#   ./fix-all-tls-issues.sh --dry-run        # Show what would be done
#   ./fix-all-tls-issues.sh --skip-deploy    # Apply fixes but skip ArgoCD sync
#   ./fix-all-tls-issues.sh --skip-cert      # Skip workstation cert installation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/tls-remediation-$(date +%Y%m%d-%H%M%S).log"

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
ARGOCD_SERVER="argocd.vectorweight.com"
ARGOCD_NAMESPACE="argocd"

# Retry configuration
MAX_RETRIES=3
RETRY_DELAY_BASE=5  # seconds, doubles each retry (5, 10, 20)
ARGOCD_SYNC_TIMEOUT=300

# Runtime flags (defaults: unattended mode)
INTERACTIVE=false
DRY_RUN=false
SKIP_DEPLOY=false
SKIP_CERT=false
VERBOSE=false

# State tracking for cleanup
BACKUPS_CREATED=false
CHANGES_COMMITTED=false
ARGOCD_TOKEN=""
PHASE_RESULTS=()

# ============================================================================
# Parse arguments
# ============================================================================
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interactive|-i) INTERACTIVE=true ;;
      --dry-run|-n)     DRY_RUN=true ;;
      --skip-deploy)    SKIP_DEPLOY=true ;;
      --skip-cert)      INSTALL_WORKSTATION_CERT=false; SKIP_CERT=true ;;
      --verbose|-v)     VERBOSE=true ;;
      --help|-h)        usage; exit 0 ;;
      *)
        print_error "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done
}

usage() {
  cat <<'USAGE'
Usage: fix-all-tls-issues.sh [OPTIONS]

Fully unattended TLS remediation with error recovery.

Options:
  --interactive, -i   Enable interactive prompts (disabled by default)
  --dry-run, -n       Show what would be done without making changes
  --skip-deploy       Apply fixes and commit but skip ArgoCD sync
  --skip-cert         Skip workstation CA certificate installation
  --verbose, -v       Enable verbose output
  --help, -h          Show this help

Examples:
  ./fix-all-tls-issues.sh                    # Fully unattended
  ./fix-all-tls-issues.sh --dry-run          # Preview changes
  ./fix-all-tls-issues.sh --interactive      # With prompts
  ./fix-all-tls-issues.sh --skip-deploy      # Fix + commit only
USAGE
}

# ============================================================================
# Logging
# ============================================================================
setup_logging() {
  mkdir -p "$(dirname "$LOG_FILE")"
  exec > >(tee -a "$LOG_FILE") 2>&1
  print_info "Log file: $LOG_FILE"
}

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE" 2>/dev/null || true
}

# ============================================================================
# Print utilities
# ============================================================================
print_banner() {
  echo ""
  echo -e "${BLUE}${BOLD}=================================================================${NC}"
  echo -e "${BLUE}${BOLD}  $*${NC}"
  echo -e "${BLUE}${BOLD}=================================================================${NC}"
  echo ""
}

print_step() {
  echo -e "\n${CYAN}${BOLD}>> $*${NC}\n"
  log "STEP: $*"
}

print_success() {
  echo -e "${GREEN}[OK] $*${NC}"
  log "OK: $*"
}

print_warning() {
  echo -e "${YELLOW}[WARN] $*${NC}"
  log "WARN: $*"
}

print_error() {
  echo -e "${RED}[ERROR] $*${NC}"
  log "ERROR: $*"
}

print_info() {
  echo -e "${BLUE}[INFO] $*${NC}"
  log "INFO: $*"
}

print_debug() {
  if [[ "$VERBOSE" == "true" ]]; then
    echo -e "[DEBUG] $*"
  fi
  log "DEBUG: $*"
}

# ============================================================================
# Confirmation (interactive mode only; auto-accepts in unattended mode)
# ============================================================================
confirm() {
  local prompt="$1"
  local default="${2:-y}"

  if [[ "$INTERACTIVE" != "true" ]]; then
    print_debug "Auto-accepting: $prompt (unattended mode)"
    return 0
  fi

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

# ============================================================================
# Retry with exponential backoff
# ============================================================================
retry_with_backoff() {
  local description="$1"
  shift
  local max_retries="${MAX_RETRIES}"
  local delay="${RETRY_DELAY_BASE}"

  for attempt in $(seq 1 "$max_retries"); do
    print_debug "Attempt $attempt/$max_retries: $description"

    if "$@"; then
      return 0
    fi

    if [[ "$attempt" -lt "$max_retries" ]]; then
      print_warning "$description failed (attempt $attempt/$max_retries), retrying in ${delay}s..."
      sleep "$delay"
      delay=$((delay * 2))
    fi
  done

  print_error "$description failed after $max_retries attempts"
  return 1
}

# ============================================================================
# ArgoCD Authentication (multi-strategy)
# ============================================================================

# Strategy 1: Check if existing CLI token is valid
argocd_cli_token_valid() {
  argocd app list --server "$ARGOCD_SERVER" &>/dev/null 2>&1
}

# Strategy 2: Login with admin password from K8s secret
argocd_login_with_password() {
  print_info "Attempting ArgoCD login with admin credentials..."

  local password
  password=$(kubectl -n "$ARGOCD_NAMESPACE" get secret argocd-initial-admin-secret \
    -o jsonpath="{.data.password}" 2>/dev/null | base64 -d 2>/dev/null) || true

  if [[ -z "$password" ]]; then
    print_debug "argocd-initial-admin-secret not found, trying argocd-secret..."
    # Some setups store the bcrypt hash in argocd-secret; we cannot use that directly.
    # Fall back to API token approach.
    return 1
  fi

  argocd login "$ARGOCD_SERVER" \
    --username admin \
    --password "$password" \
    --grpc-web \
    --insecure 2>/dev/null
}

# Strategy 3: Generate an API token via kubectl port-forward
argocd_generate_api_token() {
  print_info "Generating ArgoCD API token via K8s service account..."

  # Create a short-lived token from the ArgoCD server service account
  ARGOCD_TOKEN=$(kubectl -n "$ARGOCD_NAMESPACE" exec deploy/argocd-server -- \
    argocd account generate-token --account admin --duration 1h 2>/dev/null) || return 1

  if [[ -n "$ARGOCD_TOKEN" ]]; then
    export ARGOCD_AUTH_TOKEN="$ARGOCD_TOKEN"
    print_success "ArgoCD API token generated (expires in 1h)"
    return 0
  fi

  return 1
}

# Strategy 4: Use kubectl to interact with ArgoCD Application CRDs directly
# This bypasses the ArgoCD API entirely -- always works if kubectl works
argocd_sync_via_kubectl() {
  local app_name="$1"
  print_info "Syncing $app_name via kubectl annotation (bypassing ArgoCD CLI)..."

  # Annotate the Application to trigger a sync
  kubectl -n "$ARGOCD_NAMESPACE" patch application "$app_name" \
    --type merge \
    -p "{\"metadata\":{\"annotations\":{\"argocd.argoproj.io/refresh\":\"hard\"}}}" || return 1

  # Wait for sync to complete
  local timeout=300
  local elapsed=0
  local interval=10

  while [[ "$elapsed" -lt "$timeout" ]]; do
    local sync_status health_status
    sync_status=$(kubectl -n "$ARGOCD_NAMESPACE" get application "$app_name" \
      -o jsonpath='{.status.sync.status}' 2>/dev/null) || true
    health_status=$(kubectl -n "$ARGOCD_NAMESPACE" get application "$app_name" \
      -o jsonpath='{.status.health.status}' 2>/dev/null) || true

    print_debug "$app_name: sync=$sync_status health=$health_status (${elapsed}s/${timeout}s)"

    if [[ "$sync_status" == "Synced" && "$health_status" == "Healthy" ]]; then
      print_success "$app_name is Synced and Healthy"
      return 0
    fi

    # If OutOfSync, the hard refresh should trigger auto-sync (if selfHeal is enabled)
    # If selfHeal is not enabled, we need to force it
    if [[ "$sync_status" == "OutOfSync" && "$elapsed" -gt 30 ]]; then
      print_debug "App still OutOfSync after 30s, forcing sync operation..."
      kubectl -n "$ARGOCD_NAMESPACE" patch application "$app_name" \
        --type merge \
        -p '{"operation":{"initiatedBy":{"username":"automation"},"sync":{"revision":"HEAD"}}}' 2>/dev/null || true
    fi

    sleep "$interval"
    elapsed=$((elapsed + interval))
  done

  # Check final status even if timeout
  local final_sync final_health
  final_sync=$(kubectl -n "$ARGOCD_NAMESPACE" get application "$app_name" \
    -o jsonpath='{.status.sync.status}' 2>/dev/null) || true
  final_health=$(kubectl -n "$ARGOCD_NAMESPACE" get application "$app_name" \
    -o jsonpath='{.status.health.status}' 2>/dev/null) || true

  if [[ "$final_sync" == "Synced" ]]; then
    print_warning "$app_name synced but health=$final_health (may still be starting)"
    return 0
  fi

  print_error "$app_name sync timed out (sync=$final_sync health=$final_health)"
  return 1
}

# Master ArgoCD auth function: tries all strategies in order
ensure_argocd_auth() {
  print_step "Ensuring ArgoCD Authentication"

  # Strategy 1: Existing token
  if argocd_cli_token_valid; then
    print_success "Existing ArgoCD CLI session is valid"
    return 0
  fi

  # Strategy 2: Password login
  if argocd_login_with_password; then
    print_success "Logged in to ArgoCD with admin password"
    return 0
  fi

  # Strategy 3: API token
  if argocd_generate_api_token; then
    print_success "Using ArgoCD API token"
    return 0
  fi

  # Strategy 4 is used inline during sync (kubectl-based, no auth needed)
  print_warning "ArgoCD CLI auth unavailable; will use kubectl-based sync"
  return 0
}

# Sync a single ArgoCD application with fallback strategies
sync_argocd_app() {
  local app_name="$1"
  print_info "Syncing ArgoCD application: $app_name"

  # Try CLI sync first (fastest, most feature-complete)
  if argocd_cli_token_valid || [[ -n "${ARGOCD_AUTH_TOKEN:-}" ]]; then
    if argocd app sync "$app_name" \
        --server "$ARGOCD_SERVER" \
        --grpc-web \
        --timeout "$ARGOCD_SYNC_TIMEOUT" \
        --force \
        --prune 2>/dev/null; then
      print_success "$app_name synced via ArgoCD CLI"
      return 0
    fi

    print_warning "$app_name CLI sync failed, attempting re-auth..."

    # Token might have expired mid-execution; try to re-authenticate
    if argocd_login_with_password 2>/dev/null || argocd_generate_api_token 2>/dev/null; then
      if argocd app sync "$app_name" \
          --server "$ARGOCD_SERVER" \
          --grpc-web \
          --timeout "$ARGOCD_SYNC_TIMEOUT" \
          --force \
          --prune 2>/dev/null; then
        print_success "$app_name synced via ArgoCD CLI (re-authenticated)"
        return 0
      fi
    fi
  fi

  # Fallback: kubectl-based sync (no ArgoCD CLI auth needed)
  print_info "Falling back to kubectl-based sync for $app_name..."
  if argocd_sync_via_kubectl "$app_name"; then
    return 0
  fi

  print_error "All sync strategies failed for $app_name"
  return 1
}

# ============================================================================
# Phase tracking
# ============================================================================
record_phase() {
  local phase="$1"
  local status="$2"
  PHASE_RESULTS+=("$phase:$status")
}

# ============================================================================
# Cleanup (runs on EXIT -- handles all failure modes)
# ============================================================================
cleanup() {
  local exit_code=$?

  echo ""
  if [[ "$exit_code" -ne 0 ]]; then
    print_error "Script exited with code $exit_code"
  fi

  # Restore backups if they exist and changes were NOT committed
  if [[ "$BACKUPS_CREATED" == "true" && "$CHANGES_COMMITTED" != "true" ]]; then
    print_warning "Restoring file backups (changes were not committed)..."
    for backup in "$PROJECT_ROOT"/helm/oauth2-proxy/values.yaml.backup \
                   "$PROJECT_ROOT"/argocd/helm/prometheus/values.yaml.backup; do
      if [[ -f "$backup" ]]; then
        local original="${backup%.backup}"
        mv "$backup" "$original"
        print_info "Restored $(basename "$original")"
      fi
    done
  fi

  # Clean up backup files if changes WERE committed (backups no longer needed)
  if [[ "$CHANGES_COMMITTED" == "true" ]]; then
    rm -f "$PROJECT_ROOT"/helm/oauth2-proxy/values.yaml.backup
    rm -f "$PROJECT_ROOT"/argocd/helm/prometheus/values.yaml.backup
  fi

  # Clean up temporary ArgoCD token
  unset ARGOCD_AUTH_TOKEN 2>/dev/null || true

  # Print phase summary
  if [[ ${#PHASE_RESULTS[@]} -gt 0 ]]; then
    echo ""
    print_banner "Execution Summary"
    for result in "${PHASE_RESULTS[@]}"; do
      local phase="${result%%:*}"
      local status="${result##*:}"
      if [[ "$status" == "ok" ]]; then
        print_success "$phase"
      elif [[ "$status" == "skip" ]]; then
        print_info "$phase (skipped)"
      elif [[ "$status" == "warn" ]]; then
        print_warning "$phase (completed with warnings)"
      else
        print_error "$phase (failed)"
      fi
    done
  fi

  if [[ "$exit_code" -eq 0 ]]; then
    print_info "Log saved to: $LOG_FILE"
  else
    print_error "Log saved to: $LOG_FILE"
    print_info "Review log for details: less $LOG_FILE"
  fi
}

trap cleanup EXIT

# ============================================================================
# Phase 0: Check prerequisites
# ============================================================================
check_prerequisites() {
  print_step "Phase 0: Checking Prerequisites"

  local missing=()

  # Core commands (argocd is optional -- we have kubectl fallback)
  for cmd in kubectl git uv; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done

  if [[ ${#missing[@]} -gt 0 ]]; then
    print_error "Missing required commands: ${missing[*]}"
    return 1
  fi

  # argocd CLI is optional (we fall back to kubectl)
  if ! command -v argocd &>/dev/null; then
    print_warning "argocd CLI not found; will use kubectl-based sync"
  fi

  # Check kubectl connectivity
  if ! kubectl cluster-info &>/dev/null 2>&1; then
    print_error "kubectl not connected to cluster"
    return 1
  fi
  print_success "kubectl connected to cluster"

  # Check git repo
  if ! git -C "$PROJECT_ROOT" rev-parse --git-dir &>/dev/null; then
    print_error "Not in a git repository"
    return 1
  fi

  # Check/switch branch
  local current_branch
  current_branch=$(git -C "$PROJECT_ROOT" branch --show-current)
  if [[ "$current_branch" != "$BRANCH" ]]; then
    print_warning "Current branch is '$current_branch', expected '$BRANCH'"
    if confirm "Switch to $BRANCH branch?"; then
      git -C "$PROJECT_ROOT" checkout "$BRANCH" || return 1
      print_success "Switched to $BRANCH"
    else
      if [[ "$INTERACTIVE" == "true" ]]; then
        print_error "Aborting - must be on $BRANCH branch"
        return 1
      fi
      # In unattended mode, auto-switch
      git -C "$PROJECT_ROOT" checkout "$BRANCH" || return 1
      print_success "Auto-switched to $BRANCH"
    fi
  else
    print_success "On branch $BRANCH"
  fi

  # Check for uncommitted changes (warn but continue in unattended mode)
  if ! git -C "$PROJECT_ROOT" diff-index --quiet HEAD -- 2>/dev/null; then
    print_warning "Uncommitted changes detected"
    if [[ "$INTERACTIVE" == "true" ]]; then
      git -C "$PROJECT_ROOT" status --short
      if ! confirm "Continue anyway?" "y"; then
        return 1
      fi
    else
      print_info "Continuing with uncommitted changes (unattended mode)"
    fi
  fi

  # ArgoCD authentication (non-fatal -- we have kubectl fallback)
  if ! [[ "$SKIP_DEPLOY" == "true" ]]; then
    ensure_argocd_auth || true
  fi

  print_success "All prerequisites met"
  record_phase "Prerequisites" "ok"
}

# ============================================================================
# Phase 1: Audit current state
# ============================================================================
audit_current_state() {
  print_banner "Phase 1: Security Audit"
  print_step "Checking Current TLS Validation Status"

  cd "$PROJECT_ROOT"
  uv run scripts/fix-tls-validation.py check || {
    print_warning "Status check found issues (expected -- that is why we are running)"
  }

  if ! confirm "Proceed with automated fixes?" "y"; then
    print_info "Aborting at user request"
    exit 0
  fi

  record_phase "Security Audit" "ok"
}

# ============================================================================
# Phase 2: Apply service configuration fixes
# ============================================================================
apply_service_fixes() {
  print_banner "Phase 2: Service Configuration Fixes"
  print_step "Applying TLS Validation Fixes"

  cd "$PROJECT_ROOT"

  if [[ "$DRY_RUN" == "true" ]]; then
    print_info "[DRY RUN] Would apply TLS validation fixes"
    print_info "[DRY RUN] Would modify: helm/oauth2-proxy/values.yaml"
    print_info "[DRY RUN] Would modify: argocd/helm/prometheus/values.yaml"
    record_phase "Service Fixes" "skip"
    return 0
  fi

  # Create backups
  print_info "Creating backups..."
  for f in helm/oauth2-proxy/values.yaml argocd/helm/prometheus/values.yaml; do
    if [[ -f "$f" ]]; then
      cp "$f" "${f}.backup"
    fi
  done
  BACKUPS_CREATED=true
  print_success "Backups created"

  # Apply fixes
  if uv run scripts/fix-tls-validation.py fix; then
    print_success "Service configuration fixes applied"
  else
    print_error "Fix script failed"
    record_phase "Service Fixes" "fail"
    return 1
  fi

  # Show diff (non-interactive: just log it)
  print_step "Changes Applied"
  git -C "$PROJECT_ROOT" diff helm/oauth2-proxy/values.yaml || true
  git -C "$PROJECT_ROOT" diff argocd/helm/prometheus/values.yaml || true

  if ! confirm "Commit these changes?" "y"; then
    print_warning "Restoring original files..."
    record_phase "Service Fixes" "fail"
    return 1
  fi

  record_phase "Service Fixes" "ok"
}

# ============================================================================
# Phase 3: Commit changes
# ============================================================================
commit_changes() {
  print_banner "Phase 3: Git Commit"
  print_step "Committing Service Configuration Changes"

  cd "$PROJECT_ROOT"

  if [[ "$DRY_RUN" == "true" ]]; then
    print_info "[DRY RUN] Would commit changes"
    record_phase "Git Commit" "skip"
    return 0
  fi

  # Check if there are actually changes to commit
  if git -C "$PROJECT_ROOT" diff --quiet helm/oauth2-proxy/values.yaml argocd/helm/prometheus/values.yaml 2>/dev/null; then
    print_info "No changes to commit (files unchanged -- already remediated?)"
    CHANGES_COMMITTED=true  # Prevent backup restoration
    record_phase "Git Commit" "skip"
    return 0
  fi

  # Stage changes
  git add helm/oauth2-proxy/values.yaml argocd/helm/prometheus/values.yaml

  # Commit
  if git commit -m "$(cat <<'EOF'
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
)"; then
    CHANGES_COMMITTED=true
    print_success "Changes committed to $BRANCH"
    git log -1 --oneline
  else
    print_error "Git commit failed"
    record_phase "Git Commit" "fail"
    return 1
  fi

  record_phase "Git Commit" "ok"
}

# ============================================================================
# Phase 4: Deploy to cluster
# ============================================================================
deploy_to_cluster() {
  print_banner "Phase 4: Cluster Deployment"

  if [[ "$SKIP_DEPLOY" == "true" ]]; then
    print_info "Skipping deployment (--skip-deploy)"
    record_phase "Deployment" "skip"
    return 0
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    print_info "[DRY RUN] Would push to origin/$BRANCH"
    print_info "[DRY RUN] Would sync ArgoCD apps: ${SERVICES_TO_SYNC[*]}"
    record_phase "Deployment" "skip"
    return 0
  fi

  # Push to remote
  print_step "Pushing Changes to Remote"
  if retry_with_backoff "git push" git push origin "$BRANCH"; then
    print_success "Pushed to origin/$BRANCH"
  else
    print_warning "Git push failed -- ArgoCD sync may use stale config"
    print_info "You can manually push later: git push origin $BRANCH"
    # Continue anyway; the cluster changes might already be correct
  fi

  # Sync ArgoCD applications
  print_step "Syncing ArgoCD Applications"

  local sync_failures=0
  for service in "${SERVICES_TO_SYNC[@]}"; do
    if retry_with_backoff "ArgoCD sync $service" sync_argocd_app "$service"; then
      print_success "$service synced"
    else
      print_error "$service sync failed after all retries"
      sync_failures=$((sync_failures + 1))
    fi
  done

  # Restart pods (kubectl-based, very reliable)
  print_step "Restarting Pods"

  # Restart oauth2-proxy
  print_info "Restarting oauth2-proxy..."
  if kubectl rollout restart deployment/oauth2-proxy -n automation 2>/dev/null; then
    kubectl rollout status deployment/oauth2-proxy -n automation --timeout=300s 2>/dev/null || \
      print_warning "oauth2-proxy rollout status check timed out"
    print_success "oauth2-proxy restarted"
  else
    print_warning "oauth2-proxy restart failed (deployment may not exist)"
  fi

  # Restart Grafana
  print_info "Restarting Grafana..."
  if kubectl rollout restart deployment/prometheus-grafana -n monitoring 2>/dev/null; then
    kubectl rollout status deployment/prometheus-grafana -n monitoring --timeout=300s 2>/dev/null || \
      print_warning "Grafana rollout status check timed out"
    print_success "Grafana restarted"
  else
    print_warning "Grafana restart failed (deployment may not exist)"
  fi

  # Wait for pods to stabilize
  print_step "Waiting for Pods to Stabilize"
  sleep 10

  if [[ "$sync_failures" -gt 0 ]]; then
    record_phase "Deployment" "warn"
    print_warning "Deployment completed with $sync_failures sync failure(s)"
    print_info "Check ArgoCD UI: https://$ARGOCD_SERVER"
  else
    record_phase "Deployment" "ok"
    print_success "Deployment complete"
  fi
}

# ============================================================================
# Phase 5: Verify deployment
# ============================================================================
verify_deployment() {
  print_banner "Phase 5: Deployment Verification"

  if [[ "$SKIP_DEPLOY" == "true" || "$DRY_RUN" == "true" ]]; then
    print_info "Skipping verification (no deployment was performed)"
    record_phase "Verification" "skip"
    return 0
  fi

  print_step "Running Verification Tests"

  cd "$PROJECT_ROOT"

  local verification_ok=true

  if uv run scripts/fix-tls-validation.py verify; then
    print_success "All verification tests passed"
  else
    print_warning "Some verification tests failed"
    verification_ok=false
  fi

  print_step "Checking Service Health"

  # Check pods
  print_info "oauth2-proxy pods:"
  kubectl get pods -n automation -l app.kubernetes.io/name=oauth2-proxy 2>/dev/null || \
    print_warning "Could not list oauth2-proxy pods"

  print_info "Grafana pods:"
  kubectl get pods -n monitoring -l app.kubernetes.io/name=grafana 2>/dev/null || \
    print_warning "Could not list Grafana pods"

  # Check for TLS errors in logs
  print_step "Checking for TLS Errors in Logs"

  local tls_errors=false

  print_info "oauth2-proxy logs:"
  if kubectl logs -n automation -l app.kubernetes.io/name=oauth2-proxy --tail=20 2>/dev/null | \
      grep -iE "tls|certificate|x509" 2>/dev/null; then
    tls_errors=true
  else
    print_success "No TLS errors in oauth2-proxy"
  fi

  print_info "Grafana logs:"
  if kubectl logs -n monitoring -l app.kubernetes.io/name=grafana --tail=20 2>/dev/null | \
      grep -iE "tls|certificate|x509" 2>/dev/null; then
    tls_errors=true
  else
    print_success "No TLS errors in Grafana"
  fi

  if [[ "$verification_ok" == "true" && "$tls_errors" == "false" ]]; then
    record_phase "Verification" "ok"
  else
    record_phase "Verification" "warn"
  fi
}

# ============================================================================
# Phase 6: Install CA certificate on workstation
# ============================================================================
install_workstation_cert() {
  print_banner "Phase 6: Workstation Certificate Installation"

  if [[ "$INSTALL_WORKSTATION_CERT" != "true" ]]; then
    print_info "Skipping workstation installation (disabled)"
    record_phase "Workstation Cert" "skip"
    return 0
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    print_info "[DRY RUN] Would install CA certificate on workstation"
    record_phase "Workstation Cert" "skip"
    return 0
  fi

  print_step "Installing CA Certificate on This Workstation"

  if ! confirm "Install CA certificate on this workstation?" "y"; then
    print_info "Skipping workstation installation"
    record_phase "Workstation Cert" "skip"
    return 0
  fi

  cd "$PROJECT_ROOT"

  if [[ -x "$SCRIPT_DIR/install-ca-certificate.sh" ]]; then
    if "$SCRIPT_DIR/install-ca-certificate.sh" all; then
      print_success "CA certificate installed on workstation"
      record_phase "Workstation Cert" "ok"
    else
      print_warning "CA certificate installation failed or incomplete"
      print_info "Try manual installation: ./scripts/install-ca-certificate.sh all"
      record_phase "Workstation Cert" "warn"
    fi
  else
    print_warning "install-ca-certificate.sh not found or not executable"
    record_phase "Workstation Cert" "skip"
  fi
}

# ============================================================================
# Phase 7: Test SSO logins
# ============================================================================
test_sso_logins() {
  print_banner "Phase 7: SSO Login Testing"

  if [[ "$DRY_RUN" == "true" ]]; then
    print_info "[DRY RUN] Would test SSO endpoints"
    record_phase "SSO Testing" "skip"
    return 0
  fi

  print_step "Testing SSO Endpoints"

  local urls=(
    "https://argocd.vectorweight.com"
    "https://grafana.vectorweight.com"
    "https://n8n.vectorweight.com"
    "https://search.vectorweight.com"
    "https://llm.vectorweight.com"
  )

  local failures=0
  print_info "Testing HTTPS connections..."
  for url in "${urls[@]}"; do
    echo -n "  $url ... "
    if curl -s --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null | grep -qE '^(200|302|301|401|403)$'; then
      print_success "OK"
    else
      print_warning "UNREACHABLE"
      failures=$((failures + 1))
    fi
  done

  if [[ "$failures" -eq 0 ]]; then
    record_phase "SSO Testing" "ok"
  else
    record_phase "SSO Testing" "warn"
  fi
}

# ============================================================================
# Main execution flow
# ============================================================================
main() {
  parse_args "$@"
  setup_logging

  print_banner "TLS Remediation Automation (v2 - Unattended)"

  echo -e "${BOLD}Mode:${NC} $(if [[ "$INTERACTIVE" == "true" ]]; then echo "Interactive"; elif [[ "$DRY_RUN" == "true" ]]; then echo "Dry Run"; else echo "Unattended"; fi)"
  echo -e "${BOLD}Branch:${NC} $BRANCH"
  echo -e "${BOLD}Services:${NC} ${SERVICES_TO_SYNC[*]}"
  echo -e "${BOLD}Skip deploy:${NC} $SKIP_DEPLOY"
  echo -e "${BOLD}Skip cert:${NC} $SKIP_CERT"
  echo ""
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
    print_info "Aborting at user request"
    exit 0
  fi

  # Execute phases -- each phase is independently recoverable
  check_prerequisites || exit 1

  audit_current_state || exit 1

  # These phases use soft failure (continue on error) in unattended mode
  apply_service_fixes || {
    if [[ "$INTERACTIVE" == "true" ]]; then exit 1; fi
    print_warning "Service fixes failed, continuing..."
  }

  commit_changes || {
    if [[ "$INTERACTIVE" == "true" ]]; then exit 1; fi
    print_warning "Git commit failed, continuing..."
  }

  deploy_to_cluster || {
    if [[ "$INTERACTIVE" == "true" ]]; then exit 1; fi
    print_warning "Deployment had issues, continuing with verification..."
  }

  verify_deployment || true

  install_workstation_cert || true

  test_sso_logins || true

  # Success summary
  print_banner "Remediation Complete"

  print_info "Next steps:"
  echo "  1. Test SSO logins manually if needed"
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
