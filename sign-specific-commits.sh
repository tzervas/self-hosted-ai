#!/usr/bin/env bash
# sign-specific-commits.sh
# Sign specific commits 390e220 and 5a4ca7d in PR#69
#
# These are the only 2 unsigned commits remaining
#
# Usage:
#   ./sign-specific-commits.sh

set -euo pipefail

echo "🔏 Signing Commits 390e220 and 5a4ca7d"
echo "======================================="
echo

# Set GPG TTY
export GPG_TTY=$(tty)

# Fetch latest
git fetch origin

# Check we're on dev
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "dev" ]; then
  echo "❌ Not on dev branch (current: $CURRENT_BRANCH)"
  echo "Run: git checkout dev"
  exit 1
fi

# Reset to origin/dev to ensure we're in sync
echo "📥 Syncing with origin/dev..."
git reset --hard origin/dev
echo

# Show the commits to sign
echo "Commits to sign:"
echo "  1. 390e220 - feat(tools): add comprehensive creative production suite"
echo "  2. 5a4ca7d - feat(scripts): add Open WebUI tools upload automation script"
echo

# Verify they exist
if ! git cat-file -e 390e220 2>/dev/null; then
  echo "❌ Commit 390e220 not found"
  exit 1
fi

if ! git cat-file -e 5a4ca7d 2>/dev/null; then
  echo "❌ Commit 5a4ca7d not found"
  exit 1
fi

# Check if already signed
echo "🔍 Checking current signature status..."
for commit in 390e220 5a4ca7d; do
  if git verify-commit $commit 2>/dev/null; then
    echo "  ✓ $commit already signed"
  else
    echo "  ✗ $commit not signed (will sign)"
  fi
done
echo

# Confirm
read -p "Continue with signing? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted"
  exit 0
fi

echo
echo "🔄 Signing commits using filter-branch..."
echo

# Backup
BACKUP_BRANCH="dev-backup-$(date +%Y%m%d-%H%M%S)"
git branch $BACKUP_BRANCH
echo "📋 Created backup: $BACKUP_BRANCH"
echo

# Use filter-branch to sign specific commits
git filter-branch -f --commit-filter '
  COMMIT_HASH=$(git rev-parse HEAD | cut -c1-7)
  if [ "$COMMIT_HASH" = "390e220" ] || [ "$COMMIT_HASH" = "5a4ca7d" ]; then
    # Sign this commit
    git commit-tree -S "$@"
  else
    # Keep original signature status
    git commit-tree "$@"
  fi
' --all

echo
echo "✅ Commits signed!"
echo

# Verify
echo "🔍 Verification:"
for commit_hash in $(git log --oneline --all | grep -E "(390e220|5a4ca7d)" | awk '{print $1}'); do
  if git verify-commit $commit_hash 2>/dev/null; then
    echo "  ✓ $commit_hash is signed"
  else
    echo "  ✗ $commit_hash NOT signed (GPG may have failed)"
  fi
done
echo

# Force push
echo "📤 Force pushing to origin/dev..."
read -p "Push to update PR#69? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Not pushing. To push manually:"
  echo "  git push --force origin dev"
  exit 0
fi

if git push --force-with-lease origin dev; then
  echo "✅ Success! PR#69 updated."
  echo
  echo "Verify at: https://github.com/tzervas/self-hosted-ai/pull/69/commits"
  echo
  echo "Backup branch: $BACKUP_BRANCH"
  echo "To restore: git reset --hard $BACKUP_BRANCH"
else
  echo "❌ Push failed!"
  echo
  echo "Restore: git reset --hard $BACKUP_BRANCH"
  exit 1
fi
