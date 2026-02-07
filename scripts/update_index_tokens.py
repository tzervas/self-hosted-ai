#!/usr/bin/env python3
"""
Update token counts in INDEX.md based on actual file sizes.

Uses content hashing to detect when docs have changed materially
and updates INDEX.md token estimates accordingly.
"""

import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file content."""
    if not file_path.exists():
        return ""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def estimate_tokens(text: str) -> int:
    """Estimate token count (1.3 tokens per word for documentation)."""
    words = len(text.split())
    return int(words * 1.3)


def extract_doc_claims(index_content: str) -> List[Tuple[str, str, int]]:
    """
    Extract doc claims from INDEX.md.

    Returns list of (filename, path, claimed_tokens)
    """
    pattern = r'####\s+\[([\w\-\.]+\.md)\]\(([^)]+)\)\s+\(([0-9,]+)\s+tokens\)'
    matches = re.finditer(pattern, index_content)

    claims = []
    for match in matches:
        filename = match.group(1)
        path = match.group(2)
        claimed_tokens = int(match.group(3).replace(',', ''))
        claims.append((filename, path, claimed_tokens))

    return claims


def resolve_doc_path(relative_path: str, project_root: Path) -> Path:
    """Resolve relative path to absolute path."""
    candidates = [
        project_root / relative_path,
        project_root / 'docs' / relative_path,
        project_root / relative_path.lstrip('../')
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def update_token_counts(index_path: Path, project_root: Path,
                       threshold: float = 0.20) -> int:
    """
    Update token counts in INDEX.md if variance > threshold.

    Args:
        index_path: Path to INDEX.md
        project_root: Project root directory
        threshold: Variance threshold (default 20%)

    Returns:
        Number of token counts updated
    """
    if not index_path.exists():
        print(f"❌ INDEX.md not found at {index_path}")
        return 0

    index_content = index_path.read_text()
    original_content = index_content

    # Extract all doc claims
    claims = extract_doc_claims(index_content)

    updates = 0
    print(f"📋 Checking {len(claims)} documents for token count updates...\n")

    for filename, path, claimed_tokens in claims:
        # Resolve path
        full_path = resolve_doc_path(path, project_root)

        if not full_path.exists():
            print(f"⚠️  {filename}: File not found at {path}")
            continue

        # Calculate actual tokens
        actual_tokens = estimate_tokens(full_path.read_text())

        # Calculate variance
        variance = abs(actual_tokens - claimed_tokens) / claimed_tokens if claimed_tokens else 1.0

        if variance > threshold:
            # Update token count in INDEX
            old_pattern = rf'(\[{re.escape(filename)}\]\({re.escape(path)}\)\s+\()([0-9,]+)(\s+tokens\))'
            new_value = f'\\g<1>{actual_tokens:,}\\g<3>'

            index_content = re.sub(old_pattern, new_value, index_content)

            print(f"🔄 {filename}:")
            print(f"   Claimed: {claimed_tokens:,} → Actual: {actual_tokens:,}")
            print(f"   Variance: {variance*100:.1f}% (threshold: {threshold*100:.0f}%)")
            print(f"   ✅ Updated\n")
            updates += 1
        else:
            print(f"✓ {filename}: {claimed_tokens:,} tokens (accurate, {variance*100:.1f}% variance)")

    # Write back if changes made
    if updates > 0:
        index_path.write_text(index_content)
        print(f"\n💾 Updated INDEX.md with {updates} token count corrections")
    else:
        print(f"\n✅ All token counts accurate (no updates needed)")

    return updates


def generate_hash_manifest(project_root: Path) -> Dict[str, str]:
    """
    Generate content hash manifest for all docs.

    Returns dict of {filepath: hash}
    """
    manifest = {}
    docs_dir = project_root / 'docs'

    for doc_path in docs_dir.rglob('*.md'):
        relative_path = doc_path.relative_to(project_root)
        content_hash = compute_file_hash(doc_path)
        manifest[str(relative_path)] = content_hash

    return manifest


def save_hash_manifest(manifest: Dict[str, str], output_path: Path):
    """Save hash manifest to file."""
    import json
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def compare_manifests(old_manifest: Dict[str, str],
                     new_manifest: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Compare two hash manifests.

    Returns dict with:
    - added: Files added
    - removed: Files removed
    - changed: Files with changed content
    """
    old_files = set(old_manifest.keys())
    new_files = set(new_manifest.keys())

    added = list(new_files - old_files)
    removed = list(old_files - new_files)

    changed = []
    for filepath in old_files & new_files:
        if old_manifest[filepath] != new_manifest[filepath]:
            changed.append(filepath)

    return {
        'added': sorted(added),
        'removed': sorted(removed),
        'changed': sorted(changed)
    }


def main():
    """CLI entry point."""
    import sys

    project_root = Path(__file__).parent.parent
    index_path = project_root / 'docs' / 'INDEX.md'
    manifest_path = project_root / 'docs' / '.doc_hashes.json'

    print("🔍 Content Hashing & Token Update System\n")

    # Check if manifest exists (for detecting changes)
    if manifest_path.exists():
        import json
        old_manifest = json.loads(manifest_path.read_text())
        print("📝 Found existing hash manifest, checking for changes...")

        # Generate new manifest
        new_manifest = generate_hash_manifest(project_root)

        # Compare
        diff = compare_manifests(old_manifest, new_manifest)

        if any(diff.values()):
            print("\n📊 Documentation Changes Detected:")
            if diff['added']:
                print(f"   ➕ Added ({len(diff['added'])}): {', '.join(diff['added'][:3])}{'...' if len(diff['added']) > 3 else ''}")
            if diff['removed']:
                print(f"   ➖ Removed ({len(diff['removed'])}): {', '.join(diff['removed'][:3])}{'...' if len(diff['removed']) > 3 else ''}")
            if diff['changed']:
                print(f"   🔄 Changed ({len(diff['changed'])}): {', '.join(diff['changed'][:3])}{'...' if len(diff['changed']) > 3 else ''}")
            print()
        else:
            print("   ✅ No changes detected\n")

        # Save new manifest
        save_hash_manifest(new_manifest, manifest_path)
    else:
        print("📝 No existing hash manifest found, generating initial...")
        manifest = generate_hash_manifest(project_root)
        save_hash_manifest(manifest, manifest_path)
        print(f"   ✅ Saved to {manifest_path}\n")

    # Update token counts in INDEX.md
    updates = update_token_counts(index_path, project_root)

    if updates > 0:
        print("\n⚠️  INDEX.md was updated. Remember to:")
        print("   1. Review the changes")
        print("   2. Commit the updated INDEX.md")
        print("   3. Regenerate INDEX.json: python3 scripts/generate_index_json.py")
        sys.exit(1)  # Exit with error to prevent auto-commit of potentially incorrect changes
    else:
        print("\n✅ All documentation up to date!")
        sys.exit(0)


if __name__ == '__main__':
    main()
