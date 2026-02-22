---
title: Getting Started
description: Prerequisites, installation, and first steps
---

# Getting Started

## Prerequisites

- **k3s cluster** (v1.28+) with `kubectl` configured
- **Helm 3.x** for chart deployment
- **Python 3.12+** with [uv](https://docs.astral.sh/uv/) package manager
- **ArgoCD** installed in the cluster

## 1. Clone Repository

```bash
git clone https://github.com/tzervas/self-hosted-ai.git
cd self-hosted-ai
```

## 2. Install Python Tools

```bash
cd scripts
uv sync
source .venv/bin/activate
```

## 3. Bootstrap Cluster

=== "GitOps (Recommended)"

    ```bash
    # Deploy with ArgoCD App-of-Apps
    kubectl apply -k argocd/
    ```

=== "Manual"

    ```bash
    # Bootstrap services manually
    shai-bootstrap all
    ```

## 4. Generate Credentials

```bash
# Generate secure credentials
shai-secrets generate

# Export to agent-readable format
shai-secrets export --format markdown

# View credentials
shai-secrets show
```

## 5. Validate Deployment

```bash
shai-validate all
```

## 6. Install CA Certificate

The platform uses a self-signed CA. Install it in your browser for HTTPS access:

```bash
# Export CA certificate
kubectl get secret vectorweight-root-ca -n cert-manager \
  -o jsonpath='{.data.tls\.crt}' | base64 -d > ca.crt

# Linux (system-wide)
sudo cp ca.crt /usr/local/share/ca-certificates/vectorweight-ca.crt
sudo update-ca-certificates
```

See [TLS & Certificates](security/tls-certificates.md) for detailed browser setup instructions.

## Next Steps

- Visit [Service Endpoints](endpoints.md) to access the platform
- Read the [Architecture Overview](architecture/index.md) to understand the system design
- Check the [Operations Runbook](operations/index.md) for daily operations
