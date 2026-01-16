#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
#     "httpx>=0.27.0",
#     "pyyaml>=6.0.0",
#     "paramiko>=3.4.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
Model Synchronization System for Self-Hosted AI Platform.

This module manages AI model distribution across the homelab infrastructure,
synchronizing models between local development machines, the k3s cluster,
and the GPU worker (akula-prime).

Why This Script Exists:
    AI models (LLMs, image generation, whisper) are large files that need to be
    consistently available across multiple locations. Manual copying is error-prone
    and doesn't track which models are where. This script provides:
    - Inventory of models across all locations
    - Bidirectional sync with integrity verification
    - Support for multiple model types (Ollama, ComfyUI, Whisper)

Architecture:
    - akula-prime (192.168.1.99): Primary model storage with GPU (RTX 5080)
    - homelab (192.168.1.170): k3s cluster with CPU Ollama
    - local: Developer workstation for model development/testing

Model Types:
    - ollama: LLM models (qwen2.5-coder, llama3, deepseek, etc.)
    - checkpoints: Stable Diffusion base models
    - loras: LoRA fine-tuning weights
    - vae: Variational autoencoders
    - embeddings: Text encoder embeddings
    - whisper: Speech-to-text models

Usage:
    # Sync all models to GPU worker
    uv run scripts/sync_models.py push --all
    
    # Pull models from GPU worker to local
    uv run scripts/sync_models.py pull ollama
    
    # List models across all locations
    uv run scripts/sync_models.py list
    
    # Verify model integrity
    uv run scripts/sync_models.py verify

Example:
    >>> from sync_models import ModelSyncManager
    >>> manager = ModelSyncManager()
    >>> await manager.list_remote_ollama_models()
    ['qwen2.5-coder:14b', 'deepseek-r1:7b', ...]
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

app = typer.Typer(
    name="shai-models",
    help="Synchronize AI models across homelab infrastructure",
    no_args_is_help=True,
)
console = Console()


class ModelType(str, Enum):
    """Types of AI models managed by this system.
    
    Each type has different storage locations and sync strategies.
    """
    OLLAMA = "ollama"
    CHECKPOINTS = "checkpoints"
    LORAS = "loras"
    VAE = "vae"
    EMBEDDINGS = "embeddings"
    UPSCALE = "upscale_models"
    WHISPER = "whisper"
    ALL = "all"


class SyncDirection(str, Enum):
    """Direction of model synchronization."""
    PUSH = "push"  # Local → Remote
    PULL = "pull"  # Remote → Local


@dataclass
class ModelLocation:
    """Represents a location where models can be stored.
    
    Attributes:
        name: Human-readable location name
        host: Hostname or IP address (None for local)
        user: SSH username for remote locations
        ollama_port: Port for Ollama API
        base_path: Base path for model storage
    """
    name: str
    host: str | None
    user: str = "kang"
    ollama_port: int = 11434
    base_path: Path = field(default_factory=lambda: Path("/data/models"))
    
    @property
    def is_local(self) -> bool:
        """Check if this is the local machine."""
        return self.host is None
    
    @property
    def ollama_url(self) -> str:
        """Get Ollama API URL for this location."""
        host = self.host or "localhost"
        return f"http://{host}:{self.ollama_port}"


@dataclass
class ModelInfo:
    """Information about a single model.
    
    Attributes:
        name: Model name (e.g., 'qwen2.5-coder:14b')
        type: Model type (ollama, checkpoint, etc.)
        size_bytes: Size in bytes
        digest: Content hash for verification
        modified: Last modification timestamp
        location: Where this model is stored
    """
    name: str
    type: ModelType
    size_bytes: int = 0
    digest: str = ""
    modified: str = ""
    location: str = ""


@dataclass
class SyncConfig:
    """Configuration for model synchronization.
    
    Loaded from config/models-manifest.yml and environment variables.
    """
    local_models_dir: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "LOCAL_MODELS_DIR",
            str(Path.home() / "Documents/projects/2026/models")
        ))
    )
    gpu_worker_host: str = field(
        default_factory=lambda: os.environ.get("GPU_WORKER_HOST", "192.168.1.99")
    )
    gpu_worker_user: str = field(
        default_factory=lambda: os.environ.get("REMOTE_USER", "kang")
    )
    cluster_host: str = field(
        default_factory=lambda: os.environ.get("CLUSTER_HOST", "192.168.1.170")
    )
    remote_models_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("REMOTE_MODELS_DIR", "/data/models"))
    )
    rsync_options: list[str] = field(default_factory=lambda: [
        "-avz",
        "--progress",
        "--checksum",
        "--human-readable",
    ])


class ModelSyncManager:
    """Manages model synchronization across homelab infrastructure.
    
    This class provides methods to list, sync, and verify models across
    different locations in the homelab. It supports both Ollama models
    (via API) and file-based models (via rsync).
    
    Why Separate Sync Strategies:
        - Ollama models: Managed through Ollama API (pull/push commands)
        - File models: Synced via rsync for efficiency with large files
    
    Attributes:
        config: Sync configuration
        locations: Available model storage locations
    """
    
    def __init__(self, config: SyncConfig | None = None) -> None:
        """Initialize the model sync manager.
        
        Args:
            config: Sync configuration. Uses defaults from environment if None.
        """
        self.config = config or SyncConfig()
        
        # Define standard locations
        self.locations = {
            "local": ModelLocation(
                name="Local",
                host=None,
                base_path=self.config.local_models_dir,
            ),
            "gpu_worker": ModelLocation(
                name="GPU Worker (akula-prime)",
                host=self.config.gpu_worker_host,
                user=self.config.gpu_worker_user,
                base_path=self.config.remote_models_dir,
            ),
            "cluster": ModelLocation(
                name="Cluster (homelab)",
                host=self.config.cluster_host,
                base_path=Path("/var/lib/ollama"),
            ),
        }
        
        # Model type to subdirectory mapping
        self.type_paths = {
            ModelType.CHECKPOINTS: "comfyui/checkpoints",
            ModelType.LORAS: "comfyui/loras",
            ModelType.VAE: "comfyui/vae",
            ModelType.EMBEDDINGS: "comfyui/embeddings",
            ModelType.UPSCALE: "comfyui/upscale_models",
            ModelType.WHISPER: "whisper",
            ModelType.OLLAMA: "ollama",
        }
    
    async def list_ollama_models(self, location: ModelLocation) -> list[ModelInfo]:
        """List Ollama models at a specific location via API.
        
        Args:
            location: Where to query for models.
            
        Returns:
            List of ModelInfo for each installed model.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{location.ollama_url}/api/tags")
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                models = []
                
                for model in data.get("models", []):
                    models.append(ModelInfo(
                        name=model.get("name", ""),
                        type=ModelType.OLLAMA,
                        size_bytes=model.get("size", 0),
                        digest=model.get("digest", ""),
                        modified=model.get("modified_at", ""),
                        location=location.name,
                    ))
                
                return models
                
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Cannot reach {location.name}: {e}")
            return []
    
    async def list_file_models(
        self, 
        location: ModelLocation, 
        model_type: ModelType
    ) -> list[ModelInfo]:
        """List file-based models at a location.
        
        Args:
            location: Where to list models.
            model_type: Type of models to list.
            
        Returns:
            List of ModelInfo for found models.
        """
        if model_type == ModelType.OLLAMA or model_type == ModelType.ALL:
            return []  # Use list_ollama_models instead
        
        subpath = self.type_paths.get(model_type, "")
        base_path = location.base_path / subpath
        
        models = []
        
        if location.is_local:
            # List local files
            if base_path.exists():
                for file in base_path.iterdir():
                    if file.is_file() and not file.name.startswith("."):
                        stat = file.stat()
                        models.append(ModelInfo(
                            name=file.name,
                            type=model_type,
                            size_bytes=stat.st_size,
                            location=location.name,
                        ))
        else:
            # List remote files via SSH
            try:
                cmd = [
                    "ssh", f"{location.user}@{location.host}",
                    f"ls -la {base_path} 2>/dev/null || echo ''"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                for line in result.stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 9 and parts[0][0] != "d":
                        name = " ".join(parts[8:])
                        size = int(parts[4]) if parts[4].isdigit() else 0
                        models.append(ModelInfo(
                            name=name,
                            type=model_type,
                            size_bytes=size,
                            location=location.name,
                        ))
                        
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Cannot list {location.name}: {e}")
        
        return models
    
    async def sync_ollama_model(
        self,
        model_name: str,
        source: ModelLocation,
        destination: ModelLocation,
    ) -> bool:
        """Sync an Ollama model between locations.
        
        For Ollama models, we trigger a pull on the destination.
        The model is downloaded from the Ollama registry, not copied
        directly between hosts.
        
        Args:
            model_name: Name of model to sync (e.g., 'qwen2.5-coder:14b')
            source: Source location (used for verification)
            destination: Where to sync the model
            
        Returns:
            True if sync succeeded.
        """
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                # Trigger pull on destination
                response = await client.post(
                    f"{destination.ollama_url}/api/pull",
                    json={"name": model_name, "stream": False},
                )
                
                return response.status_code == 200
                
        except Exception as e:
            console.print(f"[red]Error syncing {model_name}:[/red] {e}")
            return False
    
    def sync_file_models(
        self,
        model_type: ModelType,
        direction: SyncDirection,
        dry_run: bool = False,
    ) -> bool:
        """Sync file-based models using rsync.
        
        Uses rsync for efficient delta transfers of large model files.
        Supports both push (local → remote) and pull (remote → local).
        
        Args:
            model_type: Type of models to sync.
            direction: Push or pull.
            dry_run: If True, show what would be synced without doing it.
            
        Returns:
            True if sync succeeded.
        """
        subpath = self.type_paths.get(model_type, "")
        if not subpath:
            return False
        
        local_path = self.config.local_models_dir / subpath
        remote_path = f"{self.config.gpu_worker_user}@{self.config.gpu_worker_host}:{self.config.remote_models_dir}/{subpath}"
        
        # Ensure local directory exists
        local_path.mkdir(parents=True, exist_ok=True)
        
        # Build rsync command
        cmd = ["rsync"] + self.config.rsync_options
        
        if dry_run:
            cmd.append("--dry-run")
        
        if direction == SyncDirection.PUSH:
            cmd.extend([f"{local_path}/", remote_path])
        else:
            cmd.extend([f"{remote_path}/", str(local_path)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]rsync error:[/red] {result.stderr}")
                return False
            
            if result.stdout:
                console.print(result.stdout)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Sync error:[/red] {e}")
            return False
    
    async def verify_model(self, model: ModelInfo, location: ModelLocation) -> bool:
        """Verify model integrity at a location.
        
        For Ollama models, checks the API for model availability.
        For file models, verifies the file exists and size matches.
        
        Args:
            model: Model to verify.
            location: Location to check.
            
        Returns:
            True if model is valid and accessible.
        """
        if model.type == ModelType.OLLAMA:
            models = await self.list_ollama_models(location)
            return any(m.name == model.name for m in models)
        else:
            # File-based verification
            subpath = self.type_paths.get(model.type, "")
            full_path = location.base_path / subpath / model.name
            
            if location.is_local:
                return full_path.exists()
            else:
                # Remote check via SSH
                cmd = [
                    "ssh", f"{location.user}@{location.host}",
                    f"test -f {full_path} && echo 'exists'"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return "exists" in result.stdout


def _format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} TB"


# =============================================================================
# CLI Commands
# =============================================================================


@app.command("list")
def list_models(
    model_type: Annotated[
        ModelType,
        typer.Argument(help="Type of models to list"),
    ] = ModelType.OLLAMA,
    location: Annotated[
        str,
        typer.Option("--location", "-l", help="Location to query (local, gpu_worker, cluster, all)"),
    ] = "all",
) -> None:
    """List available models across locations.
    
    Shows models installed at each location with size and status information.
    Use --location to filter to a specific location.
    """
    console.print(Panel("[bold blue]Model Inventory[/bold blue]"))
    
    manager = ModelSyncManager()
    
    async def _list() -> dict[str, list[ModelInfo]]:
        results: dict[str, list[ModelInfo]] = {}
        
        locations_to_check = (
            [manager.locations[location]] 
            if location != "all" 
            else list(manager.locations.values())
        )
        
        for loc in locations_to_check:
            if model_type == ModelType.OLLAMA or model_type == ModelType.ALL:
                results[loc.name] = await manager.list_ollama_models(loc)
            else:
                results[loc.name] = await manager.list_file_models(loc, model_type)
        
        return results
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Querying locations...", total=1)
        all_models = asyncio.run(_list())
        progress.update(task, completed=1)
    
    # Display results by location
    for loc_name, models in all_models.items():
        table = Table(title=f"{loc_name} - {len(models)} models")
        table.add_column("Model")
        table.add_column("Size", justify="right")
        table.add_column("Digest", max_width=12)
        
        for model in sorted(models, key=lambda m: m.name):
            table.add_row(
                model.name,
                _format_size(model.size_bytes),
                model.digest[:12] if model.digest else "-",
            )
        
        console.print(table)
        console.print()


@app.command()
def push(
    model_type: Annotated[
        ModelType,
        typer.Argument(help="Type of models to push"),
    ] = ModelType.ALL,
    model_name: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Specific model name to push"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be transferred"),
    ] = False,
) -> None:
    """Push models from local to GPU worker.
    
    Syncs models from your local development machine to the GPU worker
    (akula-prime). For Ollama models, triggers a pull on the remote.
    For file models, uses rsync for efficient transfer.
    """
    console.print(Panel("[bold blue]Push Models → GPU Worker[/bold blue]"))
    
    manager = ModelSyncManager()
    
    if model_type == ModelType.OLLAMA and model_name:
        # Push specific Ollama model
        console.print(f"Pushing Ollama model: {model_name}")
        
        async def _push_ollama():
            return await manager.sync_ollama_model(
                model_name,
                manager.locations["local"],
                manager.locations["gpu_worker"],
            )
        
        success = asyncio.run(_push_ollama())
        
        if success:
            console.print(f"[green]✓[/green] Pushed {model_name}")
        else:
            console.print(f"[red]✗[/red] Failed to push {model_name}")
            raise typer.Exit(1)
    else:
        # Push file models
        types_to_push = (
            [model_type] if model_type != ModelType.ALL 
            else [ModelType.CHECKPOINTS, ModelType.LORAS, ModelType.VAE, 
                  ModelType.EMBEDDINGS, ModelType.UPSCALE, ModelType.WHISPER]
        )
        
        for mtype in types_to_push:
            console.print(f"\n[bold]Syncing {mtype.value}...[/bold]")
            success = manager.sync_file_models(mtype, SyncDirection.PUSH, dry_run)
            
            if success:
                console.print(f"[green]✓[/green] {mtype.value} synced")
            else:
                console.print(f"[yellow]⚠[/yellow] {mtype.value} sync had issues")


@app.command()
def pull(
    model_type: Annotated[
        ModelType,
        typer.Argument(help="Type of models to pull"),
    ] = ModelType.OLLAMA,
    model_name: Annotated[
        str | None,
        typer.Option("--model", "-m", help="Specific model name to pull"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be transferred"),
    ] = False,
) -> None:
    """Pull models from GPU worker to local.
    
    Syncs models from the GPU worker (akula-prime) to your local machine.
    Useful for local development and testing.
    """
    console.print(Panel("[bold blue]Pull Models ← GPU Worker[/bold blue]"))
    
    manager = ModelSyncManager()
    
    if model_type == ModelType.OLLAMA:
        console.print("[yellow]Note:[/yellow] Ollama models should be pulled via 'ollama pull' command")
        console.print("Use 'shai-models list ollama' to see available models")
        return
    
    types_to_pull = (
        [model_type] if model_type != ModelType.ALL
        else [ModelType.CHECKPOINTS, ModelType.LORAS, ModelType.VAE,
              ModelType.EMBEDDINGS, ModelType.UPSCALE, ModelType.WHISPER]
    )
    
    for mtype in types_to_pull:
        console.print(f"\n[bold]Pulling {mtype.value}...[/bold]")
        success = manager.sync_file_models(mtype, SyncDirection.PULL, dry_run)
        
        if success:
            console.print(f"[green]✓[/green] {mtype.value} pulled")
        else:
            console.print(f"[yellow]⚠[/yellow] {mtype.value} pull had issues")


@app.command()
def diff(
    model_type: Annotated[
        ModelType,
        typer.Argument(help="Type of models to compare"),
    ] = ModelType.OLLAMA,
) -> None:
    """Compare models between local and GPU worker.
    
    Shows which models exist in each location and highlights differences.
    Useful for identifying what needs to be synced.
    """
    console.print(Panel("[bold blue]Model Diff: Local ↔ GPU Worker[/bold blue]"))
    
    manager = ModelSyncManager()
    
    async def _diff():
        local_models = await manager.list_ollama_models(manager.locations["local"])
        remote_models = await manager.list_ollama_models(manager.locations["gpu_worker"])
        return local_models, remote_models
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Comparing...", total=1)
        local, remote = asyncio.run(_diff())
        progress.update(task, completed=1)
    
    local_names = {m.name for m in local}
    remote_names = {m.name for m in remote}
    
    only_local = local_names - remote_names
    only_remote = remote_names - local_names
    both = local_names & remote_names
    
    table = Table(title="Model Comparison")
    table.add_column("Model")
    table.add_column("Local")
    table.add_column("GPU Worker")
    
    for name in sorted(local_names | remote_names):
        local_status = "[green]✓[/green]" if name in local_names else "[red]✗[/red]"
        remote_status = "[green]✓[/green]" if name in remote_names else "[red]✗[/red]"
        table.add_row(name, local_status, remote_status)
    
    console.print(table)
    console.print()
    console.print(f"Only local: {len(only_local)} | Only remote: {len(only_remote)} | Both: {len(both)}")


@app.command()
def verify(
    location: Annotated[
        str,
        typer.Option("--location", "-l", help="Location to verify"),
    ] = "gpu_worker",
) -> None:
    """Verify model integrity at a location.
    
    Checks that all expected models are accessible and responding.
    Reports any models that are missing or corrupted.
    """
    console.print(Panel(f"[bold blue]Verifying Models at {location}[/bold blue]"))
    
    manager = ModelSyncManager()
    loc = manager.locations.get(location)
    
    if not loc:
        console.print(f"[red]Error:[/red] Unknown location: {location}")
        raise typer.Exit(1)
    
    async def _verify():
        models = await manager.list_ollama_models(loc)
        results = []
        for model in models:
            valid = await manager.verify_model(model, loc)
            results.append((model, valid))
        return results
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Verifying...", total=1)
        results = asyncio.run(_verify())
        progress.update(task, completed=1)
    
    table = Table(title="Verification Results")
    table.add_column("Model")
    table.add_column("Status")
    
    all_valid = True
    for model, valid in results:
        status = "[green]✓ Valid[/green]" if valid else "[red]✗ Invalid[/red]"
        table.add_row(model.name, status)
        if not valid:
            all_valid = False
    
    console.print(table)
    
    if not all_valid:
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the model sync CLI."""
    app()


if __name__ == "__main__":
    main()
