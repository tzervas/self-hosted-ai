#!/usr/bin/env python3
"""
Validate documentation index integrity.

Checks:
- All links in INDEX.md point to existing files
- All markdown files are referenced in INDEX
- Token budgets are up to date
- File counts match reality
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def count_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 0.75 words)."""
    words = len(text.split())
    return int(words / 0.75)


def find_broken_links(index_path: Path) -> List[str]:
    """Find broken links in INDEX.md."""
    index_text = index_path.read_text()
    links = re.findall(r'\[.*?\]\(([^)]+)\)', index_text)

    broken = []
    for link in links:
        if link.startswith(('http://', 'https://', '#')):
            continue  # Skip external links and anchors

        # Try both relative to INDEX.md and relative to project root
        candidates = [
            Path(link),
            Path('docs') / link,
            Path(link.lstrip('../')),
        ]

        if not any(p.exists() for p in candidates):
            broken.append(link)

    return broken


def find_unreferenced_docs(index_path: Path, project_root: Path) -> List[Path]:
    """Find markdown files not referenced in INDEX.md."""
    index_text = index_path.read_text()

    # Exclude these from check
    exclude_patterns = [
        '**/node_modules/**',
        '**/.venv/**',
        '**/site-packages/**',
        '**/dist-info/**',
        'docs/archive/**',  # Archive docs intentionally not in INDEX
    ]

    all_docs = []
    for pattern in ['*.md', '**/*.md']:
        for doc in project_root.rglob(pattern):
            if not any(doc.match(excl) for excl in exclude_patterns):
                all_docs.append(doc)

    unreferenced = []
    for doc in all_docs:
        # Check if doc is mentioned in INDEX (by filename or path)
        doc_name = doc.name
        relative_path = doc.relative_to(project_root)

        if str(doc_name) not in index_text and str(relative_path) not in index_text:
            # Exclude README.md in subdirs (usually referenced indirectly)
            if doc_name != 'README.md':
                unreferenced.append(relative_path)

    return unreferenced


def validate_token_budgets(index_path: Path, project_root: Path) -> List[Tuple[str, int, int]]:
    """Check if token budgets in INDEX match actual doc sizes."""
    index_text = index_path.read_text()

    # Extract token claims from INDEX (e.g., "ARCHITECTURE.md (1,500 tokens)")
    pattern = r'\[([\w\-\.]+\.md)\]\([^)]+\).*?\(([0-9,]+)\s+tokens\)'
    claims = re.findall(pattern, index_text)

    mismatches = []
    for doc_name, claimed_tokens_str in claims:
        claimed_tokens = int(claimed_tokens_str.replace(',', ''))

        # Find the actual doc
        candidates = list(project_root.rglob(doc_name))
        if not candidates:
            continue

        actual_tokens = count_tokens(candidates[0].read_text())
        variance = abs(actual_tokens - claimed_tokens) / claimed_tokens

        # Flag if variance > 20%
        if variance > 0.20:
            mismatches.append((doc_name, claimed_tokens, actual_tokens))

    return mismatches


def validate_file_counts(index_path: Path, project_root: Path) -> List[Tuple[str, int, int]]:
    """Check if file counts in INDEX match actual counts."""
    index_text = index_path.read_text()

    # Extract file count claims (e.g., "argocd/applications/ | ~30 |")
    pattern = r'\|\s*([\w\-\/]+)\s*\|\s*~?(\d+)\s*\|'
    claims = re.findall(pattern, index_text)

    mismatches = []
    for dir_path, claimed_count_str in claims:
        claimed_count = int(claimed_count_str)

        # Count actual files in directory
        dir_full = project_root / dir_path
        if not dir_full.exists() or not dir_full.is_dir():
            continue

        actual_count = len(list(dir_full.glob('*')))

        variance = abs(actual_count - claimed_count) / max(claimed_count, 1)

        # Flag if variance > 30% (some flexibility for minor changes)
        if variance > 0.30:
            mismatches.append((dir_path, claimed_count, actual_count))

    return mismatches


def main():
    """Run all validation checks."""
    project_root = Path(__file__).parent.parent
    index_path = project_root / 'docs' / 'INDEX.md'

    if not index_path.exists():
        print("❌ docs/INDEX.md not found!")
        sys.exit(1)

    print("🔍 Validating documentation index...\n")

    errors = 0

    # Check 1: Broken links
    print("1. Checking for broken links...")
    broken_links = find_broken_links(index_path)
    if broken_links:
        print(f"   ❌ Found {len(broken_links)} broken links:")
        for link in broken_links:
            print(f"      - {link}")
        errors += len(broken_links)
    else:
        print("   ✅ All links valid")

    # Check 2: Unreferenced docs
    print("\n2. Checking for unreferenced documentation...")
    unreferenced = find_unreferenced_docs(index_path, project_root)
    if unreferenced:
        print(f"   ⚠️  Found {len(unreferenced)} unreferenced docs:")
        for doc in unreferenced:
            print(f"      - {doc}")
        print("   (These may be intentionally excluded)")
    else:
        print("   ✅ All docs referenced")

    # Check 3: Token budgets
    print("\n3. Checking token budget accuracy...")
    token_mismatches = validate_token_budgets(index_path, project_root)
    if token_mismatches:
        print(f"   ⚠️  Found {len(token_mismatches)} token budget mismatches:")
        for doc, claimed, actual in token_mismatches:
            print(f"      - {doc}: claimed {claimed}, actual ~{actual} ({abs(claimed-actual)} diff)")
        print("   (Update INDEX.md summaries if docs changed materially)")
    else:
        print("   ✅ Token budgets accurate")

    # Check 4: File counts
    print("\n4. Checking file count accuracy...")
    count_mismatches = validate_file_counts(index_path, project_root)
    if count_mismatches:
        print(f"   ⚠️  Found {len(count_mismatches)} file count mismatches:")
        for dir_path, claimed, actual in count_mismatches:
            print(f"      - {dir_path}: claimed ~{claimed}, actual {actual}")
        print("   (Update INDEX.md file counts)")
    else:
        print("   ✅ File counts accurate")

    # Summary
    print("\n" + "=" * 60)
    if errors > 0:
        print(f"❌ Validation failed with {errors} errors")
        sys.exit(1)
    else:
        print("✅ Documentation index is valid!")
        print("\n📊 Summary:")
        print(f"   - Index: {index_path}")
        print(f"   - All links valid")
        print(f"   - {len(unreferenced)} docs not in INDEX (may be intentional)")
        print(f"   - {len(token_mismatches)} token budget warnings")
        print(f"   - {len(count_mismatches)} file count warnings")
        sys.exit(0)


if __name__ == '__main__':
    main()
