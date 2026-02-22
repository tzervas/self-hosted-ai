---
title: Contributing
description: Git workflow, commit conventions, and contribution guidelines
---

# Contributing

## Git Workflow

### Branches

| Branch | Purpose | Merges To |
|--------|---------|-----------|
| `main` | Stable releases only | - |
| `dev` | Integration branch | `main` (manual PR) |
| `feature/*` | New features | `dev` |
| `fix/*` | Bug fixes | `dev` |
| `docs/*` | Documentation | `dev` |

!!! warning "Never commit directly to main"
    All changes go through `dev` first. Feature and fix branches merge to `dev` via PR.

### Workflow Example

```bash
# Start a new feature
git checkout dev
git pull origin dev
git checkout -b feature/add-model-presets

# Make changes, commit with conventional commits
git add .
git commit -m "feat: add model preset configuration"

# Push and create PR to dev
git push -u origin feature/add-model-presets
gh pr create --base dev --title "feat: add model preset configuration"
```

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/). The pre-commit hook enforces this.

### Format

```
<type>(<scope>): <description>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes bug nor adds feature |
| `test` | Adding or fixing tests |
| `chore` | Other changes (tooling, etc.) |

## Pre-commit Hooks

```bash
# Setup
pre-commit install
pre-commit install --hook-type commit-msg

# Run manually
pre-commit run --all-files
```

### Hooks Included

| Hook | Purpose | Auto-fix |
|------|---------|----------|
| shellcheck | Shell script linting | No |
| shfmt | Shell formatting | Yes |
| hadolint | Dockerfile linting | No |
| prettier | YAML/JSON/MD formatting | Yes |
| detect-secrets | Secret detection | No (blocks) |
| conventional-pre-commit | Commit message format | No |

## Code Standards

### Python

- Python 3.12+ required
- Ruff for linting/formatting (line length: 100)
- Type hints encouraged, mypy for checking
- Tests with pytest

### Shell Scripts

- `#!/usr/bin/env bash` with `set -euo pipefail`
- 2-space indentation (shfmt enforced)
- Quote all variables: `"$var"`

### Kubernetes/Helm

- Helm charts in `helm/<service>/` with `Chart.yaml` and `values.yaml`
- ArgoCD applications in `argocd/applications/`
- No plaintext secrets -- use SealedSecrets

## Testing

```bash
# Validation suite
task validate:all

# Individual checks
task validate:helm
task validate:manifests
task validate:policies

# Security scans
task security:trivy
task security:secrets

# Python tests
uv run pytest tests/ -v
```
