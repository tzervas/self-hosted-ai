#!/usr/bin/env bash
# setup-traefik-tls.sh - Generate TLS certificates and configure Traefik
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_PATH="${DATA_PATH:-/data}"
DOMAIN="${DOMAIN:-localhost}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

CERT_DIR="$DATA_PATH/traefik/certs"
CONFIG_DIR="$DATA_PATH/traefik/config"

generate_self_signed_cert() {
  log_info "Generating self-signed TLS certificate for domain: $DOMAIN"

  mkdir -p "$CERT_DIR"

  # Generate private key
  openssl genrsa -out "$CERT_DIR/key.pem" 4096

  # Create certificate signing request config
  cat > "$CERT_DIR/csr.conf" <<EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext
x509_extensions = v3_ca

[dn]
C = US
ST = State
L = City
O = Self-Hosted AI
OU = Infrastructure
CN = $DOMAIN

[req_ext]
subjectAltName = @alt_names

[v3_ca]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ${SERVER_HOST:-192.168.1.170}
IP.3 = ${GPU_WORKER_HOST:-192.168.1.99}
EOF

  # Generate certificate
  openssl req -new -x509 -sha256 -days 365 \
    -key "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -config "$CERT_DIR/csr.conf"

  # Set permissions
  chmod 600 "$CERT_DIR/key.pem"
  chmod 644 "$CERT_DIR/cert.pem"

  log_success "Certificate generated: $CERT_DIR/cert.pem"
  log_info "Certificate valid for 365 days"

  # Display certificate info
  echo ""
  openssl x509 -in "$CERT_DIR/cert.pem" -noout -subject -dates
  echo ""
}

setup_config() {
  log_info "Setting up Traefik configuration..."

  mkdir -p "$CONFIG_DIR"

  # Copy dynamic config template
  if [[ -f "$PROJECT_ROOT/config/traefik/dynamic.yml" ]]; then
    # Substitute environment variables
    envsubst < "$PROJECT_ROOT/config/traefik/dynamic.yml" > "$CONFIG_DIR/dynamic.yml"
    log_success "Dynamic configuration installed"
  else
    log_warn "Dynamic config template not found, creating basic config"
    cat > "$CONFIG_DIR/dynamic.yml" <<EOF
# Basic Traefik Dynamic Configuration
http:
  routers:
    openwebui:
      rule: "PathPrefix(\`/\`)"
      entryPoints:
        - websecure
      service: openwebui
      tls: {}

  services:
    openwebui:
      loadBalancer:
        servers:
          - url: "http://open-webui:8080"

tls:
  certificates:
    - certFile: /certs/cert.pem
      keyFile: /certs/key.pem
EOF
  fi
}

trust_certificate() {
  log_info "To trust this certificate on your system:"
  echo ""
  echo "  Linux (Debian/Ubuntu):"
  echo "    sudo cp $CERT_DIR/cert.pem /usr/local/share/ca-certificates/self-hosted-ai.crt"
  echo "    sudo update-ca-certificates"
  echo ""
  echo "  macOS:"
  echo "    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/cert.pem"
  echo ""
  echo "  Windows (PowerShell as Admin):"
  echo "    Import-Certificate -FilePath $CERT_DIR/cert.pem -CertStoreLocation Cert:\\LocalMachine\\Root"
  echo ""
  echo "  Firefox: Import manually via Preferences > Privacy & Security > Certificates"
  echo ""
}

main() {
  echo ""
  echo "=============================================="
  echo "  Self-Hosted AI Stack - TLS Setup"
  echo "=============================================="
  echo ""

  case "${1:-generate}" in
    generate|gen)
      generate_self_signed_cert
      setup_config
      trust_certificate
      ;;
    config)
      setup_config
      ;;
    trust)
      trust_certificate
      ;;
    info)
      if [[ -f "$CERT_DIR/cert.pem" ]]; then
        openssl x509 -in "$CERT_DIR/cert.pem" -noout -text | head -30
      else
        log_error "No certificate found"
        exit 1
      fi
      ;;
    *)
      echo "Usage: $0 [generate|config|trust|info]"
      echo ""
      echo "Commands:"
      echo "  generate  Generate self-signed certificate and config (default)"
      echo "  config    Regenerate Traefik config only"
      echo "  trust     Show instructions for trusting the certificate"
      echo "  info      Display certificate information"
      exit 1
      ;;
  esac

  echo ""
  log_success "TLS setup complete!"
  echo ""
  echo "Next steps:"
  echo "  1. Start Traefik: docker compose --profile secure up -d traefik"
  echo "  2. Access services via HTTPS:"
  echo "     - https://ai.$DOMAIN (Open WebUI)"
  echo "     - https://api.$DOMAIN (LiteLLM API)"
  echo "     - https://n8n.$DOMAIN (Workflow Automation)"
  echo ""
}

main "$@"
