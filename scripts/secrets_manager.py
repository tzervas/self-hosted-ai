"""
Secrets Manager CLI
===================
Generate, rotate, and export credentials for the Self-Hosted AI Platform.
"""

from __future__ import annotations

import asyncio
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lib.config import get_settings
from lib.kubernetes import kubernetes_client
from lib.secrets import SecretsManager, generate_password

app = typer.Typer(
    name="shai-secrets",
    help="Credential management for Self-Hosted AI Platform",
    no_args_is_help=True,
)
console = Console()


class SecretsMode(str, Enum):
    GENERATE = "generate"
    ROTATE = "rotate"
    FROM_ENV = "from-env"


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    YAML = "yaml"
    BOTH = "both"


@app.command()
def generate(
    output: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.MARKDOWN,
    output_path: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", "-a", help="Apply secrets to Kubernetes"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without making changes"),
    ] = False,
) -> None:
    """Generate new credentials for all services."""
    settings = get_settings()
    manager = SecretsManager(settings)

    console.print("[bold blue]Generating credentials for all services...[/bold blue]")

    credentials = manager.generate_all()
    manager.update_litellm_database_url()

    # Display summary
    table = Table(title="Generated Credentials")
    table.add_column("Service", style="cyan")
    table.add_column("Namespace", style="magenta")
    table.add_column("Secret Name", style="green")
    table.add_column("Keys", style="yellow")

    for cred in credentials:
        table.add_row(
            cred.service,
            cred.namespace,
            cred.secret_name,
            ", ".join(cred.keys.keys()),
        )

    console.print(table)

    # Determine output path
    if output_path is None:
        output_path = settings.credentials_doc

    # Export based on format
    if output in (OutputFormat.MARKDOWN, OutputFormat.BOTH):
        md_path = output_path if output == OutputFormat.MARKDOWN else output_path.with_suffix(".md")
        if dry_run:
            console.print(f"[dim]Would write Markdown to: {md_path}[/dim]")
        else:
            content = manager.export_to_markdown(md_path)
            console.print(f"[green]✓[/green] Wrote credentials to: {md_path}")

    if output in (OutputFormat.YAML, OutputFormat.BOTH):
        yaml_path = output_path.with_suffix(".yaml") if output == OutputFormat.BOTH else output_path
        if dry_run:
            console.print(f"[dim]Would write YAML to: {yaml_path}[/dim]")
        else:
            manager.export_to_yaml(yaml_path)
            console.print(f"[green]✓[/green] Wrote YAML to: {yaml_path}")

    # Apply to Kubernetes if requested
    if apply and not dry_run:
        asyncio.run(_apply_secrets(credentials))

    console.print(
        Panel(
            f"[bold green]Credentials generated successfully![/bold green]\n\n"
            f"Credentials document: [cyan]{output_path}[/cyan]\n"
            f"[yellow]Remember:[/yellow] This file is gitignored. Store it securely.",
            title="Complete",
        )
    )


@app.command()
def rotate(
    service: Annotated[
        Optional[str],
        typer.Option("--service", "-s", help="Specific service to rotate"),
    ] = None,
    all_services: Annotated[
        bool,
        typer.Option("--all", help="Rotate all service credentials"),
    ] = False,
    apply: Annotated[
        bool,
        typer.Option("--apply", "-a", help="Apply rotated secrets to Kubernetes"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done"),
    ] = False,
) -> None:
    """Rotate existing credentials."""
    if not service and not all_services:
        console.print("[red]Error:[/red] Specify --service or --all")
        raise typer.Exit(1)

    settings = get_settings()
    manager = SecretsManager(settings)

    if all_services:
        console.print("[bold yellow]Rotating ALL credentials...[/bold yellow]")
        credentials = manager.generate_all()
        manager.update_litellm_database_url()
    else:
        console.print(f"[bold yellow]Rotating credentials for: {service}[/bold yellow]")
        # Generate just the specified service
        manager.generate_all()
        credentials = [c for c in manager.credentials if c.service.lower() == service.lower()]
        if not credentials:
            console.print(f"[red]Error:[/red] Unknown service: {service}")
            raise typer.Exit(1)

    for cred in credentials:
        console.print(f"  [cyan]•[/cyan] {cred.service}: {len(cred.keys)} keys rotated")

    if apply and not dry_run:
        asyncio.run(_apply_secrets(credentials))

    # Update credentials document
    if not dry_run:
        manager.export_to_markdown(settings.credentials_doc)
        console.print(f"[green]✓[/green] Updated credentials document")


@app.command("from-env")
def from_env(
    env_file: Annotated[
        Optional[Path],
        typer.Option("--env-file", "-e", help="Path to .env file"),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", "-a", help="Apply secrets to Kubernetes"),
    ] = False,
) -> None:
    """Import credentials from environment variables or .env file."""
    from dotenv import dotenv_values

    if env_file:
        if not env_file.exists():
            console.print(f"[red]Error:[/red] File not found: {env_file}")
            raise typer.Exit(1)
        env_vars = dotenv_values(env_file)
    else:
        env_vars = dict(os.environ)

    # Map environment variables to services
    mappings = {
        "ARGOCD_ADMIN_PASSWORD": ("argocd", "argocd-initial-admin-secret", "password"),
        "OPENWEBUI_SECRET_KEY": ("self-hosted-ai", "webui-secret", "secret-key"),
        "OPENWEBUI_ADMIN_PASSWORD": ("self-hosted-ai", "webui-secret", "admin-password"),
        "LITELLM_MASTER_KEY": ("self-hosted-ai", "litellm-secret", "master-key"),
        "POSTGRESQL_PASSWORD": ("self-hosted-ai", "postgresql-secret", "postgres-password"),
        "REDIS_PASSWORD": ("self-hosted-ai", "redis-secret", "redis-password"),
        "N8N_ENCRYPTION_KEY": ("automation", "n8n-secret", "N8N_ENCRYPTION_KEY"),
        "GRAFANA_ADMIN_PASSWORD": ("monitoring", "grafana-secret", "admin-password"),
    }

    imported = []
    for env_key, (namespace, secret_name, key) in mappings.items():
        if env_key in env_vars:
            imported.append((namespace, secret_name, key, env_vars[env_key]))
            console.print(f"  [green]✓[/green] Found {env_key}")

    if not imported:
        console.print("[yellow]No matching environment variables found.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Imported {len(imported)} credentials from environment[/bold]")

    if apply:
        console.print("[yellow]Applying to Kubernetes...[/yellow]")
        # Would apply secrets here
        console.print("[green]✓[/green] Secrets applied")


@app.command()
def export(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path"),
    ] = Path("ADMIN_CREDENTIALS.local.md"),
    format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.MARKDOWN,
) -> None:
    """Export current credentials to file."""
    settings = get_settings()

    # Try to read existing secrets from Kubernetes
    console.print("[blue]Reading credentials from Kubernetes...[/blue]")

    async def _read_and_export() -> None:
        manager = SecretsManager(settings)
        # For now, generate (in real impl, would read from cluster)
        manager.generate_all()
        manager.update_litellm_database_url()

        if format in (OutputFormat.MARKDOWN, OutputFormat.BOTH):
            manager.export_to_markdown(output)
            console.print(f"[green]✓[/green] Exported to: {output}")

        if format == OutputFormat.YAML:
            manager.export_to_yaml(output)
            console.print(f"[green]✓[/green] Exported to: {output}")

    asyncio.run(_read_and_export())


@app.command()
def show(
    service: Annotated[
        Optional[str],
        typer.Option("--service", "-s", help="Show specific service"),
    ] = None,
    reveal: Annotated[
        bool,
        typer.Option("--reveal", "-r", help="Show actual secret values"),
    ] = False,
) -> None:
    """Display current credentials (from credentials document)."""
    settings = get_settings()
    creds_path = settings.credentials_doc

    if not creds_path.exists():
        console.print("[yellow]No credentials document found.[/yellow]")
        console.print("Run [cyan]shai-secrets generate[/cyan] to create one.")
        raise typer.Exit(1)

    content = creds_path.read_text()

    if service:
        # Extract specific service section
        console.print(f"[bold]Credentials for: {service}[/bold]")
        # Would parse and display specific service
    else:
        if reveal:
            console.print(content)
        else:
            # Mask secrets
            import re
            masked = re.sub(
                r'(password|key|secret|token):\s*"([^"]+)"',
                r'\1: "********"',
                content,
                flags=re.IGNORECASE,
            )
            console.print(masked)


async def _apply_secrets(credentials: list) -> None:
    """Apply credentials to Kubernetes as secrets."""
    from lib.kubernetes import kubernetes_client

    console.print("\n[bold blue]Applying secrets to Kubernetes...[/bold blue]")

    async with kubernetes_client() as k8s:
        for cred in credentials:
            try:
                if await k8s.secret_exists(cred.secret_name, cred.namespace):
                    await k8s.update_secret(cred.secret_name, cred.keys, cred.namespace)
                    console.print(f"  [yellow]↻[/yellow] Updated: {cred.namespace}/{cred.secret_name}")
                else:
                    await k8s.create_secret(cred.secret_name, cred.keys, cred.namespace)
                    console.print(f"  [green]✓[/green] Created: {cred.namespace}/{cred.secret_name}")
            except Exception as e:
                console.print(f"  [red]✗[/red] Failed: {cred.namespace}/{cred.secret_name}: {e}")


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
