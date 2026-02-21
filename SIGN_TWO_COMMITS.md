# Sign Two Specific Commits (390e220 and 5a4ca7d)

**Quick Reference**: Only 2 commits in PR#69 need signing

---

## Method 1: Simple One-Liner (Recommended)

```bash
export GPG_TTY=$(tty) && \
git fetch origin && \
git checkout dev && \
git reset --hard origin/dev && \
COMMIT1=390e220 && \
COMMIT2=5a4ca7d && \
git rebase --onto HEAD \
  -X ours \
  --exec "git commit --amend --no-edit -S" \
  ${COMMIT1}^ ${COMMIT2} && \
git push --force-with-lease origin dev
```

**What it does**:
1. Sets up GPG
2. Syncs with origin/dev
3. Rebases just those 2 commits
4. Signs each one
5. Force pushes

**Time**: 30 seconds + 2 GPG passphrases

---

## Method 2: Interactive Rebase (More Control)

```bash
# 1. Sync with remote
git fetch origin
git checkout dev
git reset --hard origin/dev

# 2. Find commit before first unsigned commit
git log --oneline | grep -B1 "390e220"
# Note the commit hash just before 390e220

# 3. Start rebase from that commit
# Replace HASH_BEFORE with actual hash
git rebase -i <HASH_BEFORE>

# 4. In editor, change ONLY these lines:
#    pick 390e220 ... → edit 390e220 ...
#    pick 5a4ca7d ... → edit 5a4ca7d ...

# 5. Git will stop at each. Sign them:
git commit --amend --no-edit -S
git rebase --continue

# Repeat for second commit:
git commit --amend --no-edit -S
git rebase --continue

# 6. Force push
git push --force-with-lease origin dev
```

**Time**: 2-3 minutes

---

## Method 3: Use the Script

```bash
./sign-specific-commits.sh
```

Automated version of Method 1.

---

## Method 4: Cherry-pick and Re-sign (Safest)

```bash
# 1. Create new branch from dev
git fetch origin
git checkout -b temp-sign origin/dev

# 2. Reset to commit before 390e220
BEFORE=$(git log --oneline | grep -B1 "390e220" | head -1 | awk '{print $1}')
git reset --hard $BEFORE

# 3. Cherry-pick and sign both commits
git cherry-pick -S 390e220
git cherry-pick -S 5a4ca7d

# 4. Verify signatures
git log --show-signature -2

# 5. Force update dev
git branch -f dev HEAD
git checkout dev
git push --force-with-lease origin dev

# 6. Cleanup
git branch -D temp-sign
```

**Time**: 1-2 minutes
**Safest**: Creates temp branch first

---

## Quick Verification

After signing, verify with:

```bash
# Check those specific commits
git verify-commit 390e220 && echo "390e220 ✓ signed" || echo "390e220 ✗ not signed"
git verify-commit 5a4ca7d && echo "5a4ca7d ✓ signed" || echo "5a4ca7d ✗ not signed"

# Or check PR on GitHub
gh pr view 69 --json commits --jq '.commits[] | select(.oid | startswith("390e220") or startswith("5a4ca7d")) | "\(.oid[0:7]) Verified: \(.commit.verification.verified)"'
```

Expected output:
```
390e220 Verified: true
5a4ca7d Verified: true
```

---

## Fastest Path (Copy-Paste)

```bash
# Just run this:
export GPG_TTY=$(tty)
git fetch origin
git checkout dev
git reset --hard origin/dev

# Sign commit 390e220
git rebase -i 390e220^
# In editor: change "pick 390e220" to "edit 390e220", save and exit
git commit --amend --no-edit -S
git rebase --continue

# Sign commit 5a4ca7d
git rebase -i 5a4ca7d^
# In editor: change "pick 5a4ca7d" to "edit 5a4ca7d", save and exit
git commit --amend --no-edit -S
git rebase --continue

# Push
git push --force-with-lease origin dev
```

**Note**: This signs each commit individually to avoid rebasing the entire PR.

---

## If Anything Goes Wrong

```bash
# Abort rebase
git rebase --abort

# Reset to remote
git reset --hard origin/dev

# Try again or use Method 4 (safest)
```

---

**Recommended**: Use **Method 4** (cherry-pick) - it's the safest and creates a backup automatically.

Or just run:
```bash
./sign-specific-commits.sh
```
