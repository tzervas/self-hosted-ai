#!/usr/bin/env bash
# release.sh - Create releases with semantic versioning
# Builds and pushes to GHCR and Docker Hub
set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$PROJECT_ROOT/VERSION"

# Registry configuration
GITHUB_REPO="tzervas/self-hosted-ai"
DOCKERHUB_REPO="tzervas01/self-hosted-ai"
GHCR_REPO="ghcr.io/${GITHUB_REPO}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

die() {
  log_error "$1"
  exit 1
}

# Get current version from VERSION file
get_version() {
  if [[ -f "$VERSION_FILE" ]]; then
    cat "$VERSION_FILE"
  else
    echo "0.0.0"
  fi
}

# Parse semver components
parse_version() {
  local version="$1"
  local part="$2"

  # Remove leading 'v' if present
  version="${version#v}"

  case "$part" in
    major) echo "$version" | cut -d. -f1 ;;
    minor) echo "$version" | cut -d. -f2 ;;
    patch) echo "$version" | cut -d. -f3 | cut -d- -f1 ;;
    prerelease) echo "$version" | grep -oP '(?<=-)[^+]+' || echo "" ;;
  esac
}

# Increment version
bump_version() {
  local current="$1"
  local bump_type="$2"

  local major minor patch
  major=$(parse_version "$current" "major")
  minor=$(parse_version "$current" "minor")
  patch=$(parse_version "$current" "patch")

  case "$bump_type" in
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    patch)
      patch=$((patch + 1))
      ;;
    *)
      die "Invalid bump type: $bump_type (use major, minor, or patch)"
      ;;
  esac

  echo "${major}.${minor}.${patch}"
}

# Save version to file
save_version() {
  local version="$1"
  echo "$version" >"$VERSION_FILE"
  log_success "Updated VERSION to ${version}"
}

# =============================================================================
# Pre-release Checks
# =============================================================================
check_prerequisites() {
  log_info "Running pre-release checks..."

  # Check we're on main branch
  local branch
  branch=$(git -C "$PROJECT_ROOT" branch --show-current)
  if [[ "$branch" != "main" ]]; then
    die "Releases must be created from main branch (current: $branch)"
  fi

  # Check for uncommitted changes
  if ! git -C "$PROJECT_ROOT" diff --quiet HEAD; then
    die "Working directory has uncommitted changes"
  fi

  # Check git is up to date with remote
  git -C "$PROJECT_ROOT" fetch origin main
  local local_sha remote_sha
  local_sha=$(git -C "$PROJECT_ROOT" rev-parse HEAD)
  remote_sha=$(git -C "$PROJECT_ROOT" rev-parse origin/main)
  if [[ "$local_sha" != "$remote_sha" ]]; then
    die "Local main is not up to date with origin/main"
  fi

  # Check Docker is available
  if ! command -v docker &>/dev/null; then
    die "Docker not found"
  fi

  # Check authentication
  log_info "Checking registry authentication..."

  if ! docker info 2>/dev/null | grep -q "Username"; then
    log_warn "Not logged into Docker Hub. Run: docker login"
  fi

  # Check gh CLI for GitHub releases
  if ! command -v gh &>/dev/null; then
    die "GitHub CLI (gh) not found"
  fi

  if ! gh auth status &>/dev/null; then
    die "Not authenticated with GitHub CLI. Run: gh auth login"
  fi

  log_success "All pre-release checks passed"
}

# =============================================================================
# Build & Push
# =============================================================================
build_and_push() {
  local version="$1"
  local skip_push="${2:-false}"

  log_info "Building images for version ${version}..."

  # Build labels
  local build_date
  build_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local git_sha
  git_sha=$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)

  # Common labels
  local labels=(
    "--label" "org.opencontainers.image.version=${version}"
    "--label" "org.opencontainers.image.created=${build_date}"
    "--label" "org.opencontainers.image.revision=${git_sha}"
    "--label" "org.opencontainers.image.source=https://github.com/${GITHUB_REPO}"
    "--label" "org.opencontainers.image.licenses=MIT"
  )

  # Note: This project doesn't have custom Dockerfiles yet
  # When we add them, this section will build and push images
  log_warn "No custom Dockerfiles to build yet"
  log_info "This release will only create git tags and GitHub release"

  # Placeholder for future builds:
  # docker build "${labels[@]}" \
  #   -t "${GHCR_REPO}:${version}" \
  #   -t "${GHCR_REPO}:latest" \
  #   -t "${DOCKERHUB_REPO}:${version}" \
  #   -t "${DOCKERHUB_REPO}:latest" \
  #   -f Dockerfile .

  # if [[ "$skip_push" != "true" ]]; then
  #   log_info "Pushing to registries..."
  #   docker push "${GHCR_REPO}:${version}"
  #   docker push "${GHCR_REPO}:latest"
  #   docker push "${DOCKERHUB_REPO}:${version}"
  #   docker push "${DOCKERHUB_REPO}:latest"
  # fi
}

# =============================================================================
# Git Operations
# =============================================================================
create_git_release() {
  local version="$1"
  local tag="v${version}"

  log_info "Creating git tag ${tag}..."

  # Create annotated tag
  git -C "$PROJECT_ROOT" tag -a "$tag" -m "Release ${version}"

  # Push tag
  git -C "$PROJECT_ROOT" push origin "$tag"
  log_success "Pushed tag ${tag}"

  # Create GitHub release
  log_info "Creating GitHub release..."

  # Generate release notes from commits since last tag
  local prev_tag
  prev_tag=$(git -C "$PROJECT_ROOT" describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")

  local release_notes
  if [[ -n "$prev_tag" ]]; then
    release_notes=$(git -C "$PROJECT_ROOT" log "${prev_tag}..HEAD" --pretty=format:"- %s" --no-merges)
  else
    release_notes="Initial release"
  fi

  gh release create "$tag" \
    --repo "$GITHUB_REPO" \
    --title "Release ${version}" \
    --notes "$release_notes"

  log_success "Created GitHub release ${version}"
}

# =============================================================================
# Usage
# =============================================================================
usage() {
  cat <<EOF
Usage: $(basename "$0") [command] [options]

Commands:
  bump <type>   Bump version (major, minor, patch) and create release
  tag <version> Tag specific version and create release
  status        Show current version and release status
  help          Show this help message

Options:
  --dry-run     Show what would be done without making changes
  --skip-push   Create tags but don't push to registries

Examples:
  $(basename "$0") bump patch         # 0.1.0 -> 0.1.1
  $(basename "$0") bump minor         # 0.1.1 -> 0.2.0
  $(basename "$0") bump major         # 0.2.0 -> 1.0.0
  $(basename "$0") tag 1.0.0-rc1      # Tag specific version
  $(basename "$0") status             # Show current version

Registries:
  GitHub Container Registry: ${GHCR_REPO}
  Docker Hub: ${DOCKERHUB_REPO}

EOF
}

show_status() {
  local current
  current=$(get_version)

  echo ""
  echo -e "${BLUE}Current Version:${NC} ${current}"
  echo ""

  echo -e "${BLUE}Latest Tags:${NC}"
  git -C "$PROJECT_ROOT" tag -l --sort=-version:refname | head -5 || echo "  (no tags)"
  echo ""

  echo -e "${BLUE}Registries:${NC}"
  echo "  GitHub: ghcr.io/${GITHUB_REPO}"
  echo "  Docker Hub: ${DOCKERHUB_REPO}"
  echo ""
}

# =============================================================================
# Main
# =============================================================================
main() {
  local command="${1:-help}"
  shift || true

  # Parse global options
  local dry_run=false
  local skip_push=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        dry_run=true
        shift
        ;;
      --skip-push)
        skip_push=true
        shift
        ;;
      *)
        break
        ;;
    esac
  done

  cd "$PROJECT_ROOT"

  case "$command" in
    bump)
      local bump_type="${1:-}"
      if [[ -z "$bump_type" ]]; then
        die "Usage: $(basename "$0") bump <major|minor|patch>"
      fi

      check_prerequisites

      local current new_version
      current=$(get_version)
      new_version=$(bump_version "$current" "$bump_type")

      log_info "Bumping version: ${current} -> ${new_version}"

      if [[ "$dry_run" == "true" ]]; then
        log_warn "[DRY RUN] Would bump to ${new_version}"
        exit 0
      fi

      # Update VERSION file and commit
      save_version "$new_version"
      git add VERSION
      git commit -m "chore: bump version to ${new_version}"
      git push origin main

      # Build and create release
      build_and_push "$new_version" "$skip_push"
      create_git_release "$new_version"

      log_success "Released version ${new_version}"
      ;;

    tag)
      local version="${1:-}"
      if [[ -z "$version" ]]; then
        die "Usage: $(basename "$0") tag <version>"
      fi

      check_prerequisites

      if [[ "$dry_run" == "true" ]]; then
        log_warn "[DRY RUN] Would tag ${version}"
        exit 0
      fi

      save_version "$version"
      git add VERSION
      git commit -m "chore: set version to ${version}"
      git push origin main

      build_and_push "$version" "$skip_push"
      create_git_release "$version"

      log_success "Released version ${version}"
      ;;

    status)
      show_status
      ;;

    help | --help | -h)
      usage
      ;;

    *)
      log_error "Unknown command: $command"
      usage
      exit 1
      ;;
  esac
}

main "$@"
