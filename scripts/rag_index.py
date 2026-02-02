#!/usr/bin/env python3
"""
RAG Indexing System for Self-Hosted AI Platform Documentation

This script creates a local vector database for semantic search across
all project documentation, making it searchable and queryable via LLM.

Usage:
    uv run scripts/rag_index.py index     # Index all docs
    uv run scripts/rag_index.py search "query"  # Search
    uv run scripts/rag_index.py ask "question"  # Ask with context
"""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import chromadb
import httpx
import typer
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="RAG system for self-hosted-ai documentation")
console = Console()

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DIR = PROJECT_ROOT / ".rag_index"
COLLECTION_NAME = "self-hosted-ai-docs"

# Ollama configuration - use local instance when available
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.170:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Local sentence-transformers model
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")

# File patterns to index
INCLUDE_PATTERNS = [
    "**/*.md",
    "**/*.yaml",
    "**/*.yml",
    "**/Dockerfile",
    "**/Chart.yaml",
    "**/values.yaml",
    "**/*.py",
    "**/*.rs",
    "**/*.toml",
]

EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/.venv/**",
    "**/venv/**",
    "**/target/**",
    "**/__pycache__/**",
    "**/*.egg-info/**",
    "**/htmlcov/**",
    "**/.rag_index/**",
    "**/docs/api/**",  # Generated API docs
    "**/third-party-licenses/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
    "**/.pytest_cache/**",
    "**/dist/**",
    "**/build/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/package-lock.json",
    "**/uv.lock",
]


def get_client() -> chromadb.PersistentClient:
    """Get ChromaDB persistent client."""
    CHROMA_DIR.mkdir(exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    """Get local sentence transformers embedding function."""
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


def get_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """Get or create the document collection."""
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        metadata={"description": "Self-Hosted AI Platform documentation and code"},
    )


def should_include_file(file_path: Path) -> bool:
    """Check if file should be indexed."""
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    
    # Check excludes first using string matching
    exclude_dirs = [
        "node_modules", ".git", ".venv", "venv", "target", "__pycache__",
        ".egg-info", "htmlcov", ".rag_index", "docs/api", "third-party-licenses",
        ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist", "build",
    ]
    
    for exclude_dir in exclude_dirs:
        if f"/{exclude_dir}/" in f"/{rel_path}":
            return False
        if rel_path.startswith(f"{exclude_dir}/"):
            return False
    
    # Exclude specific file patterns
    if rel_path.endswith((".min.js", ".min.css", "package-lock.json", "uv.lock")):
        return False
    
    # Check includes
    for pattern in INCLUDE_PATTERNS:
        if file_path.match(pattern):
            return True
    
    return False


def chunk_document(content: str, file_path: Path, chunk_size: int = 1500, overlap: int = 200) -> list[dict[str, Any]]:
    """Split document into overlapping chunks with metadata."""
    chunks = []
    file_type = file_path.suffix.lstrip(".")
    rel_path = str(file_path.relative_to(PROJECT_ROOT))
    
    # For small files, keep as single chunk
    if len(content) <= chunk_size:
        return [{
            "content": content,
            "file_path": rel_path,
            "file_type": file_type,
            "chunk_index": 0,
            "total_chunks": 1,
        }]
    
    # Split by sections for markdown
    if file_type == "md":
        sections = re.split(r'\n(?=#{1,3}\s)', content)
        current_chunk = ""
        
        for section in sections:
            if len(current_chunk) + len(section) <= chunk_size:
                current_chunk += section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section
        
        if current_chunk:
            chunks.append(current_chunk)
    else:
        # Generic chunking with overlap
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            
            # Try to end at a newline
            if end < len(content):
                last_newline = chunk.rfind('\n')
                if last_newline > chunk_size // 2:
                    chunk = chunk[:last_newline + 1]
                    end = start + last_newline + 1
            
            chunks.append(chunk)
            start = end - overlap
    
    return [{
        "content": chunk,
        "file_path": rel_path,
        "file_type": file_type,
        "chunk_index": i,
        "total_chunks": len(chunks),
    } for i, chunk in enumerate(chunks)]


def compute_hash(content: str) -> str:
    """Compute content hash for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@app.command()
def index(
    force: bool = typer.Option(False, "--force", "-f", help="Force re-index all files"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be indexed"),
):
    """Index all project documentation and code for RAG search."""
    
    client = get_client()
    collection = get_collection(client)
    
    # Get existing document hashes
    existing_hashes: dict[str, str] = {}
    if not force:
        try:
            existing = collection.get(include=["metadatas"])
            for i, metadata in enumerate(existing.get("metadatas", [])):
                if metadata:
                    existing_hashes[metadata.get("file_path", "")] = metadata.get("content_hash", "")
        except Exception:
            pass
    
    files_to_index: list[Path] = []
    skipped_files: list[Path] = []
    
    # Find all files to index
    for pattern in INCLUDE_PATTERNS:
        for file_path in PROJECT_ROOT.glob(pattern):
            if file_path.is_file() and should_include_file(file_path):
                try:
                    content = file_path.read_text(errors="ignore")
                    content_hash = compute_hash(content)
                    rel_path = str(file_path.relative_to(PROJECT_ROOT))
                    
                    if force or existing_hashes.get(rel_path) != content_hash:
                        files_to_index.append(file_path)
                    else:
                        skipped_files.append(file_path)
                except Exception:
                    pass
    
    if dry_run:
        console.print(f"\n[bold]Would index {len(files_to_index)} files[/bold]")
        for f in files_to_index[:20]:
            console.print(f"  • {f.relative_to(PROJECT_ROOT)}")
        if len(files_to_index) > 20:
            console.print(f"  ... and {len(files_to_index) - 20} more")
        console.print(f"\n[dim]Skipped {len(skipped_files)} unchanged files[/dim]")
        return
    
    console.print(f"\n[bold green]Indexing {len(files_to_index)} files[/bold green]")
    console.print(f"[dim]Skipping {len(skipped_files)} unchanged files[/dim]\n")
    
    all_chunks = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(files_to_index))
        
        for file_path in files_to_index:
            try:
                content = file_path.read_text(errors="ignore")
                chunks = chunk_document(content, file_path)
                
                for chunk in chunks:
                    chunk["content_hash"] = compute_hash(content)
                    all_chunks.append(chunk)
                
                progress.advance(task)
            except Exception as e:
                console.print(f"[red]Error processing {file_path}: {e}[/red]")
    
    if all_chunks:
        # Delete existing chunks for files being re-indexed
        files_being_indexed = {str(f.relative_to(PROJECT_ROOT)) for f in files_to_index}
        try:
            existing = collection.get(include=["metadatas"])
            ids_to_delete = []
            for i, (doc_id, metadata) in enumerate(zip(
                existing.get("ids", []),
                existing.get("metadatas", [])
            )):
                if metadata and metadata.get("file_path") in files_being_indexed:
                    ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
        except Exception:
            pass
        
        # Add new chunks
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating embeddings...", total=len(all_chunks))
            
            # Process in batches
            batch_size = 50
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                
                ids = [f"{chunk['file_path']}#{chunk['chunk_index']}" for chunk in batch]
                documents = [chunk["content"] for chunk in batch]
                metadatas = [{
                    "file_path": chunk["file_path"],
                    "file_type": chunk["file_type"],
                    "chunk_index": chunk["chunk_index"],
                    "total_chunks": chunk["total_chunks"],
                    "content_hash": chunk["content_hash"],
                } for chunk in batch]
                
                collection.add(ids=ids, documents=documents, metadatas=metadatas)
                progress.advance(task, len(batch))
    
    # Summary
    total_docs = collection.count()
    console.print(f"\n[bold green]✓ Indexed successfully![/bold green]")
    console.print(f"  Total chunks in index: {total_docs}")
    console.print(f"  Index location: {CHROMA_DIR}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of results"),
    file_type: str | None = typer.Option(None, "--type", "-t", help="Filter by file type"),
):
    """Search the indexed documentation."""
    
    client = get_client()
    collection = get_collection(client)
    
    where_filter = {"file_type": file_type} if file_type else None
    
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    
    if not results["documents"][0]:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    table = Table(title=f"Search Results: '{query}'", show_lines=True)
    table.add_column("Score", style="cyan", width=8)
    table.add_column("File", style="green")
    table.add_column("Preview", style="white", max_width=80)
    
    for doc, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = f"{1 - distance:.2f}"  # Convert distance to similarity
        file_path = metadata.get("file_path", "unknown")
        chunk_info = f" (chunk {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks', 1)})"
        
        # Truncate preview
        preview = doc[:200].replace("\n", " ").strip()
        if len(doc) > 200:
            preview += "..."
        
        table.add_row(score, file_path + chunk_info, preview)
    
    console.print(table)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask"),
    context_chunks: int = typer.Option(5, "--context", "-c", help="Number of context chunks"),
    model: str = typer.Option(CHAT_MODEL, "--model", "-m", help="Chat model to use"),
):
    """Ask a question using RAG (retrieval-augmented generation)."""
    
    client = get_client()
    collection = get_collection(client)
    
    # Retrieve relevant context
    results = collection.query(
        query_texts=[question],
        n_results=context_chunks,
        include=["documents", "metadatas"],
    )
    
    if not results["documents"][0]:
        console.print("[yellow]No relevant documentation found.[/yellow]")
        return
    
    # Build context
    context_parts = []
    sources = []
    for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
        file_path = metadata.get("file_path", "unknown")
        sources.append(file_path)
        context_parts.append(f"=== From {file_path} ===\n{doc}")
    
    context = "\n\n".join(context_parts)
    
    # Create prompt
    system_prompt = """You are a helpful assistant for the Self-Hosted AI Platform project.
Answer questions based on the provided documentation context.
Be concise but thorough. If the context doesn't contain enough information, say so.
Reference specific files when relevant."""

    user_prompt = f"""Context from project documentation:

{context}

Question: {question}

Answer based on the above context:"""

    console.print(f"\n[dim]Searching with model: {model}[/dim]")
    console.print(f"[dim]Using {len(sources)} context chunks from:[/dim]")
    for src in set(sources):
        console.print(f"  [dim]• {src}[/dim]")
    console.print()
    
    # Call Ollama
    try:
        with httpx.Client(timeout=120.0) as http_client:
            response = http_client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            answer = response.json()["message"]["content"]
            
            console.print(Panel(
                Markdown(answer),
                title="[bold green]Answer[/bold green]",
                border_style="green",
            ))
    except httpx.HTTPError as e:
        console.print(f"[red]Error calling Ollama: {e}[/red]")
        console.print(f"[dim]Make sure Ollama is running at {OLLAMA_BASE_URL}[/dim]")


@app.command()
def stats():
    """Show index statistics."""
    
    client = get_client()
    collection = get_collection(client)
    
    total_chunks = collection.count()
    
    # Get file type breakdown
    results = collection.get(include=["metadatas"])
    
    file_types: dict[str, int] = {}
    files: set[str] = set()
    
    for metadata in results.get("metadatas", []):
        if metadata:
            ft = metadata.get("file_type", "unknown")
            file_types[ft] = file_types.get(ft, 0) + 1
            files.add(metadata.get("file_path", ""))
    
    console.print("\n[bold]RAG Index Statistics[/bold]\n")
    console.print(f"  Total chunks: {total_chunks}")
    console.print(f"  Total files:  {len(files)}")
    console.print(f"  Index path:   {CHROMA_DIR}")
    
    console.print("\n[bold]By File Type:[/bold]")
    table = Table()
    table.add_column("Type", style="cyan")
    table.add_column("Chunks", style="green", justify="right")
    
    for ft, count in sorted(file_types.items(), key=lambda x: -x[1]):
        table.add_row(ft or "none", str(count))
    
    console.print(table)


@app.command()
def clear():
    """Clear the entire index."""
    
    if not typer.confirm("Are you sure you want to clear the index?"):
        raise typer.Abort()
    
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        console.print("[green]Index cleared successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Error clearing index: {e}[/red]")


if __name__ == "__main__":
    app()
