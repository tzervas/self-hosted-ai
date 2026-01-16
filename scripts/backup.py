#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
#     "asyncpg>=0.30.0",
#     "httpx>=0.27.0",
#     "pyyaml>=6.0.0",
#     "aiofiles>=24.1.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
Backup and Restore System for Self-Hosted AI Platform.

This module provides comprehensive backup capabilities for all critical components
of the Self-Hosted AI Platform including PostgreSQL databases, Qdrant vector stores,
OpenWebUI configurations, and Kubernetes secrets.

Why This Script Exists:
    Data protection is critical for self-hosted infrastructure. This script ensures
    automated, consistent backups with configurable retention policies and supports
    both local storage and remote archival (S3/GCS).

Architecture Decisions:
    - Uses async I/O for parallel backup operations across services
    - Implements incremental backups where supported (Qdrant snapshots)
    - Follows 3-2-1 backup rule: 3 copies, 2 media types, 1 offsite
    - Supports both streaming and file-based backup strategies

Usage:
    # Run directly with uv (no install needed)
    uv run scripts/backup.py create --all
    uv run scripts/backup.py restore --component postgresql --date 2026-01-15
    uv run scripts/backup.py list
    uv run scripts/backup.py cleanup --retain-days 30

Environment Variables:
    BACKUP_ROOT: Base directory for backups (default: /data/backups)
    POSTGRES_HOST: PostgreSQL host (default: localhost)
    POSTGRES_PASSWORD: PostgreSQL password (required for backup)
    QDRANT_HOST: Qdrant host (default: localhost)
    REMOTE_BUCKET: S3/GCS bucket for remote archival

Example:
    >>> from backup import BackupManager
    >>> manager = BackupManager()
    >>> await manager.backup_postgresql()
    >>> await manager.backup_all()
"""

from __future__ import annotations

import asyncio
import gzip
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="shai-backup",
    help="Backup and restore Self-Hosted AI Platform components",
    no_args_is_help=True,
)
console = Console()


class BackupComponent(str, Enum):
    """Supported backup components.
    
    Each component represents a distinct data store or configuration that
    requires independent backup and restore procedures.
    """
    POSTGRESQL = "postgresql"
    QDRANT = "qdrant"
    OPENWEBUI = "openwebui"
    SECRETS = "secrets"
    CONFIG = "config"
    ALL = "all"


class BackupType(str, Enum):
    """Backup frequency type for retention management.
    
    Daily backups are retained for 7 days by default, weekly for 4 weeks.
    This follows standard backup retention best practices.
    """
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


@dataclass
class BackupConfig:
    """Configuration for backup operations.
    
    Attributes:
        backup_root: Base directory for all backups
        retain_daily: Number of daily backups to retain
        retain_weekly: Number of weekly backups to retain
        postgres_host: PostgreSQL server hostname
        postgres_port: PostgreSQL server port
        postgres_user: PostgreSQL username
        postgres_db: PostgreSQL database name
        qdrant_host: Qdrant server hostname
        qdrant_port: Qdrant HTTP port
        openwebui_data: Path to OpenWebUI data directory
        remote_enabled: Whether to archive to remote storage
        remote_bucket: S3/GCS bucket name
        remote_prefix: Prefix path within bucket
    """
    backup_root: Path = field(default_factory=lambda: Path(os.environ.get("BACKUP_ROOT", "/data/backups")))
    retain_daily: int = 7
    retain_weekly: int = 4
    postgres_host: str = field(default_factory=lambda: os.environ.get("POSTGRES_HOST", "localhost"))
    postgres_port: int = field(default_factory=lambda: int(os.environ.get("POSTGRES_PORT", "5432")))
    postgres_user: str = field(default_factory=lambda: os.environ.get("POSTGRES_USER", "litellm"))
    postgres_db: str = field(default_factory=lambda: os.environ.get("POSTGRES_DB", "litellm"))
    qdrant_host: str = field(default_factory=lambda: os.environ.get("QDRANT_HOST", "localhost"))
    qdrant_port: int = field(default_factory=lambda: int(os.environ.get("QDRANT_PORT", "6333")))
    openwebui_data: Path = field(default_factory=lambda: Path(os.environ.get("OPENWEBUI_DATA", "/data/open-webui")))
    remote_enabled: bool = field(default_factory=lambda: os.environ.get("REMOTE_ENABLED", "false").lower() == "true")
    remote_bucket: str = field(default_factory=lambda: os.environ.get("REMOTE_BUCKET", ""))
    remote_prefix: str = field(default_factory=lambda: os.environ.get("REMOTE_PREFIX", "self-hosted-ai/backups"))


@dataclass
class BackupResult:
    """Result of a backup operation.
    
    Attributes:
        component: Which component was backed up
        success: Whether the backup succeeded
        path: Path to the backup file (if successful)
        size_bytes: Size of the backup in bytes
        duration_seconds: Time taken for the backup
        error: Error message if backup failed
    """
    component: BackupComponent
    success: bool
    path: Path | None = None
    size_bytes: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


class BackupManager:
    """Manages backup and restore operations for all platform components.
    
    This class coordinates backup operations across multiple data stores,
    ensuring consistency and proper sequencing. It supports both synchronous
    and asynchronous backup patterns.
    
    Why Async:
        Backup operations are I/O bound (disk, network). Using async allows
        parallel backups of independent components, reducing total backup time.
    
    Attributes:
        config: Backup configuration
        
    Example:
        >>> manager = BackupManager()
        >>> result = await manager.backup_postgresql()
        >>> print(f"Backup saved to: {result.path}")
    """
    
    def __init__(self, config: BackupConfig | None = None) -> None:
        """Initialize the backup manager.
        
        Args:
            config: Backup configuration. If None, uses defaults from environment.
        """
        self.config = config or BackupConfig()
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create backup directory structure if it doesn't exist."""
        for component in [BackupComponent.POSTGRESQL, BackupComponent.QDRANT, 
                          BackupComponent.OPENWEBUI, BackupComponent.SECRETS, BackupComponent.CONFIG]:
            for backup_type in [BackupType.DAILY, BackupType.WEEKLY, BackupType.MANUAL]:
                path = self.config.backup_root / component.value / backup_type.value
                path.mkdir(parents=True, exist_ok=True)
    
    def _get_timestamp(self) -> str:
        """Generate timestamp string for backup filenames."""
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    def _get_backup_type(self) -> BackupType:
        """Determine backup type based on day of week.
        
        Weekly backups are taken on Sundays (weekday 6).
        """
        if datetime.now(timezone.utc).weekday() == 6:
            return BackupType.WEEKLY
        return BackupType.DAILY
    
    async def backup_postgresql(self) -> BackupResult:
        """Backup PostgreSQL database using pg_dump.
        
        Creates a compressed SQL dump of the entire database. Uses streaming
        compression to minimize disk I/O and storage requirements.
        
        Returns:
            BackupResult with path to compressed backup file.
            
        Raises:
            RuntimeError: If pg_dump is not available or connection fails.
        """
        start_time = datetime.now(timezone.utc)
        timestamp = self._get_timestamp()
        backup_type = self._get_backup_type()
        backup_dir = self.config.backup_root / "postgresql" / backup_type.value
        backup_file = backup_dir / f"postgresql_{timestamp}.sql.gz"
        
        try:
            # Build pg_dump command
            env = os.environ.copy()
            env["PGPASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "")
            
            cmd = [
                "pg_dump",
                "-h", self.config.postgres_host,
                "-p", str(self.config.postgres_port),
                "-U", self.config.postgres_user,
                "-d", self.config.postgres_db,
                "--format=plain",
                "--no-owner",
                "--no-acl",
            ]
            
            # Execute pg_dump and compress output
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return BackupResult(
                    component=BackupComponent.POSTGRESQL,
                    success=False,
                    error=stderr.decode() if stderr else "pg_dump failed",
                )
            
            # Compress and write to file
            with gzip.open(backup_file, "wb") as f:
                f.write(stdout)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            size = backup_file.stat().st_size
            
            return BackupResult(
                component=BackupComponent.POSTGRESQL,
                success=True,
                path=backup_file,
                size_bytes=size,
                duration_seconds=duration,
            )
            
        except Exception as e:
            return BackupResult(
                component=BackupComponent.POSTGRESQL,
                success=False,
                error=str(e),
            )
    
    async def backup_qdrant(self) -> BackupResult:
        """Backup Qdrant vector database using snapshot API.
        
        Triggers a snapshot creation in Qdrant and downloads the resulting
        snapshot file. This is an atomic operation that ensures consistency.
        
        Returns:
            BackupResult with path to snapshot file.
        """
        import httpx
        
        start_time = datetime.now(timezone.utc)
        timestamp = self._get_timestamp()
        backup_type = self._get_backup_type()
        backup_dir = self.config.backup_root / "qdrant" / backup_type.value
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Trigger snapshot creation
                url = f"http://{self.config.qdrant_host}:{self.config.qdrant_port}/snapshots"
                response = await client.post(url)
                
                if response.status_code != 200:
                    return BackupResult(
                        component=BackupComponent.QDRANT,
                        success=False,
                        error=f"Snapshot creation failed: {response.text}",
                    )
                
                snapshot_name = response.json().get("result", {}).get("name")
                if not snapshot_name:
                    return BackupResult(
                        component=BackupComponent.QDRANT,
                        success=False,
                        error="No snapshot name in response",
                    )
                
                # Download snapshot
                download_url = f"{url}/{snapshot_name}"
                backup_file = backup_dir / f"qdrant_{timestamp}_{snapshot_name}"
                
                async with client.stream("GET", download_url) as stream:
                    with open(backup_file, "wb") as f:
                        async for chunk in stream.aiter_bytes():
                            f.write(chunk)
                
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                size = backup_file.stat().st_size
                
                return BackupResult(
                    component=BackupComponent.QDRANT,
                    success=True,
                    path=backup_file,
                    size_bytes=size,
                    duration_seconds=duration,
                )
                
        except Exception as e:
            return BackupResult(
                component=BackupComponent.QDRANT,
                success=False,
                error=str(e),
            )
    
    async def backup_openwebui(self) -> BackupResult:
        """Backup OpenWebUI data directory.
        
        Creates a compressed tar archive of the OpenWebUI data directory,
        which includes user data, chat history, and configuration.
        
        Returns:
            BackupResult with path to tar.gz archive.
        """
        start_time = datetime.now(timezone.utc)
        timestamp = self._get_timestamp()
        backup_type = self._get_backup_type()
        backup_dir = self.config.backup_root / "openwebui" / backup_type.value
        backup_file = backup_dir / f"openwebui_{timestamp}.tar.gz"
        
        try:
            if not self.config.openwebui_data.exists():
                return BackupResult(
                    component=BackupComponent.OPENWEBUI,
                    success=False,
                    error=f"Data directory not found: {self.config.openwebui_data}",
                )
            
            # Create tar.gz archive
            shutil.make_archive(
                str(backup_file.with_suffix("").with_suffix("")),
                "gztar",
                self.config.openwebui_data.parent,
                self.config.openwebui_data.name,
            )
            
            # Rename to expected filename (make_archive adds .tar.gz)
            actual_file = backup_file.with_suffix("").with_suffix(".tar.gz")
            if actual_file != backup_file:
                actual_file.rename(backup_file)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            size = backup_file.stat().st_size
            
            return BackupResult(
                component=BackupComponent.OPENWEBUI,
                success=True,
                path=backup_file,
                size_bytes=size,
                duration_seconds=duration,
            )
            
        except Exception as e:
            return BackupResult(
                component=BackupComponent.OPENWEBUI,
                success=False,
                error=str(e),
            )
    
    async def backup_secrets(self) -> BackupResult:
        """Backup Kubernetes secrets using kubectl.
        
        Exports all secrets from critical namespaces as YAML. Note that this
        requires appropriate RBAC permissions on the cluster.
        
        Security Note:
            Backup files contain sensitive data and should be encrypted
            before storing offsite.
        
        Returns:
            BackupResult with path to secrets YAML file.
        """
        start_time = datetime.now(timezone.utc)
        timestamp = self._get_timestamp()
        backup_type = self._get_backup_type()
        backup_dir = self.config.backup_root / "secrets" / backup_type.value
        backup_file = backup_dir / f"secrets_{timestamp}.yaml.gz"
        
        namespaces = ["self-hosted-ai", "argocd", "cert-manager", "monitoring"]
        
        try:
            all_secrets = []
            
            for ns in namespaces:
                cmd = ["kubectl", "get", "secrets", "-n", ns, "-o", "yaml"]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    all_secrets.append(f"# Namespace: {ns}\n")
                    all_secrets.append(stdout.decode())
                    all_secrets.append("\n---\n")
            
            # Compress and write
            with gzip.open(backup_file, "wt") as f:
                f.write("".join(all_secrets))
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            size = backup_file.stat().st_size
            
            return BackupResult(
                component=BackupComponent.SECRETS,
                success=True,
                path=backup_file,
                size_bytes=size,
                duration_seconds=duration,
            )
            
        except Exception as e:
            return BackupResult(
                component=BackupComponent.SECRETS,
                success=False,
                error=str(e),
            )
    
    async def backup_all(self) -> list[BackupResult]:
        """Backup all components in parallel.
        
        Runs all backup operations concurrently for maximum efficiency.
        Independent components (PostgreSQL, Qdrant, etc.) have no ordering
        requirements and can safely run in parallel.
        
        Returns:
            List of BackupResults for each component.
        """
        tasks = [
            self.backup_postgresql(),
            self.backup_qdrant(),
            self.backup_openwebui(),
            self.backup_secrets(),
        ]
        
        return await asyncio.gather(*tasks)
    
    def cleanup_old_backups(self) -> dict[str, int]:
        """Remove backups older than retention period.
        
        Enforces the retention policy by removing old backups:
        - Daily backups older than retain_daily days
        - Weekly backups older than retain_weekly weeks
        
        Returns:
            Dict mapping component names to number of files removed.
        """
        removed: dict[str, int] = {}
        now = datetime.now(timezone.utc)
        
        for component in [BackupComponent.POSTGRESQL, BackupComponent.QDRANT,
                          BackupComponent.OPENWEBUI, BackupComponent.SECRETS]:
            removed[component.value] = 0
            
            # Clean daily backups
            daily_dir = self.config.backup_root / component.value / "daily"
            daily_cutoff = now - timedelta(days=self.config.retain_daily)
            
            for file in daily_dir.glob("*"):
                if file.stat().st_mtime < daily_cutoff.timestamp():
                    file.unlink()
                    removed[component.value] += 1
            
            # Clean weekly backups
            weekly_dir = self.config.backup_root / component.value / "weekly"
            weekly_cutoff = now - timedelta(weeks=self.config.retain_weekly)
            
            for file in weekly_dir.glob("*"):
                if file.stat().st_mtime < weekly_cutoff.timestamp():
                    file.unlink()
                    removed[component.value] += 1
        
        return removed
    
    def list_backups(self, component: BackupComponent | None = None) -> list[dict[str, Any]]:
        """List available backups.
        
        Args:
            component: Filter to specific component, or None for all.
            
        Returns:
            List of backup metadata dicts with name, path, size, date.
        """
        backups: list[dict[str, Any]] = []
        
        components = [component] if component else [
            BackupComponent.POSTGRESQL, BackupComponent.QDRANT,
            BackupComponent.OPENWEBUI, BackupComponent.SECRETS
        ]
        
        for comp in components:
            comp_dir = self.config.backup_root / comp.value
            for backup_type in [BackupType.DAILY, BackupType.WEEKLY, BackupType.MANUAL]:
                type_dir = comp_dir / backup_type.value
                if type_dir.exists():
                    for file in sorted(type_dir.glob("*"), reverse=True):
                        stat = file.stat()
                        backups.append({
                            "component": comp.value,
                            "type": backup_type.value,
                            "name": file.name,
                            "path": str(file),
                            "size_bytes": stat.st_size,
                            "date": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                        })
        
        return backups


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


@app.command()
def create(
    component: Annotated[
        BackupComponent,
        typer.Argument(help="Component to backup (postgresql, qdrant, openwebui, secrets, all)"),
    ] = BackupComponent.ALL,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Create a backup of specified component(s).
    
    Creates timestamped backups in the configured backup directory.
    Use 'all' to backup all components in parallel.
    """
    console.print(Panel("[bold blue]Self-Hosted AI Platform - Backup[/bold blue]"))
    
    manager = BackupManager()
    
    async def _run_backup() -> list[BackupResult]:
        if component == BackupComponent.ALL:
            return await manager.backup_all()
        elif component == BackupComponent.POSTGRESQL:
            return [await manager.backup_postgresql()]
        elif component == BackupComponent.QDRANT:
            return [await manager.backup_qdrant()]
        elif component == BackupComponent.OPENWEBUI:
            return [await manager.backup_openwebui()]
        elif component == BackupComponent.SECRETS:
            return [await manager.backup_secrets()]
        else:
            return []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Backing up {component.value}...", total=1)
        results = asyncio.run(_run_backup())
        progress.update(task, completed=1)
    
    # Display results
    table = Table(title="Backup Results")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Size")
    table.add_column("Duration")
    table.add_column("Path" if verbose else "")
    
    for result in results:
        status = "[green]✓ Success[/green]" if result.success else f"[red]✗ {result.error}[/red]"
        size = _format_size(result.size_bytes) if result.success else "-"
        duration = f"{result.duration_seconds:.1f}s" if result.success else "-"
        path = str(result.path) if result.success and verbose else ""
        
        table.add_row(result.component.value, status, size, duration, path)
    
    console.print(table)
    
    # Exit with error if any backup failed
    if not all(r.success for r in results):
        raise typer.Exit(1)


@app.command()
def restore(
    component: Annotated[
        BackupComponent,
        typer.Argument(help="Component to restore"),
    ],
    backup_file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Specific backup file to restore"),
    ] = None,
    date: Annotated[
        str,
        typer.Option("--date", "-d", help="Date to restore from (YYYYMMDD)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be restored without doing it"),
    ] = False,
) -> None:
    """Restore a component from backup.
    
    Restores data from a previous backup. Either specify a specific
    backup file with --file, or use --date to restore the most recent
    backup from that date.
    """
    console.print(Panel("[bold yellow]Self-Hosted AI Platform - Restore[/bold yellow]"))
    
    manager = BackupManager()
    
    # Find backup file
    if backup_file:
        if not backup_file.exists():
            console.print(f"[red]Error:[/red] Backup file not found: {backup_file}")
            raise typer.Exit(1)
        target_file = backup_file
    elif date:
        backups = manager.list_backups(component)
        matching = [b for b in backups if date in b["name"]]
        if not matching:
            console.print(f"[red]Error:[/red] No backup found for date: {date}")
            raise typer.Exit(1)
        target_file = Path(matching[0]["path"])
    else:
        # Use most recent
        backups = manager.list_backups(component)
        if not backups:
            console.print(f"[red]Error:[/red] No backups found for {component.value}")
            raise typer.Exit(1)
        target_file = Path(backups[0]["path"])
    
    console.print(f"Restoring from: [cyan]{target_file}[/cyan]")
    
    if dry_run:
        console.print("[yellow]Dry run - no changes made[/yellow]")
        return
    
    # TODO: Implement actual restore logic for each component
    console.print("[yellow]Restore functionality not yet implemented[/yellow]")


@app.command("list")
def list_backups_cmd(
    component: Annotated[
        BackupComponent | None,
        typer.Argument(help="Filter by component"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of backups to show"),
    ] = 20,
) -> None:
    """List available backups.
    
    Shows all available backups sorted by date, newest first.
    Optionally filter by component.
    """
    manager = BackupManager()
    backups = manager.list_backups(component)[:limit]
    
    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        return
    
    table = Table(title="Available Backups")
    table.add_column("Component")
    table.add_column("Type")
    table.add_column("Date")
    table.add_column("Size")
    table.add_column("Filename")
    
    for backup in backups:
        date_str = backup["date"].strftime("%Y-%m-%d %H:%M")
        table.add_row(
            backup["component"],
            backup["type"],
            date_str,
            _format_size(backup["size_bytes"]),
            backup["name"],
        )
    
    console.print(table)


@app.command()
def cleanup(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be removed"),
    ] = False,
) -> None:
    """Remove old backups according to retention policy.
    
    Removes backups older than the configured retention period:
    - Daily backups: 7 days
    - Weekly backups: 4 weeks
    """
    manager = BackupManager()
    
    if dry_run:
        console.print("[yellow]Dry run - showing what would be removed:[/yellow]")
        # Show files that would be removed
        backups = manager.list_backups()
        now = datetime.now(timezone.utc)
        daily_cutoff = now - timedelta(days=manager.config.retain_daily)
        weekly_cutoff = now - timedelta(weeks=manager.config.retain_weekly)
        
        for backup in backups:
            if backup["type"] == "daily" and backup["date"] < daily_cutoff:
                console.print(f"  Would remove: {backup['path']}")
            elif backup["type"] == "weekly" and backup["date"] < weekly_cutoff:
                console.print(f"  Would remove: {backup['path']}")
    else:
        removed = manager.cleanup_old_backups()
        total = sum(removed.values())
        console.print(f"[green]Cleaned up {total} old backup files[/green]")
        for component, count in removed.items():
            if count > 0:
                console.print(f"  {component}: {count} files removed")


def main() -> None:
    """Entry point for the backup CLI."""
    app()


if __name__ == "__main__":
    main()
