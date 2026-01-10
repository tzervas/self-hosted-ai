# Contributing to Self-Hosted AI Stack

Thank you for your interest in contributing! This document outlines the development workflow and standards.

## Git Workflow

### Branches

| Branch | Purpose | Merges To |
|--------|---------|-----------|
| `main` | Stable releases only | - |
| `dev` | Integration branch | `main` (manual) |
| `feature/*` | New features | `dev` |
| `fix/*` | Bug fixes | `dev` |
| `docs/*` | Documentation | `dev` |

### Branch Rules

1. **Never commit directly to `main`** - All changes go through `dev` first
2. **PRs to `dev`** - Feature and fix branches merge to `dev` via PR
3. **PRs to `main`** - Only from `dev`, requires manual approval
4. **Releases** - Created from `main` using `./scripts/release.sh`

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

# After PR approval and merge, clean up
git checkout dev
git pull origin dev
git branch -d feature/add-model-presets
```

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/). The pre-commit hook enforces this.

### Format

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change that neither fixes bug nor adds feature |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `build` | Build system or dependencies |
| `ci` | CI/CD configuration |
| `chore` | Other changes (tooling, etc.) |
| `revert` | Revert a previous commit |

### Examples

```bash
# Feature
git commit -m "feat(bootstrap): add model existence check before pull"

# Fix
git commit -m "fix(server): correct OLLAMA_BASE_URLS separator"

# Documentation
git commit -m "docs: update deployment instructions for RTX 5080"

# Breaking change
git commit -m "feat!: change config file format to YAML"
```

## Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. They:

1. **Auto-fix** safe issues (formatting, trailing whitespace)
2. **Block** on unfixable errors (syntax errors, detected secrets)

### Setup

```bash
./scripts/bootstrap.sh setup
```

### Manual Run

```bash
# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run shellcheck --all-files
```

### Hooks Included

| Hook | Purpose | Auto-fix |
|------|---------|----------|
| shellcheck | Shell script linting | No |
| shfmt | Shell formatting | Yes |
| hadolint | Dockerfile linting | No |
| prettier | YAML/JSON/MD formatting | Yes |
| markdownlint | Markdown linting | Yes |
| detect-secrets | Secret detection | No (blocks) |
| conventional-pre-commit | Commit message format | No |

## Code Standards

### Shell Scripts

- Use `#!/usr/bin/env bash`
- Enable strict mode: `set -euo pipefail`
- Quote all variables: `"$var"` not `$var`
- Use `[[ ]]` for conditionals
- 2-space indentation (enforced by shfmt)

### Docker Compose

- No `version` attribute (deprecated)
- Use `.env` files for configuration
- Never commit secrets
- Use bind mounts for persistence

### Configuration

- Use `.env.example` for templates
- Use `${VAR:-default}` syntax for defaults
- Document all variables

## Testing Changes

### Local Testing

```bash
# Check stack status
./scripts/bootstrap.sh status

# Test model connectivity
curl http://192.168.1.99:11434/api/tags
curl http://192.168.1.170:11434/api/tags

# Test Open WebUI
curl http://192.168.1.170:3001/health
```

### Before PR

1. Run pre-commit on all files: `pre-commit run --all-files`
2. Test deployment scripts work
3. Verify documentation matches behavior
4. Update CHANGELOG if applicable

## Release Process

Releases are created from `main` branch only:

1. Ensure `dev` is stable and tested
2. Create PR from `dev` to `main`
3. After merge, run release script:

```bash
git checkout main
git pull origin main
./scripts/release.sh bump <major|minor|patch>
```

The release script will:

- Bump version in `VERSION` file
- Create git tag
- Push to GitHub
- Create GitHub release with changelog

## Questions?

Open an issue or discussion on GitHub.
