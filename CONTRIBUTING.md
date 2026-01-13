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

## Development Setup

For developing the Python agent framework and Rust runtime, follow these steps:

### Quick Setup

```bash
# Run automated setup script
./scripts/setup-dev.sh
```

This installs:
- Python virtual environment with all dependencies
- Rust toolchain and builds the agent runtime
- Pre-commit hooks for Python and Rust
- Runs tests to verify installation

### Manual Setup

**Python Agents:**

```bash
cd agents
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

**Rust Runtime:**

```bash
cd rust-agents
cargo build --release
cargo test
```

**Pre-commit Hooks:**

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

## Agent Framework Development

### Project Structure

```text
agents/
├── agents/
│   ├── core/              # Base abstractions
│   │   ├── base.py        # Agent, AgentConfig, AgentResult
│   │   ├── task.py        # Task management
│   │   └── workflow.py    # Workflow orchestration
│   ├── specialized/       # Specialized agent implementations
│   │   ├── research.py
│   │   ├── development.py
│   │   ├── code_review.py
│   │   ├── testing.py
│   │   └── documentation.py
│   ├── logging_config.py  # Structured logging with loguru
│   └── metrics.py         # Prometheus metrics
├── tests/                 # Pytest test suite
└── pyproject.toml         # Package configuration

rust-agents/
├── src/
│   ├── agent_runtime.rs   # Core Rust agent runtime
│   ├── python_bindings.rs # PyO3 FFI bindings
│   └── lib.rs             # Library entry point
├── Cargo.toml             # Rust package config
├── rustfmt.toml           # Formatting config
└── clippy.toml            # Linting config
```

### Running Tests

**Python:**

```bash
cd agents
pytest tests/ -v                    # Run all tests
pytest tests/test_core_base.py -v  # Run specific test file
pytest tests/ --cov=agents          # With coverage
pytest tests/ -k "test_research"    # Run matching tests
```

**Rust:**

```bash
cd rust-agents
cargo test                          # Run all tests
cargo test --verbose                # Verbose output
cargo test --release                # Test release build
```

### Code Quality

**Python - Auto-format and lint:**

```bash
cd agents

# Format code
black agents/
isort agents/

# Type checking
mypy agents/

# Linting
ruff check agents/ --fix
pylint agents/
```

**Rust - Auto-format and lint:**

```bash
cd rust-agents

# Format code
cargo fmt

# Linting
cargo clippy -- -D warnings

# Check all
cargo clippy --all-features --all-targets
```

### Creating a New Agent

1. **Create agent class** in `agents/specialized/`:

```python
from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus

class MyCustomAgent(Agent):
    """Custom agent for specific task."""

    @property
    def system_prompt(self) -> str:
        return "You are a specialized AI assistant that..."

    async def execute(self, input_data: str) -> AgentResult:
        if not self.validate_input(input_data):
            return AgentResult(
                status=AgentStatus.FAILED,
                output="",
                error="Invalid input",
            )

        prompt = f"{self.system_prompt}\n\nTask: {input_data}"
        response = await self._call_llm(prompt)

        return AgentResult(
            status=AgentStatus.COMPLETED,
            output=response,
            metadata={"custom_field": "value"},
        )
```

2. **Add tests** in `tests/test_specialized_my_custom.py`:

```python
import pytest
from agents.specialized.my_custom import MyCustomAgent

@pytest.mark.asyncio
async def test_my_custom_agent(mock_ollama_response):
    agent = MyCustomAgent(agent_config)
    result = await agent.execute("test input")
    assert result.status == AgentStatus.COMPLETED
```

3. **Export in** `agents/__init__.py`:

```python
from agents.specialized.my_custom import MyCustomAgent

__all__ = [..., "MyCustomAgent"]
```

### Adding Logging and Metrics

**Logging:**

```python
from agents.logging_config import logger, log_agent_execution

# In agent execute method
with log_agent_execution(self.agent_id, self.__class__.__name__, len(input_data)):
    logger.info("Starting agent execution")
    result = await self._call_llm(prompt)
    logger.debug(f"LLM response: {result[:100]}...")
```

**Metrics:**

```python
from agents.metrics import get_metrics_collector
import time

# Track execution
start_time = time.time()
result = await agent.execute(input_data)
duration = time.time() - start_time

metrics = get_metrics_collector()
metrics.record_agent_execution(
    agent_id=agent.agent_id,
    agent_type=agent.__class__.__name__,
    duration=duration,
    status=result.status.value,
)
```

### Continuous Integration

GitHub Actions workflows run automatically on push/PR:

- **Python Tests** (`.github/workflows/python-tests.yml`): Runs pytest with coverage on Python 3.10, 3.11, 3.12
- **Rust Build** (`.github/workflows/rust-build.yml`): Builds, tests, and lints Rust code
- **Docker Build** (`.github/workflows/docker-build.yml`): Validates docker-compose files and runs security scans
- **Documentation** (`.github/workflows/docs.yml`): Generates API docs and checks markdown links

### Performance Benchmarking

**Rust:**

```bash
cd rust-agents
cargo bench
```

Results saved to `target/criterion/`.

**Python:**

```bash
cd agents
pytest tests/ --benchmark-only
```

## Troubleshooting

**Python import errors:**
```bash
# Ensure package is installed in editable mode
cd agents
pip install -e ".[dev]"
```

**Rust compilation errors:**
```bash
# Clean and rebuild
cd rust-agents
cargo clean
cargo build --release
```

**Pre-commit hook failures:**
```bash
# Run specific hook to see detailed error
pre-commit run black --all-files
pre-commit run clippy --all-files
```

**Tests failing:**
```bash
# Run with verbose output
pytest tests/ -vv --tb=long

# Run specific test
pytest tests/test_core_base.py::test_agent_config -vv
```

