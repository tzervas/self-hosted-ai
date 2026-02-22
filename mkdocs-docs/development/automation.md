---
title: Automation
description: Python automation scripts and task runner
---

# Automation

## Task Runner

The project uses [Task](https://taskfile.dev/) for common operations, defined in `Taskfile.yaml`:

```bash
# Setup development environment
task setup:dev

# Linting and formatting
task lint                    # Run all pre-commit hooks
task lint:fix                # Run with auto-fix

# Validation
task validate:helm           # Lint all Helm charts
task validate:manifests      # Validate K8s manifests
task validate:policies       # Validate Kyverno policies
task validate:all            # Run all validation

# Security scanning
task security:trivy          # Trivy config scan
task security:secrets        # Detect secrets in codebase
```

## Python Scripts

All Python scripts are managed with uv in the `scripts/` directory:

```bash
cd scripts
uv sync
```

### Available Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap.py` | Initial cluster setup |
| `validate_cluster.py` | Health checks |
| `secrets_manager.py` | SealedSecret generation and rotation |
| `sync_models.py` | Ollama model management |
| `rag_index.py` | Documentation RAG indexer |
| `fix-tls-validation.py` | TLS validation fixes |

### CLI Tools

```bash
# Main CLI
shai --help

# Bootstrap
shai-bootstrap all
shai-bootstrap services
shai-bootstrap models

# Validate
shai-validate all
shai-validate dns
shai-validate tls
shai-validate services

# Secrets
shai-secrets generate
shai-secrets export
shai-secrets rotate
shai-secrets show
```
