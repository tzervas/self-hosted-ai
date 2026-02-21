#!/usr/bin/env bash
# sign-last-two.sh
# Sign the last 2 commits in PR#69
#
# Commits to sign:
# - 5a4ca7d: feat(scripts): add Open WebUI tools upload automation script
# - 390e220: feat(tools): add comprehensive creative production suite (5 new tools)
#
# Usage:
#   ./sign-last-two.sh

set -euo pipefail

echo "🔏 Signing Last 2 Commits in PR#69"
echo "==================================="
echo

# Set GPG TTY
export GPG_TTY=$(tty)

# Check we're on dev branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "dev" ]; then
  echo "❌ Not on dev branch (current: $CURRENT_BRANCH)"
  echo "Run: git checkout dev"
  exit 1
fi

# Show commits to sign
echo "Commits to sign:"
git log --oneline -2 dev
echo

# Backup current HEAD
BACKUP_REF=$(git rev-parse HEAD)
echo "📋 Backup: $BACKUP_REF"
echo "   (To restore: git reset --hard $BACKUP_REF)"
echo

# Confirm
read -p "Sign these 2 commits? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted"
  exit 0
fi

echo
echo "🔄 Rebasing to sign commits..."
echo

# Method 1: Rebase last 2 commits and sign
# Get commit before the 2 we want to sign
BASE_COMMIT=$(git rev-parse HEAD~2)

# Interactive rebase with auto-edit and auto-sign
GIT_SEQUENCE_EDITOR="sed -i 's/^pick/edit/g'" \
  git rebase -i $BASE_COMMIT

# We're now stopped at first commit
echo "📝 Signing commit 1/2..."
git commit --amend --no-edit -S

# Continue to next
git rebase --continue

# Now at second commit
echo "📝 Signing commit 2/2..."
git commit --amend --no-edit -S

# Continue (should finish)
git rebase --continue

echo
echo "✅ Both commits signed!"
echo

# Verify
echo "🔍 Verification:"
git log --show-signature -2 dev | grep -E "(commit|gpg:)" | head -8
echo

# Force push
echo "📤 Force pushing to origin/dev..."
if git push --force-with-lease origin dev; then
  echo "✅ Success! PR#69 updated."
  echo
  echo "Verify at: https://github.com/tzervas/self-hosted-ai/pull/69"
else
  echo "❌ Push failed!"
  echo
  echo "Restore backup: git reset --hard $BACKUP_REF"
  exit 1
fi
