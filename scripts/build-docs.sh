#!/usr/bin/env bash
set -euo pipefail

# Build and optionally push the docs-site container image.
#
# Usage:
#   ./scripts/build-docs.sh              # Build only
#   ./scripts/build-docs.sh --push       # Build and push to GHCR
#   ./scripts/build-docs.sh --local      # Build and serve locally (port 8080)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="ghcr.io/tzervas/self-hosted-ai-docs"
IMAGE_TAG="${DOCS_TAG:-latest}"

cd "$PROJECT_ROOT"

case "${1:-}" in
  --push)
    echo "Building docs-site image: ${IMAGE_NAME}:${IMAGE_TAG}"
    docker build \
      -f containers/docs-site/Dockerfile \
      -t "${IMAGE_NAME}:${IMAGE_TAG}" \
      .
    echo "Pushing to GHCR..."
    docker push "${IMAGE_NAME}:${IMAGE_TAG}"
    echo "Done: ${IMAGE_NAME}:${IMAGE_TAG}"
    ;;
  --local)
    echo "Building and serving locally on http://localhost:8080"
    docker build \
      -f containers/docs-site/Dockerfile \
      -t docs-site:local \
      .
    docker run --rm -p 8080:8080 docs-site:local
    ;;
  *)
    echo "Building docs-site image: ${IMAGE_NAME}:${IMAGE_TAG}"
    docker build \
      -f containers/docs-site/Dockerfile \
      -t "${IMAGE_NAME}:${IMAGE_TAG}" \
      .
    echo "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "To push:  ./scripts/build-docs.sh --push"
    echo "To serve: ./scripts/build-docs.sh --local"
    ;;
esac
