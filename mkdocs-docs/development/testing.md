---
title: Testing
description: Test strategy, running tests, and validation
---

# Testing

## Validation Suite

```bash
# Run all validation
task validate:all

# Individual checks
task validate:helm         # Lint Helm charts
task validate:manifests    # Validate K8s manifests with kubeconform
task validate:policies     # Validate Kyverno policies
```

## Security Scanning

```bash
# Trivy configuration scan
task security:trivy

# Secret detection in codebase
task security:secrets
```

## Python Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Single test file
uv run pytest tests/test_core_base.py -v

# Single test
uv run pytest -k "test_function_name"

# With coverage
uv run pytest tests/ --cov=agents --cov-report=html
```

## Rust Tests

```bash
cd rust-agents
cargo test
cargo clippy -- -D warnings
cargo fmt --check
```

## Pre-commit Validation

```bash
# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files
```

## CI/CD

GitHub Actions workflows run automatically on push/PR:

- **Python Tests**: Runs pytest on Python 3.10, 3.11, 3.12
- **Rust Build**: Builds, tests, and lints Rust code
- **Docker Build**: Validates Dockerfiles and runs security scans
