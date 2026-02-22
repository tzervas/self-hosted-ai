---
title: TLS & Certificates
description: Certificate management, CA installation, and TLS validation
---

# TLS & Certificates

## Architecture

The platform uses a self-signed internal CA managed by cert-manager:

- **Root CA**: `vectorweight-root-ca` (stored as Kubernetes secret in `cert-manager` namespace)
- **Wildcard Certificate**: `vectorweight-wildcard-tls` (covers `*.vectorweight.com`)
- **Issuer**: cert-manager ClusterIssuer using the root CA

## Installing the CA Certificate

### Automated Installation

```bash
# Install on all supported platforms
scripts/install-ca-certificate.sh all
```

### Manual Installation

=== "Linux"

    ```bash
    # Export CA certificate
    kubectl get secret vectorweight-root-ca -n cert-manager \
      -o jsonpath='{.data.tls\.crt}' | base64 -d > ca.crt

    # Install system-wide
    sudo cp ca.crt /usr/local/share/ca-certificates/vectorweight-ca.crt
    sudo update-ca-certificates
    ```

=== "macOS"

    ```bash
    # Export and install to system keychain
    kubectl get secret vectorweight-root-ca -n cert-manager \
      -o jsonpath='{.data.tls\.crt}' | base64 -d > ca.crt
    sudo security add-trusted-cert -d -r trustRoot \
      -k /Library/Keychains/System.keychain ca.crt
    ```

=== "Windows"

    ```powershell
    # Export certificate
    kubectl get secret vectorweight-root-ca -n cert-manager `
      -o jsonpath='{.data.tls\.crt}' | base64 -d > ca.crt
    # Import via Certificate Manager
    certutil -addstore -f "ROOT" ca.crt
    ```

### Browser Setup

**Firefox**: Settings > Privacy & Security > View Certificates > Import > Select `ca.crt`

**Chrome**: Settings > Privacy and Security > Security > Manage certificates > Import

## Verification

```bash
# Check certificate status
kubectl get certificates -n cert-manager -o wide

# Test TLS connection
openssl s_client -connect ai.vectorweight.com:443 -servername ai.vectorweight.com

# Verify CA chain
curl -v https://ai.vectorweight.com 2>&1 | grep -i "ssl\|certificate"
```

## Certificate Rotation

Certificates are automatically renewed by cert-manager before expiry. To force renewal:

```bash
# Delete the certificate (ArgoCD will recreate it)
kubectl delete certificate <name> -n cert-manager

# Verify new certificate
kubectl get certificates -n cert-manager -o wide
```
