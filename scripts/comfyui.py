#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
#     "httpx>=0.27.0",
#     "pyyaml>=6.0.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
ComfyUI Workflow and Model Management for Self-Hosted AI Platform.

This module manages ComfyUI workflows and their model dependencies,
providing tools to list, setup, validate, and export workflows for
image generation tasks.

Why This Script Exists:
    ComfyUI workflows depend on specific models (checkpoints, LoRAs, VAE).
    Each workflow has different model requirements documented in the manifest.
    This script automates:
    - Workflow discovery and documentation
    - Model dependency checking and downloading
    - ComfyUI connectivity validation
    - API-ready workflow export

Architecture:
    - Workflows stored in: config/comfyui-workflows/*.json
    - Manifest at: config/comfyui-workflows/manifest.yml
    - Models on GPU worker: /data/comfyui/models/
    - ComfyUI runs on akula-prime (192.168.1.99:8188)

Workflow Types:
    - txt2img: Text-to-image generation (SDXL, Flux)
    - img2img: Image transformation
    - inpaint: Region-based editing
    - upscale: Super-resolution enhancement

Usage:
    # List available workflows
    uv run scripts/comfyui.py list
    
    # Show workflow details and model requirements
    uv run scripts/comfyui.py info txt2img-sdxl
    
    # Setup workflow (download required models)
    uv run scripts/comfyui.py setup txt2img-sdxl
    
    # Validate ComfyUI connectivity
    uv run scripts/comfyui.py validate

Example:
    >>> from comfyui import ComfyUIManager
    >>> manager = ComfyUIManager()
    >>> workflows = manager.list_workflows()
    >>> manager.setup_workflow("txt2img-sdxl")
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn
from rich.table import Table

app = typer.Typer(
    name="shai-comfyui",
    help="Manage ComfyUI workflows and models",
    no_args_is_help=True,
)
console = Console()


class WorkflowPriority(str, Enum):
    """Priority levels for workflows."""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


@dataclass
class ModelRequirement:
    """A model required by a workflow.
    
    Attributes:
        name: Model filename
        type: Model type (checkpoint, lora, vae, etc.)
        path: Subdirectory within models folder
        url: Download URL (optional)
        size_gb: Approximate size in gigabytes
    """
    name: str
    type: str
    path: str = ""
    url: str | None = None
    size_gb: float = 0


@dataclass
class Workflow:
    """Represents a ComfyUI workflow configuration.
    
    Attributes:
        id: Unique workflow identifier
        name: Human-readable name
        description: What the workflow does
        priority: Installation priority level
        tags: Categorization tags
        vram_min_gb: Minimum VRAM required
        models: Required models
        file: JSON workflow filename
    """
    id: str
    name: str
    description: str = ""
    priority: WorkflowPriority = WorkflowPriority.OPTIONAL
    tags: list[str] = field(default_factory=list)
    vram_min_gb: int = 8
    models: list[ModelRequirement] = field(default_factory=list)
    file: str = ""


@dataclass
class ComfyUIConfig:
    """Configuration for ComfyUI management.
    
    Attributes:
        project_root: Root directory of the project
        workflows_dir: Directory containing workflow files
        manifest_file: Path to manifest.yml
        models_path: Path to ComfyUI models directory
        gpu_worker_host: GPU worker hostname/IP
        comfyui_port: ComfyUI API port
    """
    project_root: Path = field(
        default_factory=lambda: Path(__file__).parent.parent
    )
    workflows_dir: Path = field(default=None)
    manifest_file: Path = field(default=None)
    models_path: Path = field(
        default_factory=lambda: Path(os.environ.get(
            "COMFYUI_MODELS_PATH",
            "/data/comfyui/models"
        ))
    )
    gpu_worker_host: str = field(
        default_factory=lambda: os.environ.get("GPU_WORKER_HOST", "192.168.1.99")
    )
    comfyui_port: int = field(
        default_factory=lambda: int(os.environ.get("COMFYUI_PORT", "8188"))
    )
    
    def __post_init__(self):
        """Initialize derived paths."""
        if self.workflows_dir is None:
            self.workflows_dir = self.project_root / "config" / "comfyui-workflows"
        if self.manifest_file is None:
            self.manifest_file = self.workflows_dir / "manifest.yml"
    
    @property
    def comfyui_url(self) -> str:
        """Get ComfyUI API URL."""
        return f"http://{self.gpu_worker_host}:{self.comfyui_port}"


class ComfyUIManager:
    """Manages ComfyUI workflows and model dependencies.
    
    This class provides methods for workflow discovery, model management,
    and ComfyUI API interaction. It reads workflow configurations from
    the manifest file and handles model downloading.
    
    Why a Manifest File:
        Workflows are JSON files optimized for ComfyUI, not humans.
        The manifest adds human-readable metadata like descriptions,
        tags, and explicit model requirements. This enables automated
        setup and validation.
    
    Attributes:
        config: ComfyUI configuration
    """
    
    def __init__(self, config: ComfyUIConfig | None = None) -> None:
        """Initialize the ComfyUI manager.
        
        Args:
            config: ComfyUI configuration. Uses defaults if None.
        """
        self.config = config or ComfyUIConfig()
        self._manifest_cache: dict | None = None
    
    def _load_manifest(self) -> dict:
        """Load and cache the workflow manifest.
        
        Returns:
            Parsed manifest data.
        """
        if self._manifest_cache is None:
            if not self.config.manifest_file.exists():
                self._manifest_cache = {"workflows": {}}
            else:
                with open(self.config.manifest_file) as f:
                    self._manifest_cache = yaml.safe_load(f) or {"workflows": {}}
        return self._manifest_cache
    
    def list_workflows(self) -> list[Workflow]:
        """List all available workflows.
        
        Returns:
            List of Workflow objects.
        """
        manifest = self._load_manifest()
        workflows = []
        
        for wf_id, data in manifest.get("workflows", {}).items():
            models = []
            for model in data.get("requirements", {}).get("models", []):
                models.append(ModelRequirement(
                    name=model.get("name", ""),
                    type=model.get("type", ""),
                    path=model.get("path", ""),
                    url=model.get("url"),
                    size_gb=model.get("size_gb", 0),
                ))
            
            workflows.append(Workflow(
                id=wf_id,
                name=data.get("name", wf_id),
                description=data.get("description", ""),
                priority=WorkflowPriority(data.get("priority", "optional")),
                tags=data.get("tags", []),
                vram_min_gb=data.get("requirements", {}).get("vram_min_gb", 8),
                models=models,
                file=data.get("file", f"{wf_id}.json"),
            ))
        
        return workflows
    
    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a specific workflow by ID.
        
        Args:
            workflow_id: Unique workflow identifier.
            
        Returns:
            Workflow if found, None otherwise.
        """
        workflows = self.list_workflows()
        return next((w for w in workflows if w.id == workflow_id), None)
    
    def check_model_exists(self, model: ModelRequirement) -> bool:
        """Check if a model file exists on disk.
        
        Args:
            model: Model requirement to check.
            
        Returns:
            True if model file exists.
        """
        full_path = self.config.models_path / model.path / model.name
        return full_path.exists()
    
    async def download_model(
        self,
        model: ModelRequirement,
        progress: Progress | None = None,
    ) -> bool:
        """Download a model file.
        
        Uses httpx for async download with progress tracking.
        Prefers aria2c for faster multi-connection downloads.
        
        Args:
            model: Model to download.
            progress: Rich progress instance for display.
            
        Returns:
            True if download succeeded.
        """
        if not model.url:
            console.print(f"[yellow]No URL for {model.name}[/yellow]")
            return False
        
        dest_dir = self.config.models_path / model.path
        dest_file = dest_dir / model.name
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                async with client.stream("GET", model.url) as response:
                    response.raise_for_status()
                    
                    total = int(response.headers.get("content-length", 0))
                    task = None
                    
                    if progress and total > 0:
                        task = progress.add_task(f"Downloading {model.name}", total=total)
                    
                    with open(dest_file, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
                            if task is not None:
                                progress.update(task, advance=len(chunk))
            
            return True
            
        except Exception as e:
            console.print(f"[red]Download failed:[/red] {e}")
            return False
    
    async def validate_connection(self) -> dict[str, Any]:
        """Validate ComfyUI API connectivity.
        
        Returns:
            Dictionary with validation results.
        """
        results = {
            "api_reachable": False,
            "api_url": self.config.comfyui_url,
            "system_stats": None,
            "models_path_exists": self.config.models_path.exists(),
            "checkpoint_count": 0,
            "upscale_count": 0,
        }
        
        # Check API
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.config.comfyui_url}/system_stats")
                if response.status_code == 200:
                    results["api_reachable"] = True
                    results["system_stats"] = response.json()
        except Exception:
            pass
        
        # Count models
        if self.config.models_path.exists():
            checkpoints = self.config.models_path / "checkpoints"
            if checkpoints.exists():
                results["checkpoint_count"] = len(list(
                    checkpoints.glob("*.safetensors")
                ) + list(checkpoints.glob("*.ckpt")))
            
            upscale = self.config.models_path / "upscale_models"
            if upscale.exists():
                results["upscale_count"] = len(list(upscale.glob("*.pth")))
        
        return results
    
    def export_workflow(self, workflow_id: str) -> dict | None:
        """Export a workflow JSON for API use.
        
        Removes _meta section that's only for human reference.
        
        Args:
            workflow_id: Workflow to export.
            
        Returns:
            Workflow JSON dict, or None if not found.
        """
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return None
        
        workflow_file = self.config.workflows_dir / workflow.file
        if not workflow_file.exists():
            return None
        
        with open(workflow_file) as f:
            data = json.load(f)
        
        # Remove metadata section
        data.pop("_meta", None)
        
        return data


# =============================================================================
# CLI Commands
# =============================================================================


@app.command("list")
def list_workflows() -> None:
    """List all available ComfyUI workflows.
    
    Shows workflow ID, name, priority, and tags for quick reference.
    """
    console.print(Panel("[bold blue]Available ComfyUI Workflows[/bold blue]"))
    
    manager = ComfyUIManager()
    workflows = manager.list_workflows()
    
    if not workflows:
        console.print("[yellow]No workflows found in manifest[/yellow]")
        return
    
    table = Table()
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Priority")
    table.add_column("Tags")
    
    for wf in workflows:
        priority_style = {
            WorkflowPriority.REQUIRED: "[green]required[/green]",
            WorkflowPriority.RECOMMENDED: "[yellow]recommended[/yellow]",
            WorkflowPriority.OPTIONAL: "[dim]optional[/dim]",
        }.get(wf.priority, wf.priority.value)
        
        table.add_row(
            wf.id,
            wf.name,
            priority_style,
            ", ".join(wf.tags),
        )
    
    console.print(table)


@app.command()
def info(
    workflow_id: Annotated[str, typer.Argument(help="Workflow ID to show info for")],
) -> None:
    """Show detailed information about a workflow.
    
    Displays description, requirements, and model dependencies.
    """
    manager = ComfyUIManager()
    workflow = manager.get_workflow(workflow_id)
    
    if not workflow:
        console.print(f"[red]Workflow not found:[/red] {workflow_id}")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]{workflow.name}[/bold]\n\n"
        f"[bold]Description:[/bold] {workflow.description or 'N/A'}\n"
        f"[bold]Priority:[/bold] {workflow.priority.value}\n"
        f"[bold]Tags:[/bold] {', '.join(workflow.tags) or 'None'}\n"
        f"[bold]VRAM Required:[/bold] {workflow.vram_min_gb}GB",
        title=f"Workflow: {workflow_id}",
    ))
    
    if workflow.models:
        console.print("\n[bold]Required Models:[/bold]")
        
        table = Table()
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Size")
        table.add_column("Installed")
        
        for model in workflow.models:
            installed = manager.check_model_exists(model)
            status = "[green]✓[/green]" if installed else "[red]✗[/red]"
            
            table.add_row(
                model.name,
                model.type,
                f"{model.size_gb}GB" if model.size_gb else "?",
                status,
            )
        
        console.print(table)
    else:
        console.print("\n[dim]No specific models required[/dim]")


@app.command()
def setup(
    workflow_id: Annotated[str, typer.Argument(help="Workflow ID to setup")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Re-download existing models"),
    ] = False,
) -> None:
    """Setup a workflow by downloading required models.
    
    Checks for missing models and prompts to download them.
    Use --force to re-download existing models.
    """
    manager = ComfyUIManager()
    workflow = manager.get_workflow(workflow_id)
    
    if not workflow:
        console.print(f"[red]Workflow not found:[/red] {workflow_id}")
        raise typer.Exit(1)
    
    console.print(Panel(f"[bold blue]Setting up: {workflow.name}[/bold blue]"))
    
    if not workflow.models:
        console.print("[green]✓[/green] No models required for this workflow")
        return
    
    for model in workflow.models:
        exists = manager.check_model_exists(model)
        
        if exists and not force:
            console.print(f"[green]✓[/green] Model exists: {model.name}")
            continue
        
        if not model.url:
            console.print(f"[yellow]⚠[/yellow] Model missing (no URL): {model.name}")
            console.print(f"  Expected path: {manager.config.models_path / model.path / model.name}")
            continue
        
        size_info = f" ({model.size_gb}GB)" if model.size_gb else ""
        console.print(f"[yellow]⚠[/yellow] Model missing: {model.name}{size_info}")
        
        if typer.confirm(f"Download {model.name}?"):
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                console=console,
            ) as progress:
                asyncio.run(manager.download_model(model, progress))
        else:
            console.print(f"  [dim]Skipped[/dim]")


@app.command()
def setup_required() -> None:
    """Setup all required workflows.
    
    Automatically sets up workflows marked as priority=required
    in the manifest, downloading any missing models.
    """
    console.print(Panel("[bold blue]Setting up Required Workflows[/bold blue]"))
    
    manager = ComfyUIManager()
    workflows = manager.list_workflows()
    
    required = [w for w in workflows if w.priority == WorkflowPriority.REQUIRED]
    
    if not required:
        console.print("[yellow]No required workflows found in manifest[/yellow]")
        return
    
    for workflow in required:
        console.print(f"\n[bold]Setting up: {workflow.name}[/bold]")
        
        for model in workflow.models:
            if manager.check_model_exists(model):
                console.print(f"[green]✓[/green] {model.name}")
            elif model.url:
                console.print(f"[yellow]Downloading:[/yellow] {model.name}")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    console=console,
                ) as progress:
                    asyncio.run(manager.download_model(model, progress))
            else:
                console.print(f"[red]✗[/red] Missing (no URL): {model.name}")


@app.command()
def validate() -> None:
    """Validate ComfyUI setup and connectivity.
    
    Checks API connectivity, models directory, and counts
    installed models by type.
    """
    console.print(Panel("[bold blue]Validating ComfyUI Setup[/bold blue]"))
    
    manager = ComfyUIManager()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Checking...", total=1)
        results = asyncio.run(manager.validate_connection())
        progress.update(task, completed=1)
    
    # API connectivity
    if results["api_reachable"]:
        console.print(f"[green]✓[/green] ComfyUI API: {results['api_url']}")
    else:
        console.print(f"[red]✗[/red] ComfyUI API not reachable: {results['api_url']}")
    
    # Models directory
    if results["models_path_exists"]:
        console.print(f"[green]✓[/green] Models directory: {manager.config.models_path}")
    else:
        console.print(f"[yellow]⚠[/yellow] Models directory not found: {manager.config.models_path}")
    
    # Model counts
    console.print()
    console.print("[bold]Installed Models:[/bold]")
    console.print(f"  Checkpoints: {results['checkpoint_count']}")
    console.print(f"  Upscale Models: {results['upscale_count']}")
    
    # System stats if available
    if results["system_stats"]:
        stats = results["system_stats"]
        console.print()
        console.print("[bold]System Stats:[/bold]")
        if "devices" in stats:
            for device in stats["devices"]:
                console.print(f"  {device.get('name', 'Unknown')}: "
                            f"{device.get('vram_total', 0) // (1024**3)}GB VRAM")


@app.command()
def export(
    workflow_id: Annotated[str, typer.Argument(help="Workflow ID to export")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file (default: stdout)"),
    ] = None,
) -> None:
    """Export workflow JSON for API use.
    
    Removes metadata sections for clean API consumption.
    Output to file with --output or stdout by default.
    """
    manager = ComfyUIManager()
    data = manager.export_workflow(workflow_id)
    
    if not data:
        console.print(f"[red]Workflow not found:[/red] {workflow_id}")
        raise typer.Exit(1)
    
    output_json = json.dumps(data, indent=2)
    
    if output:
        output.write_text(output_json)
        console.print(f"[green]✓[/green] Exported to: {output}")
    else:
        print(output_json)


def main() -> None:
    """Entry point for the ComfyUI management CLI."""
    app()


if __name__ == "__main__":
    main()
