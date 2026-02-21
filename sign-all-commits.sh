#!/usr/bin/env bash
# sign-all-commits.sh
# Rebase and GPG sign all commits in PR#69 (dev branch ahead of main)
#
# This script will:
# 1. Find the base commit where dev diverged from main
# 2. Rebase all commits from that point
# 3. Sign each commit with GPG
# 4. Force push to update PR#69
#
# Prerequisites:
# - GPG key configured for signing
# - Git user.signingkey configured
# - On dev branch
# - Clean working directory
#
# Usage:
#   ./sign-all-commits.sh

set -euo pipefail

echo "🔏 Signing All Commits in PR#69"
echo "================================"
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
  echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

# Check we're on dev branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "dev" ]; then
  print_error "Not on dev branch (current: $CURRENT_BRANCH)"
  echo "Run: git checkout dev"
  exit 1
fi

# Check working directory is clean
if ! git diff --quiet || ! git diff --cached --quiet; then
  print_error "Working directory has uncommitted changes"
  echo "Commit or stash changes first"
  exit 1
fi

# Find base commit
BASE_COMMIT=$(git merge-base main dev)
print_status "Base commit: ${BASE_COMMIT:0:7}"

# Count commits to sign
COMMIT_COUNT=$(git log --oneline "${BASE_COMMIT}..dev" | wc -l)
echo "  Commits to sign: $COMMIT_COUNT"
echo

# Confirm with user
echo "⚠️  WARNING: This will rewrite history and require force push"
echo "   PR#69 will be updated with signed commits"
echo
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted"
  exit 0
fi

echo
echo "🔄 Rebasing and signing commits..."
echo "===================================="
echo

# Set up GPG to use the current TTY
export GPG_TTY=$(tty)

# Method 1: Use git filter-branch to sign all commits
# This is more reliable than interactive rebase in a script

echo "  Using filter-branch to sign commits..."

# Backup current branch
git branch dev-backup-$(date +%Y%m%d-%H%M%S) || true

# Filter-branch to sign all commits
git filter-branch -f --commit-filter '
  if [ "$GIT_COMMIT" != "'"$BASE_COMMIT"'" ]; then
    git commit-tree -S "$@"
  else
    git commit-tree "$@"
  fi
' "${BASE_COMMIT}..HEAD"

print_status "All commits signed!"
echo

# Verify signing
echo "📋 Verification"
echo "==============="
echo

UNSIGNED_COUNT=$(git log --oneline --no-show-signature "${BASE_COMMIT}..HEAD" | \
  while read commit_hash commit_msg; do
    if ! git verify-commit "$commit_hash" 2>/dev/null; then
      echo "$commit_hash"
    fi
  done | wc -l)

if [ "$UNSIGNED_COUNT" -eq 0 ]; then
  print_status "All $COMMIT_COUNT commits are now signed!"
else
  print_warning "$UNSIGNED_COUNT commits still unsigned"
  echo
  echo "Unsigned commits:"
  git log --oneline --no-show-signature "${BASE_COMMIT}..HEAD" | \
    while read commit_hash commit_msg; do
      if ! git verify-commit "$commit_hash" 2>/dev/null; then
        echo "  - $commit_hash $commit_msg"
      fi
    done
fi

echo
echo "📤 Force Pushing to Origin"
echo "==========================="
echo

# Force push to update PR
echo "  Pushing to origin/dev..."
if git push --force-with-lease origin dev; then
  print_status "Force pushed successfully!"
else
  print_error "Force push failed"
  echo
  echo "Your local dev branch has been signed."
  echo "Restore backup: git reset --hard dev-backup-YYYYMMDD-HHMMSS"
  echo "Force push manually: git push --force origin dev"
  exit 1
fi

echo
echo "✅ Done!"
echo
echo "PR#69 has been updated with signed commits."
echo "Check: gh pr view 69"
echo
echo "If you need to restore the backup:"
echo "  git branch -a | grep dev-backup"
echo "  git reset --hard dev-backup-YYYYMMDD-HHMMSS"
