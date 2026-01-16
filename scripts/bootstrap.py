"""
Service Bootstrap System
========================
Configure and initialize all services via their APIs for first-time deployment.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from lib.config import Settings, get_settings
from lib.kubernetes import kubernetes_client
from lib.secrets import SecretsManager
from lib.services import (
    GrafanaClient,
    LiteLLMClient,
    N8NClient,
    OllamaClient,
    OpenWebUIClient,
    SearXNGClient,
)

app = typer.Typer(
    name="shai-bootstrap",
    help="Bootstrap and configure Self-Hosted AI Platform services",
    no_args_is_help=True,
)
console = Console()


@app.command()
def all(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without making changes"),
    ] = False,
    skip_models: Annotated[
        bool,
        typer.Option("--skip-models", help="Skip model pulling"),
    ] = False,
) -> None:
    """Bootstrap all services for first-time deployment."""
    console.print(Panel("[bold blue]Self-Hosted AI Platform - Full Bootstrap[/bold blue]"))

    asyncio.run(_bootstrap_all(dry_run, skip_models))


@app.command()
def services(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without making changes"),
    ] = False,
) -> None:
    """Configure all services via their APIs."""
    console.print("[bold]Configuring services...[/bold]")
    asyncio.run(_bootstrap_services(dry_run))


@app.command()
def models(
    manifest: Annotated[
        Optional[Path],
        typer.Option("--manifest", "-m", help="Models manifest file"),
    ] = None,
    gpu_only: Annotated[
        bool,
        typer.Option("--gpu-only", help="Only pull to GPU worker"),
    ] = False,
) -> None:
    """Pull AI models from manifest."""
    settings = get_settings()
    manifest_path = manifest or settings.models_manifest

    if not manifest_path.exists():
        console.print(f"[red]Error:[/red] Manifest not found: {manifest_path}")
        raise typer.Exit(1)

    asyncio.run(_bootstrap_models(manifest_path, gpu_only))


@app.command()
def openwebui(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without making changes"),
    ] = False,
) -> None:
    """Configure Open WebUI (admin user, Ollama connections, RAG)."""
    asyncio.run(_bootstrap_openwebui(dry_run))


@app.command()
def litellm(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without making changes"),
    ] = False,
) -> None:
    """Configure LiteLLM (model routing, rate limits)."""
    asyncio.run(_bootstrap_litellm(dry_run))


@app.command()
def n8n(
    import_workflows: Annotated[
        bool,
        typer.Option("--import-workflows", help="Import workflows from config/n8n-workflows/"),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without making changes"),
    ] = False,
) -> None:
    """Configure n8n (API key, import workflows)."""
    asyncio.run(_bootstrap_n8n(import_workflows, dry_run))


@app.command()
def grafana(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview without making changes"),
    ] = False,
) -> None:
    """Configure Grafana (datasources, dashboards)."""
    asyncio.run(_bootstrap_grafana(dry_run))


# ============================================
# Implementation Functions
# ============================================


async def _bootstrap_all(dry_run: bool, skip_models: bool) -> None:
    """Run full bootstrap sequence."""
    settings = get_settings()

    steps = [
        ("Generating credentials", _generate_credentials),
        ("Configuring Open WebUI", lambda dr: _bootstrap_openwebui(dr)),
        ("Configuring LiteLLM", lambda dr: _bootstrap_litellm(dr)),
        ("Configuring n8n", lambda dr: _bootstrap_n8n(True, dr)),
        ("Configuring Grafana", lambda dr: _bootstrap_grafana(dr)),
    ]

    if not skip_models:
        steps.append(("Pulling AI models", lambda dr: _bootstrap_models(settings.models_manifest, False)))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for description, func in steps:
            task = progress.add_task(description, total=1)
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(dry_run)
                else:
                    func(dry_run)
                progress.update(task, completed=1)
                console.print(f"  [green]✓[/green] {description}")
            except Exception as e:
                progress.update(task, completed=1)
                console.print(f"  [red]✗[/red] {description}: {e}")

    console.print(Panel("[bold green]Bootstrap complete![/bold green]"))


async def _bootstrap_services(dry_run: bool) -> None:
    """Configure all services."""
    await _bootstrap_openwebui(dry_run)
    await _bootstrap_litellm(dry_run)
    await _bootstrap_n8n(True, dry_run)
    await _bootstrap_grafana(dry_run)


def _generate_credentials(dry_run: bool) -> None:
    """Generate and apply credentials."""
    settings = get_settings()
    manager = SecretsManager(settings)
    manager.generate_all()
    manager.update_litellm_database_url()

    if not dry_run:
        manager.export_to_markdown(settings.credentials_doc)
        console.print(f"    Credentials saved to: {settings.credentials_doc}")


async def _bootstrap_openwebui(dry_run: bool) -> None:
    """Configure Open WebUI."""
    settings = get_settings()

    if dry_run:
        console.print("  [dim]Would configure Open WebUI[/dim]")
        return

    async with OpenWebUIClient(settings) as client:
        # Check health
        health = await client.health_check()
        if health["status"] != "healthy":
            console.print(f"  [yellow]⚠[/yellow] Open WebUI not healthy: {health}")
            return

        # Try to create admin or sign in
        # In production, read credentials from secrets
        admin_email = f"admin@{settings.domain}"
        admin_password = "changeme-on-first-login"  # Would come from secrets

        result = await client.create_admin_user(admin_email, admin_password)
        if result.get("success"):
            console.print("    Created admin user")
        else:
            # Try signing in (user might exist)
            signin = await client.signin(admin_email, admin_password)
            if signin.get("success"):
                console.print("    Signed in as admin")

        # Configure Ollama connections
        ollama_urls = [
            f"http://ollama.self-hosted-ai:11434",
            f"http://ollama-gpu.gpu-workloads:11434",
        ]
        for url in ollama_urls:
            try:
                await client.add_ollama_connection(url)
                console.print(f"    Added Ollama connection: {url}")
            except Exception:
                pass  # May already exist


async def _bootstrap_litellm(dry_run: bool) -> None:
    """Configure LiteLLM."""
    settings = get_settings()

    if dry_run:
        console.print("  [dim]Would configure LiteLLM[/dim]")
        return

    # LiteLLM configuration is primarily via config file
    # API is used for runtime management
    async with LiteLLMClient(settings) as client:
        health = await client.health_check()
        if health["status"] != "healthy":
            console.print(f"  [yellow]⚠[/yellow] LiteLLM not healthy: {health}")
            return

        models = await client.list_models()
        console.print(f"    LiteLLM has {len(models)} models configured")


async def _bootstrap_n8n(import_workflows: bool, dry_run: bool) -> None:
    """Configure n8n."""
    settings = get_settings()

    if dry_run:
        console.print("  [dim]Would configure n8n[/dim]")
        return

    async with N8NClient(settings) as client:
        health = await client.health_check()
        if health["status"] != "healthy":
            console.print(f"  [yellow]⚠[/yellow] n8n not healthy: {health}")
            return

        if import_workflows:
            workflows_dir = settings.config_dir / "n8n-workflows"
            if workflows_dir.exists():
                for workflow_file in workflows_dir.glob("*.json"):
                    try:
                        workflow = json.loads(workflow_file.read_text())
                        await client.import_workflow(workflow)
                        console.print(f"    Imported workflow: {workflow_file.stem}")
                    except Exception as e:
                        console.print(f"    [yellow]⚠[/yellow] Failed to import {workflow_file.stem}: {e}")


async def _bootstrap_grafana(dry_run: bool) -> None:
    """Configure Grafana."""
    settings = get_settings()

    if dry_run:
        console.print("  [dim]Would configure Grafana[/dim]")
        return

    async with GrafanaClient(settings) as client:
        health = await client.health_check()
        if health["status"] != "healthy":
            console.print(f"  [yellow]⚠[/yellow] Grafana not healthy: {health}")
            return

        # Add Prometheus datasource
        prometheus_ds = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": "http://prometheus-server.monitoring:80",
            "access": "proxy",
            "isDefault": True,
        }

        try:
            await client.add_datasource(prometheus_ds)
            console.print("    Added Prometheus datasource")
        except Exception:
            pass  # May already exist


async def _bootstrap_models(manifest_path: Path, gpu_only: bool) -> None:
    """Pull models from manifest."""
    manifest = yaml.safe_load(manifest_path.read_text())
    models = manifest.get("models", [])

    settings = get_settings()

    # Determine targets
    targets = []
    if not gpu_only:
        targets.append(("CPU (cluster)", f"http://ollama.self-hosted-ai:11434"))
    targets.append(("GPU worker", f"http://{settings.gpu_worker_ip}:11434"))

    table = Table(title="Model Pull Status")
    table.add_column("Model")
    table.add_column("Target")
    table.add_column("Status")

    for model_info in models:
        model_name = model_info.get("name")
        if not model_name:
            continue

        for target_name, target_url in targets:
            try:
                async with OllamaClient(target_url) as client:
                    if await client.model_exists(model_name):
                        table.add_row(model_name, target_name, "[green]exists[/green]")
                    else:
                        result = await client.pull_model(model_name)
                        if result.get("success"):
                            table.add_row(model_name, target_name, "[green]pulled[/green]")
                        else:
                            table.add_row(model_name, target_name, "[red]failed[/red]")
            except Exception as e:
                table.add_row(model_name, target_name, f"[red]error: {e}[/red]")

    console.print(table)


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
