# Self-Hosted AI Platform - Scripts

Infrastructure automation scripts for the Self-Hosted AI Platform, built with Python 3.12+ and managed with [uv](https://docs.astral.sh/uv/).

## Quick Start

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
cd scripts/
uv sync

# Run any script via the CLI
uv run shai --help
uv run shai-bootstrap --help
uv run shai-validate --help
uv run shai-secrets --help
```

## Available Commands

### `shai` - Main CLI
```bash
uv run shai --help
uv run shai status              # Cluster status overview
uv run shai services            # List all services
uv run shai logs <service>      # View service logs
```

### `shai-bootstrap` - Initial Setup
```bash
uv run shai-bootstrap --help
uv run shai-bootstrap all       # Full cluster bootstrap
uv run shai-bootstrap services  # Configure all services
uv run shai-bootstrap models    # Pull/sync AI models
```

### `shai-validate` - Health Checks
```bash
uv run shai-validate --help
uv run shai-validate all        # Full validation suite
uv run shai-validate api        # Test all API endpoints
uv run shai-validate dns        # Verify DNS resolution
uv run shai-validate tls        # Check TLS certificates
```

### `shai-secrets` - Credential Management
```bash
uv run shai-secrets --help
uv run shai-secrets generate    # Generate new secrets
uv run shai-secrets rotate      # Rotate existing secrets
uv run shai-secrets export      # Export to ADMIN_CREDENTIALS.local.md
uv run shai-secrets from-env    # Import from environment
```

### `shai-backup` - Backup & Restore
```bash
uv run shai-backup --help
uv run shai-backup create       # Create full backup
uv run shai-backup restore      # Restore from backup
uv run shai-backup list         # List available backups
```

## Project Structure

```
scripts/
├── pyproject.toml          # uv/Python project configuration
├── README.md               # This file
├── lib/                    # Shared libraries
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── kubernetes.py       # K8s async utilities
│   ├── services.py         # Service API clients
│   └── secrets.py          # Secrets management
├── bootstrap.py            # Service bootstrap logic
├── validate_cluster.py     # Cluster validation
└── secrets_manager.py      # Credential management

# Utility scripts (shell - still needed)
├── backup-components.sh    # PostgreSQL/Qdrant backup
├── configure-host-system.sh # System-level config (sudo)
├── deploy-gpu-worker.sh    # Docker-compose GPU worker
├── manage-keys.sh          # API key management
├── migrate-postgres.sh     # Database migrations
├── release.sh              # Container image releases
├── setup-arc-github-app.sh # ARC GitHub App wizard
├── setup-autogit.sh        # GitHub/GitLab mirroring
├── setup-dev.sh            # Development environment
├── setup-dns.sh            # DNS configuration
├── setup-selfsigned-certs.sh # Certificate setup
├── setup-storage.sh        # btrfs/Longhorn storage
├── sync-models.sh          # Model vault sync
├── sync-models-from-akula.sh # Cross-host model sync
└── validate-env.sh         # Environment validation
```
├── bootstrap.py            # Service bootstrap logic
├── validate_cluster.py     # Cluster validation
├── secrets_manager.py      # Credential management
├── backup_restore.py       # Backup operations
├── sync_models.py          # Model synchronization
└── tests/                  # Test suite
    └── ...
```

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

## Environment Variables

Create a `.env.local` file (gitignored) for local overrides:

```bash
# Kubernetes context (defaults to current)
KUBECONFIG=/path/to/kubeconfig

# Domain configuration
DOMAIN=vectorweight.com
CLUSTER_IP=192.168.1.170

# GPU worker
GPU_WORKER_HOST=192.168.1.99

# Feature flags
DRY_RUN=false
VERBOSE=true
```

## Remaining Shell Scripts

These shell scripts are kept because they either:
- Require root/sudo access (system-level configuration)
- Run outside Kubernetes (GPU worker docker-compose)
- Are interactive setup wizards
- Handle database-level operations (pg_dump/restore)

| Script | Purpose | Why Shell |
|--------|---------|-----------|
| `backup-components.sh` | PostgreSQL/Qdrant backup | pg_dump/restore via CLI |
| `configure-host-system.sh` | sysctl, inotify settings | Requires sudo |
| `deploy-gpu-worker.sh` | GPU node docker-compose | Runs on akula-prime |
| `migrate-postgres.sh` | Database version migration | pg_dump/restore |
| `release.sh` | Container image builds | Build & push workflow |
| `setup-arc-github-app.sh` | ARC GitHub App setup | Interactive wizard |
| `setup-autogit.sh` | GitHub↔GitLab mirroring | Git remote setup |
| `setup-storage.sh` | btrfs subvolume creation | Requires sudo |

**Note**: Cloudflare-related scripts have been archived - the project now uses self-signed certificates via `vectorweight-root-ca` ClusterIssuer.

## License

MIT - See [LICENSE](../LICENSE) for details.
