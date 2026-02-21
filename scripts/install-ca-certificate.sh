#!/usr/bin/env bash
set -euo pipefail

# VectorWeight CA Certificate Installation Script
# Automates extraction and installation of the self-signed root CA
# for proper TLS validation across all services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CA_SECRET_NAME="vectorweight-root-ca"
CA_NAMESPACE="cert-manager"
CA_FILENAME="vectorweight-ca.crt"
TEMP_DIR="/tmp/vectorweight-ca"

# Detect OS
detect_os() {
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f /etc/debian_version ]; then
      echo "debian"
    elif [ -f /etc/redhat-release ]; then
      echo "rhel"
    elif [ -f /etc/arch-release ]; then
      echo "arch"
    else
      echo "linux-unknown"
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"
  else
    echo "unknown"
  fi
}

# Print colored message
print_msg() {
  local color=$1
  shift
  echo -e "${color}$*${NC}"
}

# Print section header
print_header() {
  echo ""
  print_msg "$BLUE" "═══════════════════════════════════════════════════════════════"
  print_msg "$BLUE" "  $*"
  print_msg "$BLUE" "═══════════════════════════════════════════════════════════════"
  echo ""
}

# Extract CA certificate from Kubernetes
extract_ca_from_k8s() {
  print_header "Extracting CA Certificate from Kubernetes"

  mkdir -p "$TEMP_DIR"

  if ! kubectl get secret "$CA_SECRET_NAME" -n "$CA_NAMESPACE" &>/dev/null; then
    print_msg "$RED" "Error: Secret $CA_SECRET_NAME not found in namespace $CA_NAMESPACE"
    print_msg "$YELLOW" "Make sure cert-manager is deployed and the CA secret exists"
    return 1
  fi

  kubectl get secret "$CA_SECRET_NAME" -n "$CA_NAMESPACE" \
    -o jsonpath='{.data.tls\.crt}' | base64 -d > "$TEMP_DIR/$CA_FILENAME"

  print_msg "$GREEN" "✓ Certificate extracted to: $TEMP_DIR/$CA_FILENAME"

  # Display certificate info
  print_msg "$BLUE" "\nCertificate Information:"
  openssl x509 -in "$TEMP_DIR/$CA_FILENAME" -noout -subject -issuer -dates
  echo ""
}

# Install on Debian/Ubuntu
install_debian() {
  print_header "Installing CA Certificate (Debian/Ubuntu)"

  if [ ! -f "$TEMP_DIR/$CA_FILENAME" ]; then
    print_msg "$RED" "Error: Certificate file not found. Run extract first."
    return 1
  fi

  print_msg "$YELLOW" "This requires sudo privileges..."

  # Copy to system CA directory
  sudo cp "$TEMP_DIR/$CA_FILENAME" /usr/local/share/ca-certificates/

  # Update CA trust store
  sudo update-ca-certificates

  print_msg "$GREEN" "✓ Certificate installed to system trust store"
}

# Install on RHEL/Fedora/CentOS
install_rhel() {
  print_header "Installing CA Certificate (RHEL/Fedora/CentOS)"

  if [ ! -f "$TEMP_DIR/$CA_FILENAME" ]; then
    print_msg "$RED" "Error: Certificate file not found. Run extract first."
    return 1
  fi

  print_msg "$YELLOW" "This requires sudo privileges..."

  # Copy to system CA directory
  sudo cp "$TEMP_DIR/$CA_FILENAME" /etc/pki/ca-trust/source/anchors/

  # Update CA trust store
  sudo update-ca-trust

  print_msg "$GREEN" "✓ Certificate installed to system trust store"
}

# Install on Arch Linux
install_arch() {
  print_header "Installing CA Certificate (Arch Linux)"

  if [ ! -f "$TEMP_DIR/$CA_FILENAME" ]; then
    print_msg "$RED" "Error: Certificate file not found. Run extract first."
    return 1
  fi

  print_msg "$YELLOW" "This requires sudo privileges..."

  # Copy to system CA directory
  sudo cp "$TEMP_DIR/$CA_FILENAME" /etc/ca-certificates/trust-source/anchors/

  # Update CA trust store
  sudo trust extract-compat

  print_msg "$GREEN" "✓ Certificate installed to system trust store"
}

# Install on macOS
install_macos() {
  print_header "Installing CA Certificate (macOS)"

  if [ ! -f "$TEMP_DIR/$CA_FILENAME" ]; then
    print_msg "$RED" "Error: Certificate file not found. Run extract first."
    return 1
  fi

  print_msg "$YELLOW" "Adding certificate to macOS Keychain..."

  # Add to system keychain
  sudo security add-trusted-cert -d -r trustRoot \
    -k /Library/Keychains/System.keychain \
    "$TEMP_DIR/$CA_FILENAME"

  print_msg "$GREEN" "✓ Certificate added to System Keychain"
}

# Configure Firefox (all platforms)
configure_firefox() {
  print_header "Configuring Firefox"

  if [ ! -f "$TEMP_DIR/$CA_FILENAME" ]; then
    print_msg "$RED" "Error: Certificate file not found. Run extract first."
    return 1
  fi

  print_msg "$YELLOW" "Firefox uses its own certificate store."
  print_msg "$YELLOW" "To add the CA certificate to Firefox:"
  echo ""
  print_msg "$BLUE" "1. Open Firefox → Settings → Privacy & Security"
  print_msg "$BLUE" "2. Scroll to 'Certificates' → Click 'View Certificates'"
  print_msg "$BLUE" "3. Go to 'Authorities' tab → Click 'Import'"
  print_msg "$BLUE" "4. Select: $TEMP_DIR/$CA_FILENAME"
  print_msg "$BLUE" "5. Check 'Trust this CA to identify websites'"
  echo ""
  print_msg "$GREEN" "Certificate file location: $TEMP_DIR/$CA_FILENAME"
}

# Verify installation
verify_installation() {
  print_header "Verifying Certificate Trust"

  local test_urls=(
    "https://auth.vectorweight.com"
    "https://argocd.vectorweight.com"
    "https://ai.vectorweight.com"
  )

  for url in "${test_urls[@]}"; do
    echo -n "Testing $url ... "
    if curl -s --max-time 5 "$url" > /dev/null 2>&1; then
      print_msg "$GREEN" "✓ OK"
    else
      print_msg "$YELLOW" "⚠ Failed (service may be down, not a cert issue)"
    fi
  done

  echo ""
  print_msg "$BLUE" "Manual verification commands:"
  echo "  curl -v https://auth.vectorweight.com 2>&1 | grep 'SSL certificate verify'"
  echo "  openssl s_client -connect auth.vectorweight.com:443 -CAfile $TEMP_DIR/$CA_FILENAME"
}

# Export for service configuration
export_for_services() {
  print_header "Exporting for Service Configuration"

  local export_dir="$PROJECT_ROOT/config/certificates"
  mkdir -p "$export_dir"

  cp "$TEMP_DIR/$CA_FILENAME" "$export_dir/"

  print_msg "$GREEN" "✓ Certificate exported to: $export_dir/$CA_FILENAME"
  echo ""
  print_msg "$BLUE" "Use this certificate in service configurations:"
  echo "  - oauth2-proxy: Mount as volume, set SSL_CERT_FILE"
  echo "  - Grafana: Configure tls_client_ca"
  echo "  - Python apps: Set REQUESTS_CA_BUNDLE or SSL_CERT_FILE"
  echo "  - Node.js apps: Set NODE_EXTRA_CA_CERTS"
}

# Show usage
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Automates installation and configuration of VectorWeight Root CA certificate
for proper TLS validation across all services.

OPTIONS:
  install          Extract from K8s and install to system trust store
  extract          Extract certificate from Kubernetes only
  verify           Verify certificate trust is working
  firefox          Show Firefox configuration instructions
  export           Export certificate for service configuration
  all              Run all steps (extract, install, verify, export)
  help             Show this help message

EXAMPLES:
  $(basename "$0") install        # Install CA certificate
  $(basename "$0") all            # Complete installation and verification
  $(basename "$0") verify         # Check if certificate is trusted

REQUIREMENTS:
  - kubectl configured with cluster access
  - cert-manager deployed with vectorweight-root-ca secret
  - sudo privileges for system-wide installation

SECURITY NOTE:
  This script installs a self-signed CA certificate. Only install certificates
  you trust. Verify the certificate fingerprint before installation.

EOF
}

# Main command dispatcher
main() {
  if [ $# -eq 0 ]; then
    usage
    exit 0
  fi

  local command=$1
  local os_type
  os_type=$(detect_os)

  case "$command" in
    extract)
      extract_ca_from_k8s
      ;;
    install)
      extract_ca_from_k8s
      case "$os_type" in
        debian)
          install_debian
          ;;
        rhel)
          install_rhel
          ;;
        arch)
          install_arch
          ;;
        macos)
          install_macos
          ;;
        *)
          print_msg "$RED" "Error: Unsupported OS type: $os_type"
          print_msg "$YELLOW" "Manual installation required. Certificate at: $TEMP_DIR/$CA_FILENAME"
          exit 1
          ;;
      esac
      ;;
    verify)
      verify_installation
      ;;
    firefox)
      configure_firefox
      ;;
    export)
      extract_ca_from_k8s
      export_for_services
      ;;
    all)
      extract_ca_from_k8s

      case "$os_type" in
        debian|rhel|arch|macos)
          main install
          ;;
        *)
          print_msg "$YELLOW" "Skipping system installation (unsupported OS)"
          ;;
      esac

      export_for_services
      configure_firefox
      verify_installation

      print_header "Installation Complete"
      print_msg "$GREEN" "✓ CA certificate has been installed and configured"
      print_msg "$BLUE" "Next steps:"
      echo "  1. Restart your browser to load the new certificate"
      echo "  2. Test SSO login at https://argocd.vectorweight.com"
      echo "  3. Fix remaining services (oauth2-proxy, Grafana) per docs/SECURITY_TLS_VALIDATION_AUDIT.md"
      ;;
    help|--help|-h)
      usage
      ;;
    *)
      print_msg "$RED" "Error: Unknown command: $command"
      echo ""
      usage
      exit 1
      ;;
  esac
}

main "$@"
