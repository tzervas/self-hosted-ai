# Archived Legacy Scripts

These shell scripts have been **superseded** by Python tooling or GitOps patterns and are kept here for historical reference only.

**DO NOT USE THESE SCRIPTS** - they reference outdated configurations and deployment patterns.

## Why Archived

| Script | Replacement | Reason |
|--------|-------------|--------|
| `bootstrap.sh` | `scripts/bootstrap.py` | Python CLI with Typer provides better UX |
| `bootstrap-argocd.sh` | ArgoCD App-of-Apps | GitOps handles ongoing deployments |
| `cull-rust-analyzer.sh` | N/A | Personal developer utility, not project infra |
| `deploy-full-stack.sh` | ArgoCD | SSH-based deployment replaced by GitOps |
| `deploy-server.sh` | ArgoCD | Docker-compose model deprecated |
| `generate-secrets.sh` | `scripts/secrets_manager.py` | Python CLI with generate/rotate/export |
| `monitor-cloudflare.sh` | N/A | **OBSOLETE** - Using self-signed certs now |
| `preload-models.sh` | `scripts/bootstrap.py models` | Reads from models-manifest.yml |
| `setup-cloudflare.sh` | N/A | **OBSOLETE** - Using self-signed certs now |
| `setup-traefik-tls.sh` | cert-manager | TLS via ClusterIssuer annotations |
| `verify-cluster-health.sh` | `scripts/validate_cluster.py` | Comprehensive Python health checks |

## Current Tools

Use the modern Python tooling:

```bash
# Bootstrap cluster
uv run shai-bootstrap

# Validate cluster health
uv run shai-validate

# Manage secrets
uv run shai-secrets generate
uv run shai-secrets rotate --all
uv run shai-secrets export
```

## Certificate Strategy Changed

The project moved from Cloudflare DNS-01 challenges to a **self-signed root CA** approach:

- **Old**: `cert-manager` with Cloudflare API for public certs
- **New**: `vectorweight-root-ca` ClusterIssuer for internal certs

This eliminates external dependencies and works in air-gapped environments.

---

*Archived on: $(date)*
