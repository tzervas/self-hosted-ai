#!/usr/bin/env python3
"""
Generate INDEX.json sidecar from INDEX.md for machine-readable access.

This enables:
- Programmatic doc navigation by agents
- Automated validation and updates
- Content change detection via hashing
- API-based documentation queries
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file content."""
    if not file_path.exists():
        return ""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def estimate_tokens(text: str) -> int:
    """Estimate token count (1.3 tokens per word for documentation)."""
    words = len(text.split())
    return int(words * 1.3)


def parse_index_md(index_path: Path, project_root: Path) -> Dict[str, Any]:
    """
    Parse INDEX.md and extract structured data.

    Returns dict with:
    - metadata
    - navigation_matrix
    - documents
    - quick_references
    - emergency_procedures
    """
    if not index_path.exists():
        raise FileNotFoundError(f"INDEX.md not found at {index_path}")

    content = index_path.read_text()

    # Extract metadata
    metadata = {
        "generated": datetime.now().isoformat(),
        "source_file": str(index_path.relative_to(project_root)),
        "version": "1.0",
        "index_hash": compute_file_hash(index_path)
    }

    # Extract navigation matrix
    navigation_matrix = extract_navigation_matrix(content)

    # Extract document summaries
    documents = extract_documents(content, project_root)

    # Extract quick references
    quick_refs = extract_quick_references(content)

    # Extract emergency procedures
    emergency = extract_emergency_procedures(content)

    # Compute statistics
    stats = compute_statistics(documents, project_root)

    return {
        "metadata": metadata,
        "navigation_matrix": navigation_matrix,
        "documents": documents,
        "quick_references": quick_refs,
        "emergency_procedures": emergency,
        "statistics": stats
    }


def extract_navigation_matrix(content: str) -> Dict[str, Any]:
    """Extract navigation matrix from INDEX.md."""
    matrix = {
        "by_persona": [],
        "by_task": [],
        "by_urgency": []
    }

    # Extract "By Persona" table
    persona_section = re.search(
        r'### By Persona\s*\n\n\|.*?\n\|.*?\n((?:\|.*?\n)+)',
        content,
        re.MULTILINE
    )
    if persona_section:
        rows = persona_section.group(1).strip().split('\n')
        for row in rows:
            cells = [c.strip() for c in row.split('|')[1:-1]]
            if len(cells) >= 3:
                matrix["by_persona"].append({
                    "persona": cells[0].strip('*'),
                    "start_here": cells[1],
                    "then_read": cells[2]
                })

    # Extract "By Task" table
    task_section = re.search(
        r'### By Task\s*\n\n\|.*?\n\|.*?\n((?:\|.*?\n)+)',
        content,
        re.MULTILINE
    )
    if task_section:
        rows = task_section.group(1).strip().split('\n')
        for row in rows:
            cells = [c.strip() for c in row.split('|')[1:-1]]
            if len(cells) >= 4:
                matrix["by_task"].append({
                    "task": cells[0].strip('*'),
                    "primary_docs": cells[1],
                    "supporting_files": cells[2],
                    "cli_tools": cells[3]
                })

    return matrix


def extract_documents(content: str, project_root: Path) -> List[Dict[str, Any]]:
    """Extract all documented files with summaries and metadata."""
    documents = []

    # Pattern: #### [FILENAME](path) (X tokens)
    # Followed by summary information
    doc_pattern = r'####\s+\[([\w\-\.]+\.md)\]\(([^)]+)\)\s+\(([0-9,]+)\s+tokens\)\s*\n\*\*(\w+)\*\*:\s+([^\n]+)'

    matches = re.finditer(doc_pattern, content)

    for match in matches:
        filename = match.group(1)
        path = match.group(2)
        claimed_tokens = int(match.group(3).replace(',', ''))
        field_name = match.group(4)  # Purpose, Mission, etc.
        field_value = match.group(5)

        # Resolve full path
        full_path = resolve_doc_path(path, project_root)

        # Compute hash and actual tokens
        file_hash = ""
        actual_tokens = 0
        if full_path and full_path.exists():
            file_hash = compute_file_hash(full_path)
            actual_tokens = estimate_tokens(full_path.read_text())

        # Extract additional metadata (Key Sections, Dependencies, When to Read)
        doc_section_start = match.end()
        doc_section_end = content.find('####', doc_section_start)
        if doc_section_end == -1:
            doc_section_end = content.find('---', doc_section_start)

        doc_content = content[doc_section_start:doc_section_end]

        key_sections = extract_list_items(doc_content, r'\*\*Key Sections\*\*:')
        dependencies = extract_list_items(doc_content, r'\*\*Dependencies\*\*:')
        when_to_read = extract_field(doc_content, r'\*\*When to Read\*\*:\s*([^\n]+)')

        documents.append({
            "filename": filename,
            "path": path,
            "full_path": str(full_path) if full_path else None,
            "purpose": field_value if field_name in ["Purpose", "Mission"] else "",
            "claimed_tokens": claimed_tokens,
            "actual_tokens": actual_tokens,
            "token_variance": abs(actual_tokens - claimed_tokens) / claimed_tokens if claimed_tokens else 0,
            "content_hash": file_hash,
            "key_sections": key_sections,
            "dependencies": dependencies,
            "when_to_read": when_to_read,
            "exists": full_path.exists() if full_path else False
        })

    return documents


def extract_list_items(text: str, pattern: str) -> List[str]:
    """Extract list items after a pattern."""
    match = re.search(pattern, text)
    if not match:
        return []

    start = match.end()
    lines = text[start:].split('\n')
    items = []

    for line in lines:
        line = line.strip()
        if line.startswith('-'):
            items.append(line[1:].strip())
        elif line.startswith('*'):
            items.append(line.lstrip('*').strip())
        elif not line or line.startswith('**'):
            break

    return items


def extract_field(text: str, pattern: str) -> str:
    """Extract a single field value."""
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def resolve_doc_path(relative_path: str, project_root: Path) -> Path:
    """Resolve relative path to absolute path."""
    # Try multiple resolution strategies
    candidates = [
        project_root / relative_path,
        project_root / 'docs' / relative_path,
        project_root / relative_path.lstrip('../')
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]  # Return first even if doesn't exist


def extract_quick_references(content: str) -> Dict[str, List[str]]:
    """Extract quick reference sections."""
    refs = {
        "commands": [],
        "endpoints": [],
        "sync_waves": [],
        "namespaces": []
    }

    # Extract common commands
    cmd_section = re.search(
        r'### Common Commands\s*```bash\s*\n(.*?)\n```',
        content,
        re.DOTALL
    )
    if cmd_section:
        cmds = cmd_section.group(1).strip().split('\n')
        refs["commands"] = [c.strip() for c in cmds if c.strip() and not c.strip().startswith('#')]

    # Extract service endpoints
    endpoint_pattern = r'- \*\*?(\w+[\w\s]*)\*\*?: (https?://[^\s]+)'
    refs["endpoints"] = [
        {"service": m.group(1), "url": m.group(2)}
        for m in re.finditer(endpoint_pattern, content)
    ]

    # Extract sync waves
    wave_section = re.search(
        r'### ArgoCD Sync Waves.*?\n\n\|.*?\n\|.*?\n((?:\|.*?\n)+)',
        content,
        re.DOTALL
    )
    if wave_section:
        rows = wave_section.group(1).strip().split('\n')
        for row in rows:
            cells = [c.strip() for c in row.split('|')[1:-1]]
            if len(cells) >= 3:
                refs["sync_waves"].append({
                    "wave": cells[0],
                    "services": cells[1],
                    "purpose": cells[2]
                })

    return refs


def extract_emergency_procedures(content: str) -> Dict[str, List[str]]:
    """Extract emergency procedures section."""
    procedures = {}

    # Find emergency section
    emergency_section = re.search(
        r'## 🚨 Emergency Procedures.*?(?=##|\Z)',
        content,
        re.DOTALL
    )

    if not emergency_section:
        return procedures

    section_text = emergency_section.group(0)

    # Extract each emergency type
    emergency_types = [
        "Production Service Down",
        "Deployment Failing",
        "Security Incident"
    ]

    for etype in emergency_types:
        pattern = rf'\*\*{etype}\?\*\*\s*\n((?:\d+\..*?\n)+)'
        match = re.search(pattern, section_text)
        if match:
            steps = []
            for line in match.group(1).split('\n'):
                line = line.strip()
                if line and re.match(r'^\d+\.', line):
                    steps.append(re.sub(r'^\d+\.\s*', '', line))
            procedures[etype.lower().replace(' ', '_')] = steps

    return procedures


def compute_statistics(documents: List[Dict], project_root: Path) -> Dict[str, Any]:
    """Compute documentation statistics."""
    total_claimed_tokens = sum(d["claimed_tokens"] for d in documents)
    total_actual_tokens = sum(d["actual_tokens"] for d in documents)

    # Count files by category
    all_docs = list(project_root.rglob('*.md'))
    indexed_docs = len(documents)

    return {
        "total_documents": len(documents),
        "total_claimed_tokens": total_claimed_tokens,
        "total_actual_tokens": total_actual_tokens,
        "token_accuracy": 1.0 - (abs(total_actual_tokens - total_claimed_tokens) / total_claimed_tokens) if total_claimed_tokens else 1.0,
        "documents_indexed": indexed_docs,
        "documents_in_project": len(all_docs),
        "index_coverage": indexed_docs / len(all_docs) if all_docs else 0,
        "missing_documents": len(all_docs) - indexed_docs
    }


def generate_index_json(project_root: Path) -> Dict[str, Any]:
    """Main function to generate INDEX.json."""
    index_path = project_root / 'docs' / 'INDEX.md'

    print(f"📄 Parsing INDEX.md from {index_path}...")
    index_data = parse_index_md(index_path, project_root)

    print(f"✅ Parsed {len(index_data['documents'])} documents")
    print(f"📊 Statistics:")
    print(f"   - Claimed tokens: {index_data['statistics']['total_claimed_tokens']:,}")
    print(f"   - Actual tokens: {index_data['statistics']['total_actual_tokens']:,}")
    print(f"   - Token accuracy: {index_data['statistics']['token_accuracy']*100:.1f}%")
    print(f"   - Index coverage: {index_data['statistics']['index_coverage']*100:.1f}%")

    return index_data


def save_index_json(data: Dict[str, Any], output_path: Path):
    """Save INDEX.json with pretty formatting."""
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"💾 Saved INDEX.json to {output_path}")


def main():
    """CLI entry point."""
    project_root = Path(__file__).parent.parent

    print("🚀 Generating INDEX.json sidecar...\n")

    # Generate index data
    index_data = generate_index_json(project_root)

    # Save to docs/INDEX.json
    output_path = project_root / 'docs' / 'INDEX.json'
    save_index_json(index_data, output_path)

    print("\n✨ Done! INDEX.json is ready for machine-readable access.")
    print(f"\nUsage:")
    print(f"  - API: Load {output_path} to query documentation programmatically")
    print(f"  - Validation: Compare content_hash to detect changes")
    print(f"  - Navigation: Use navigation_matrix for agent routing")


if __name__ == '__main__':
    main()
