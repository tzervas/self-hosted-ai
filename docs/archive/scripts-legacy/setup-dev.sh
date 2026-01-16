#!/usr/bin/env bash
# Setup script for self-hosted-ai development environment
# Installs all dependencies for Python agents, Rust runtime, and pre-commit hooks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Setting up self-hosted-ai development environment"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
check_python() {
  echo "==> Checking Python version..."
  if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
  fi

  PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
  REQUIRED_VERSION="3.10"

  if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher required (found $PYTHON_VERSION)${NC}"
    exit 1
  fi

  echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
}

# Install Python agents
install_python_agents() {
  echo "==> Installing Python agent framework..."
  cd "${PROJECT_ROOT}/agents"
  
  if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
  fi

  source venv/bin/activate
  pip install --upgrade pip setuptools wheel
  pip install -e ".[dev]"
  
  echo -e "${GREEN}✓ Python agents installed${NC}"
}

# Install Rust runtime
install_rust_runtime() {
  echo "==> Installing Rust agent runtime..."
  
  if ! command -v cargo &>/dev/null; then
    echo -e "${YELLOW}Warning: cargo not found. Install Rust from https://rustup.rs/${NC}"
    echo "Skipping Rust installation..."
    return 0
  fi

  cd "${PROJECT_ROOT}/rust-agents"
  cargo build --release
  
  echo -e "${GREEN}✓ Rust runtime built${NC}"
}

# Install pre-commit hooks
install_precommit() {
  echo "==> Installing pre-commit hooks..."
  
  if ! command -v pre-commit &>/dev/null; then
    pip install pre-commit
  fi

  cd "${PROJECT_ROOT}"
  pre-commit install
  pre-commit install --hook-type commit-msg
  
  echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
}

# Run tests to verify installation
run_tests() {
  echo "==> Running tests to verify installation..."
  
  cd "${PROJECT_ROOT}/agents"
  source venv/bin/activate
  pytest tests/ -v --tb=short
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
  else
    echo -e "${YELLOW}Warning: Some tests failed${NC}"
  fi
}

# Main installation flow
main() {
  check_python
  install_python_agents
  install_rust_runtime
  install_precommit
  
  echo ""
  echo -e "${GREEN}==> Setup complete!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Activate Python virtual environment: source agents/venv/bin/activate"
  echo "  2. Run tests: cd agents && pytest tests/"
  echo "  3. Check formatting: pre-commit run --all-files"
  echo "  4. Start coding!"
  echo ""
  
  # Optionally run tests
  read -p "Run tests now? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    run_tests
  fi
}

# Run main installation
main "$@"
