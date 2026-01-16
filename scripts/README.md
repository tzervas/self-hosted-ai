# Self-Hosted AI Platform - Scripts

Infrastructure automation scripts for the Self-Hosted AI Platform, built with Python 3.12+ and [PEP 723](https://peps.python.org/pep-0723/) inline script metadata for standalone execution via [uv](https://docs.astral.sh/uv/).

## Quick Start

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run any script standalone (dependencies auto-installed)
uv run scripts/backup.py --help
uv run scripts/sync_models.py list
uv run scripts/api_keys.py generate --name "my-key"

# Or create virtual environment for development
cd scripts/
uv sync
```

## Python Scripts (PEP 723)

All Python scripts use inline script metadata, making them fully standalone:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer>=0.12.0", "rich>=13.9.0"]
# ///
```

### Backup & Restore
```bash
# Create full backup (PostgreSQL, Qdrant, OpenWebUI)
uv run scripts/backup.py create --all

# List available backups
uv run scripts/backup.py list

# Restore from backup
uv run scripts/backup.py restore 20250119_120000

# Cleanup old backups
uv run scripts/backup.py cleanup --keep 5
```

### Model Synchronization
```bash
# List models across all locations
uv run scripts/sync_models.py list

# Push models to GPU worker
uv run scripts/sync_models.py push --all

# Pull models from GPU worker
uv run scripts/sync_models.py pull checkpoints

# Compare models between locations
uv run scripts/sync_models.py diff
```

### API Key Management
```bash
# Generate new API key
uv run scripts/api_keys.py generate --name "production-api" --tier premium

# List all keys
uv run scripts/api_keys.py list

# Rotate a key
uv run scripts/api_keys.py rotate --key-prefix sk_abc123

# Check keys expiring soon
uv run scripts/api_keys.py check

# Export Prometheus metrics
uv run scripts/api_keys.py metrics > /var/lib/prometheus/keys.prom
```

### Release Management
```bash
# Show current version
uv run scripts/release.py status

# Bump patch version and release
uv run scripts/release.py bump patch

# Tag specific version
uv run scripts/release.py tag 1.0.0-rc1

# Check pre-release requirements
uv run scripts/release.py check
```

### ComfyUI Workflows
```bash
# List available workflows
uv run scripts/comfyui.py list

# Show workflow details
uv run scripts/comfyui.py info txt2img-sdxl

# Setup workflow (download models)
uv run scripts/comfyui.py setup txt2img-sdxl

# Validate ComfyUI connectivity
uv run scripts/comfyui.py validate

# Export workflow for API
uv run scripts/comfyui.py export txt2img-sdxl > workflow.json
```

### Development Setup
```bash
# Check environment status
uv run scripts/dev_setup.py check

# Full development environment setup
uv run scripts/dev_setup.py setup

# Setup Python agents only
uv run scripts/dev_setup.py setup --python-only

# Run tests
uv run scripts/dev_setup.py test
```

### Database Migration
```bash
# Check migration prerequisites
uv run scripts/migrate_db.py check

# Run full PostgreSQL 16→17 migration
uv run scripts/migrate_db.py migrate

# Create backup only
uv run scripts/migrate_db.py backup

# Verify migration integrity
uv run scripts/migrate_db.py verify
```

### Cluster Validation
```bash
# Full validation suite
uv run scripts/validate_cluster.py all

# Test API endpoints
uv run scripts/validate_cluster.py api

# Check TLS certificates
uv run scripts/validate_cluster.py tls

# Verify DNS resolution
uv run scripts/validate_cluster.py dns
```

### Secrets Management
```bash
# Generate new secrets
uv run scripts/secrets_manager.py generate

# Rotate existing secrets
uv run scripts/secrets_manager.py rotate

# Export credentials
uv run scripts/secrets_manager.py export
```

## Project Structure

```
scripts/
├── pyproject.toml           # uv/Python project configuration
├── README.md                # This file
│
├── # Python CLI Scripts (PEP 723 standalone)
├── backup.py                # Backup/restore PostgreSQL, Qdrant, OpenWebUI
├── sync_models.py           # Model sync across homelab locations
├── api_keys.py              # API key lifecycle management
├── release.py               # Semantic versioning and releases
├── comfyui.py               # ComfyUI workflow and model management
├── dev_setup.py             # Development environment setup
├── migrate_db.py            # PostgreSQL version migration
├── validate_cluster.py      # Cluster health validation
├── secrets_manager.py       # Credential management
├── bootstrap.py             # Service bootstrap logic
│
├── lib/                     # Shared libraries
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── kubernetes.py        # K8s async utilities
│   ├── services.py          # Service API clients
│   └── secrets.py           # Secrets management
│
├── # Shell Scripts (require sudo/system access)
├── configure-host-system.sh # sysctl, inotify settings (sudo)
├── setup-storage.sh         # btrfs subvolume creation (sudo)
├── deploy-gpu-worker.sh     # GPU node docker-compose (akula-prime)
├── setup-arc-github-app.sh  # ARC GitHub App wizard (interactive)
└── setup-autogit.sh         # GitHub↔GitLab mirroring (interactive)
```

## Environment Variables

Create a `.env.local` file (gitignored) for local overrides:

```bash
# Kubernetes context
KUBECONFIG=/path/to/kubeconfig

# Domain configuration
DOMAIN=vectorweight.com
CLUSTER_IP=192.168.1.170

# GPU worker
GPU_WORKER_HOST=192.168.1.99

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
POSTGRES_PASSWORD=secret

# Feature flags
DRY_RUN=false
VERBOSE=true
```

## Shell Scripts (Kept for System Access)

These shell scripts remain because they require:
- Root/sudo access (system-level configuration)
- Run outside Kubernetes (GPU worker docker-compose)
- Interactive setup wizards

| Script | Purpose | Why Shell |
|--------|---------|-----------|
| `configure-host-system.sh` | sysctl, inotify, vm.max_map_count | Requires sudo |
| `setup-storage.sh` | btrfs subvolume creation | Requires sudo |
| `deploy-gpu-worker.sh` | GPU node docker-compose | Runs on akula-prime |
| `setup-arc-github-app.sh` | ARC GitHub App setup | Interactive wizard |
| `setup-autogit.sh` | GitHub↔GitLab mirroring | Git remote setup |

## Archived Scripts

The following legacy shell scripts have been replaced with Python:

| Old Shell Script | Replaced By |
|-----------------|-------------|
| `backup-components.sh` | `backup.py` |
| `sync-models.sh` | `sync_models.py` |
| `sync-models-from-akula.sh` | `sync_models.py` |
| `manage-keys.sh` | `api_keys.py` |
| `release.sh` | `release.py` |
| `comfyui-setup.sh` | `comfyui.py` |
| `setup-dev.sh` | `dev_setup.py` |
| `migrate-postgres.sh` | `migrate_db.py` |
| `validate-env.sh` | `validate_cluster.py` |

**Note**: Cloudflare-related scripts have been archived - the project now uses self-signed certificates via `vectorweight-root-ca` ClusterIssuer.

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Run type checker
uv run mypy .

# Format code
uv run ruff format .
```

## License

MIT - See [LICENSE](../LICENSE) for details.
