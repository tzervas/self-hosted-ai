#!/usr/bin/env bash
# =============================================================================
# setup-arc-github-app.sh - Configure GitHub App for Actions Runner Controller
# =============================================================================
# This script helps create and configure a GitHub App for ARC authentication.
#
# Prerequisites:
#   - gh CLI authenticated with your GitHub account
#   - kubeseal installed for creating SealedSecrets
#   - Access to the GitHub organization
#
# Usage:
#   ./scripts/setup-arc-github-app.sh --org YOUR_ORG
# =============================================================================

set -euo pipefail

# Configuration
GITHUB_ORG="${GITHUB_ORG:-}"
ARC_NAMESPACE="arc-runners"
SECRET_NAME="github-app-secret"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --org)
            GITHUB_ORG="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --org YOUR_ORG"
            echo ""
            echo "This script helps configure a GitHub App for Actions Runner Controller."
            echo ""
            echo "Required:"
            echo "  --org    Your GitHub organization name"
            echo ""
            echo "The script will guide you through:"
            echo "  1. Creating a GitHub App with correct permissions"
            echo "  2. Installing the app in your organization"
            echo "  3. Creating a Kubernetes secret with the app credentials"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$GITHUB_ORG" ]]; then
    log_error "GitHub organization is required. Use --org YOUR_ORG"
    exit 1
fi

# Check prerequisites
if ! command -v gh &> /dev/null; then
    log_error "gh CLI not found. Install from: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    log_error "Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found"
    exit 1
fi

echo ""
echo "============================================================================="
echo "              GitHub App Setup for Actions Runner Controller"
echo "============================================================================="
echo ""
echo "This script will guide you through creating a GitHub App for ARC."
echo "Organization: $GITHUB_ORG"
echo ""

# Step 1: Create the GitHub App
log_info "Step 1: Create GitHub App"
echo ""
echo "Go to: https://github.com/organizations/${GITHUB_ORG}/settings/apps/new"
echo ""
echo "Configure the app with these settings:"
echo ""
echo "┌─────────────────────────────────────────────────────────────────────────┐"
echo "│ GitHub App Name: arc-homelab-runners                                    │"
echo "│ Homepage URL: https://github.com/${GITHUB_ORG}                         │"
echo "│                                                                          │"
echo "│ Webhook: UNCHECK 'Active' (not needed)                                  │"
echo "│                                                                          │"
echo "│ Repository Permissions:                                                  │"
echo "│   - Actions: Read-only                                                   │"
echo "│   - Administration: Read & write (for self-hosted runners)              │"
echo "│   - Checks: Read-only                                                    │"
echo "│   - Metadata: Read-only                                                  │"
echo "│                                                                          │"
echo "│ Organization Permissions:                                                │"
echo "│   - Self-hosted runners: Read & write                                   │"
echo "│                                                                          │"
echo "│ Where can this app be installed: Only on this account                   │"
echo "└─────────────────────────────────────────────────────────────────────────┘"
echo ""
read -p "Press Enter after creating the app..."

# Step 2: Generate and download private key
log_info "Step 2: Generate Private Key"
echo ""
echo "After creating the app:"
echo "  1. Click 'Generate a private key'"
echo "  2. Save the downloaded .pem file"
echo ""
read -p "Enter the path to the downloaded private key file: " PRIVATE_KEY_PATH

if [[ ! -f "$PRIVATE_KEY_PATH" ]]; then
    log_error "Private key file not found: $PRIVATE_KEY_PATH"
    exit 1
fi

# Step 3: Get App ID and Installation ID
log_info "Step 3: Get App ID and Installation ID"
echo ""
echo "From the app settings page, note the 'App ID' (a number like 123456)"
read -p "Enter the App ID: " APP_ID

echo ""
echo "Now install the app in your organization:"
echo "  1. Go to app settings -> Install App"
echo "  2. Select your organization"
echo "  3. Choose 'All repositories' or select specific repos"
echo ""
echo "After installation, get the Installation ID from the URL:"
echo "  URL will be: https://github.com/organizations/${GITHUB_ORG}/settings/installations/XXXXX"
echo "  The number at the end is the Installation ID"
echo ""
read -p "Enter the Installation ID: " INSTALLATION_ID

# Step 4: Create Kubernetes namespace
log_info "Step 4: Creating namespace and secret..."

kubectl create namespace "$ARC_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Step 5: Create the secret
PRIVATE_KEY_CONTENT=$(cat "$PRIVATE_KEY_PATH")

kubectl create secret generic "$SECRET_NAME" \
    --namespace="$ARC_NAMESPACE" \
    --from-literal=github_app_id="$APP_ID" \
    --from-literal=github_app_installation_id="$INSTALLATION_ID" \
    --from-literal=github_app_private_key="$PRIVATE_KEY_CONTENT" \
    --dry-run=client -o yaml | kubectl apply -f -

log_success "Secret created successfully!"

# Step 6: Create runner groups
log_info "Step 5: Creating runner groups..."

echo ""
echo "Creating runner groups via GitHub API..."

# Create standard runner group
gh api --method POST "/orgs/${GITHUB_ORG}/actions/runner-groups" \
    -f name="homelab-runners" \
    -f visibility="all" \
    2>/dev/null || log_warn "Runner group 'homelab-runners' may already exist"

# Create GPU runner group
gh api --method POST "/orgs/${GITHUB_ORG}/actions/runner-groups" \
    -f name="homelab-gpu-runners" \
    -f visibility="all" \
    2>/dev/null || log_warn "Runner group 'homelab-gpu-runners' may already exist"

# Summary
echo ""
echo "============================================================================="
echo "                        SETUP COMPLETE"
echo "============================================================================="
echo ""
echo "GitHub App configured:"
echo "  App ID:           $APP_ID"
echo "  Installation ID:  $INSTALLATION_ID"
echo "  Organization:     $GITHUB_ORG"
echo ""
echo "Kubernetes resources created:"
echo "  Namespace:        $ARC_NAMESPACE"
echo "  Secret:           $SECRET_NAME"
echo ""
echo "Runner groups created:"
echo "  - homelab-runners (for standard workloads)"
echo "  - homelab-gpu-runners (for GPU workloads)"
echo ""
echo "Next steps:"
echo "  1. Deploy ARC controller:"
echo "     kubectl apply -f argocd/applications/arc-controller.yaml"
echo ""
echo "  2. Deploy runner scale sets:"
echo "     kubectl apply -f argocd/applications/arc-runners-standard.yaml"
echo "     kubectl apply -f argocd/applications/arc-runners-gpu.yaml"
echo ""
echo "  3. Verify runners are registered:"
echo "     gh api /orgs/${GITHUB_ORG}/actions/runners"
echo ""
echo "  4. Test with a workflow:"
echo "     runs-on: [self-hosted, linux, homelab-runners]"
echo ""
echo "============================================================================="

# Cleanup: securely delete the private key reminder
echo ""
log_warn "SECURITY: Delete the private key file after confirming the setup works:"
echo "  rm -f $PRIVATE_KEY_PATH"
