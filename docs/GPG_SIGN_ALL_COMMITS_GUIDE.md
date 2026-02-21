# GPG Sign All Commits in PR#69 Guide

**Date**: 2026-02-21
**PR**: #69 (dev → main)
**Issue**: 20 commits in PR#69 are unsigned (Verified: null)

---

## Quick Start (Recommended Method)

### Method 1: Auto-sign with Filter-Branch (Fastest)

```bash
cd /home/kang/Documents/projects/github/homelab-cluster/self-hosted-ai

# Run the automated script
./sign-all-commits.sh
```

**What it does**:
- Finds base commit where dev diverged from main
- Uses `git filter-branch` to sign all 20 commits
- Creates backup branch before modifying
- Force pushes to update PR#69
- Verifies all commits are signed

**Time**: ~2 minutes (includes GPG passphrase prompts)

---

## Method 2: Interactive Rebase (Manual Control)

If you want more control over the process:

### Step 1: Start Interactive Rebase

```bash
# Find base commit
BASE=$(git merge-base main dev)
echo "Base commit: $BASE"

# Start interactive rebase
git rebase -i $BASE
```

### Step 2: Mark All Commits for Edit

In the editor that opens, change **every** line from:
```
pick a44d81c refactor(comfyui): install WanVideo deps...
pick 580bf34 feat(comfyui): use NFS shared models storage...
pick 84b4a60 fix(gpu-worker): add revisionHistoryLimit...
...
```

To:
```
edit a44d81c refactor(comfyui): install WanVideo deps...
edit 580bf34 feat(comfyui): use NFS shared models storage...
edit 84b4a60 fix(gpu-worker): add revisionHistoryLimit...
...
```

**Vim shortcut**: `:%s/^pick/edit/g` then `:wq`

### Step 3: Sign Each Commit

Git will stop at each commit. For each one:

```bash
# Sign the commit (preserving message and author)
git commit --amend --no-edit -S

# Continue to next commit
git rebase --continue
```

Repeat for all 20 commits. This will take ~5 minutes if you automate it.

### Step 4: Force Push

```bash
git push --force-with-lease origin dev
```

---

## Method 3: One-Liner Automated Rebase (Advanced)

For experienced users who trust automation:

```bash
# Export GPG TTY
export GPG_TTY=$(tty)

# Find base commit
BASE=$(git merge-base main dev)

# Rebase with auto-signing
GIT_SEQUENCE_EDITOR="sed -i 's/^pick/edit/g'" \
  git rebase -i $BASE \
  --exec 'git commit --amend --no-edit -S'

# Force push
git push --force-with-lease origin dev
```

**Warning**: This will prompt for GPG passphrase for each commit (20 times). Consider using `gpg-agent` with cached passphrase.

---

## Method 4: Squash and Re-sign (Nuclear Option)

If you want to condense all changes into fewer commits:

```bash
# Find base
BASE=$(git merge-base main dev)

# Soft reset to base (keeps all changes staged)
git reset --soft $BASE

# Create new signed commit with all changes
git commit -S -m "feat(sso,gpu-worker): Complete SSO integration and fix GPU worker availability

## Complete Summary

This mega-commit includes all changes from PR#69:
- SSO integration for all 12 web services
- GPU worker (ollama-gpu) fixes and NFS storage
- Creative production suite (5 new Open WebUI tools)
- Documentation updates (1200+ lines)
- ArgoCD configuration for OIDC

All previous commits squashed for clean history.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Force push
git push --force origin dev
```

**Pros**: Clean single signed commit
**Cons**: Loses granular commit history

---

## Verify Signing After Push

```bash
# Check PR commits are signed
gh pr view 69 --json commits --jq '.commits[] | "\(.oid[0:7]) \(.messageHeadline) - Verified: \(.commit.verification.verified)"'

# Expected output: all should show "Verified: true"

# Or check locally
git log --show-signature origin/dev ^main | grep "gpg: Good signature"
```

---

## Troubleshooting

### "gpg failed to sign the data"

**Cause**: GPG agent not running or passphrase cache expired

**Fix**:
```bash
# Start GPG agent
eval $(gpg-agent --daemon)

# Test signing
echo "test" | gpg --clearsign

# If passphrase prompt works, try again
```

### "error: cannot 'commit' with modification or unmerged files"

**Cause**: Rebase conflict or uncommitted changes

**Fix**:
```bash
# Check status
git status

# If conflict, resolve and continue
git add .
git rebase --continue

# If stuck, abort and start over
git rebase --abort
```

### "force push rejected"

**Cause**: Someone else pushed to dev since you started

**Fix**:
```bash
# Fetch latest
git fetch origin

# Rebase your signed commits on top
git rebase origin/dev

# Force push with lease (safer)
git push --force-with-lease origin dev
```

### "GPG passphrase prompt not showing"

**Cause**: TTY not set for GPG

**Fix**:
```bash
# Set GPG TTY
export GPG_TTY=$(tty)

# Test
echo "test" | gpg --clearsign
```

### "Too many passphrase prompts"

**Solution 1: Cache passphrase**:
```bash
# Edit ~/.gnupg/gpg-agent.conf
default-cache-ttl 3600
max-cache-ttl 7200

# Reload agent
gpg-connect-agent reloadagent /bye
```

**Solution 2: Use Method 4 (squash)**:
- One commit = one passphrase prompt

---

## Backup and Restore

### Before Starting

```bash
# Create backup branch
git branch dev-backup-$(date +%Y%m%d-%H%M%S)

# List backups
git branch -a | grep dev-backup
```

### Restore from Backup

```bash
# If something goes wrong
git checkout dev
git reset --hard dev-backup-YYYYMMDD-HHMMSS

# Force push original state
git push --force origin dev
```

---

## Post-Signing Checklist

- [ ] All commits show "Verified: true" in PR#69
- [ ] PR#69 shows green "Verified" badge on commits
- [ ] CI/CD passes (if any)
- [ ] No force-push conflicts with other contributors
- [ ] Backup branch created (in case of issues)

---

## Why Sign Commits?

1. **Authenticity**: Proves you wrote the code
2. **Integrity**: Detects tampering
3. **Trust**: GitHub shows "Verified" badge
4. **Compliance**: Some orgs require signed commits
5. **Best Practice**: Recommended for production repos

---

## Alternative: Sign New Commits Going Forward

If you don't want to rewrite history for PR#69:

```bash
# Enable commit signing globally
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_GPG_KEY_ID

# All future commits will be signed automatically
```

Then:
- Let PR#69 merge with unsigned commits (accepted by GitHub)
- All **new** commits will be signed going forward

---

## Recommended Approach

**For this PR#69**: Use **Method 1** (automated script)
- Fastest
- Least error-prone
- Creates backup automatically
- Verifies results

**For future commits**: Enable `commit.gpgsign true` globally

---

## Script Usage

```bash
# Method 1: Automated
./sign-all-commits.sh

# Follow prompts:
# 1. Confirm you're on dev branch
# 2. Confirm rewrite history
# 3. Enter GPG passphrase (may be multiple times)
# 4. Script force pushes to origin/dev
# 5. PR#69 automatically updates
```

**Expected output**:
```
🔏 Signing All Commits in PR#69
================================

✓ Base commit: 390e220
  Commits to sign: 20

⚠️  WARNING: This will rewrite history and require force push
   PR#69 will be updated with signed commits

Continue? (y/N) y

🔄 Rebasing and signing commits...
====================================
  Using filter-branch to sign commits...
✓ All commits signed!

📋 Verification
===============
✓ All 20 commits are now signed!

📤 Force Pushing to Origin
===========================
  Pushing to origin/dev...
✓ Force pushed successfully!

✅ Done!

PR#69 has been updated with signed commits.
Check: gh pr view 69
```

---

**Ready to proceed?**
```bash
./sign-all-commits.sh
```

Or choose one of the manual methods above for more control.
