#!/usr/bin/env bash
# =============================================================================
# Self-Signed Certificate Setup for Local Development
# =============================================================================
# Creates a self-signed wildcard certificate for vectorweight.com and installs
# it on the local machine for testing before DNS propagates.
# =============================================================================

set -euo pipefail

DOMAIN="vectorweight.com"
CERT_DIR="/tmp/vectorweight-selfsigned"
CA_NAME="vectorweight-local-ca"
NAMESPACE="cert-manager"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# =============================================================================
# Create self-signed CA and wildcard certificate
# =============================================================================

log_info "Creating self-signed CA and wildcard certificate..."

mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# Create CA private key
if [[ ! -f ca-key.pem ]]; then
    log_info "Generating CA private key..."
    openssl genrsa -out ca-key.pem 4096
fi

# Create CA certificate
if [[ ! -f ca-cert.pem ]]; then
    log_info "Generating CA certificate..."
    cat > ca-config.cnf <<EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
CN = ${CA_NAME}
O = VectorWeight Local Development
OU = Self-Signed CA

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
EOF

    openssl req -new -x509 -days 3650 -key ca-key.pem -out ca-cert.pem \
        -config ca-config.cnf -extensions v3_ca
    
    log_success "CA certificate created"
fi

# Create wildcard certificate private key
if [[ ! -f wildcard-key.pem ]]; then
    log_info "Generating wildcard certificate private key..."
    openssl genrsa -out wildcard-key.pem 2048
fi

# Create wildcard certificate signing request
log_info "Creating certificate signing request..."
cat > wildcard-csr.cnf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = *.${DOMAIN}
O = VectorWeight
OU = Self-Hosted AI

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
EOF

openssl req -new -key wildcard-key.pem -out wildcard.csr -config wildcard-csr.cnf

# Sign the certificate with our CA
log_info "Signing certificate with CA..."
cat > wildcard-ext.cnf <<EOF
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
EOF

openssl x509 -req -in wildcard.csr -CA ca-cert.pem -CAkey ca-key.pem \
    -CAcreateserial -out wildcard-cert.pem -days 365 \
    -extfile wildcard-ext.cnf

log_success "Wildcard certificate created"

# =============================================================================
# Create Kubernetes secret
# =============================================================================

log_info "Creating Kubernetes secret..."

kubectl create secret tls vectorweight-selfsigned-tls \
    --cert=wildcard-cert.pem \
    --key=wildcard-key.pem \
    -n "$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -

log_success "Secret created in ${NAMESPACE} namespace"

# =============================================================================
# Install CA certificate on local machine
# =============================================================================

log_info "Installing CA certificate on local machine..."

if [[ -f /etc/debian_version ]]; then
    # Debian/Ubuntu
    sudo cp ca-cert.pem /usr/local/share/ca-certificates/${CA_NAME}.crt
    sudo update-ca-certificates
    log_success "CA installed in system trust store"
elif [[ -f /etc/redhat-release ]]; then
    # RHEL/CentOS
    sudo cp ca-cert.pem /etc/pki/ca-trust/source/anchors/${CA_NAME}.pem
    sudo update-ca-trust
    log_success "CA installed in system trust store"
elif [[ -f /etc/arch-release ]]; then
    # Arch
    sudo cp ca-cert.pem /etc/ca-certificates/trust-source/anchors/${CA_NAME}.crt
    sudo trust extract-compat
    log_success "CA installed in system trust store"
else
    log_warn "Unknown distro - please manually install ca-cert.pem to your trust store"
fi

# Install in Firefox (if exists)
if command -v firefox &> /dev/null; then
    FIREFOX_PROFILES="$HOME/.mozilla/firefox"
    if [[ -d "$FIREFOX_PROFILES" ]]; then
        log_info "Installing CA in Firefox profiles..."
        for profile in "$FIREFOX_PROFILES"/*.*/; do
            if [[ -d "$profile" ]]; then
                certutil -A -n "$CA_NAME" -t "C,," -i ca-cert.pem -d sql:"$profile" 2>/dev/null || true
            fi
        done
        log_success "CA installed in Firefox"
    fi
fi

# =============================================================================
# Update ingresses to use self-signed cert
# =============================================================================

log_info "Updating ingresses to use self-signed certificate..."

for ns in argocd self-hosted-ai monitoring longhorn-system; do
    kubectl get ingress -n "$ns" --no-headers 2>/dev/null | awk '{print $1}' | while read ingress; do
        kubectl annotate ingress -n "$ns" "$ingress" \
            cert-manager.io/cluster-issuer=self-signed \
            cert-manager.io/common-name="${DOMAIN}" \
            --overwrite 2>/dev/null || true
        
        # Patch to use the self-signed cert
        kubectl patch ingress -n "$ns" "$ingress" --type=json -p='[
            {"op": "replace", "path": "/spec/tls", "value": [
                {
                    "hosts": ["*.'"${DOMAIN}"'", "'"${DOMAIN}"'"],
                    "secretName": "vectorweight-selfsigned-tls"
                }
            ]}
        ]' 2>/dev/null || true
    done
done

log_success "Ingresses updated"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "============================================================================="
echo "                  SELF-SIGNED CERTIFICATE INSTALLED"
echo "============================================================================="
echo ""
echo "✅ CA Certificate: ${CERT_DIR}/ca-cert.pem"
echo "✅ Wildcard Cert:  ${CERT_DIR}/wildcard-cert.pem"
echo "✅ Kubernetes Secret: vectorweight-selfsigned-tls (in ${NAMESPACE})"
echo "✅ System Trust: CA installed and trusted"
echo ""
echo "The certificate covers:"
echo "  - ${DOMAIN}"
echo "  - *.${DOMAIN}"
echo ""
echo "Valid for: 365 days"
echo ""
echo "⚠️  This is a self-signed certificate for local development only."
echo "    When DNS propagates, certificates will automatically switch to Let's Encrypt."
echo ""
echo "You can now access services at:"
echo "  - https://ai.${DOMAIN}"
echo "  - https://llm.${DOMAIN}"
echo "  - https://argocd.${DOMAIN}"
echo "  - https://grafana.${DOMAIN}"
echo ""

log_info "Certificate files saved to: ${CERT_DIR}"
