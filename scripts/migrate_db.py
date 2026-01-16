#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
#     "asyncpg>=0.29.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
PostgreSQL Database Migration for Self-Hosted AI Platform.

This module handles database migrations, including major version upgrades
(e.g., PostgreSQL 16 → 17) using a zero-downtime parallel deployment strategy.

Why This Script Exists:
    PostgreSQL major version upgrades require careful handling to avoid
    data loss and minimize downtime. This script automates:
    - Pre-migration backup creation
    - Data migration via pg_dump/restore
    - Verification of migrated data
    - Guidance for configuration updates

Migration Strategy:
    Zero-downtime parallel deployment:
    1. Run both old and new PostgreSQL versions simultaneously
    2. Export from old, import to new
    3. Verify data integrity
    4. Update application configuration
    5. Decommission old instance after verification period

Architecture:
    - PostgreSQL 16: Source (postgres-db container)
    - PostgreSQL 17: Target (postgres-17-db container)
    - LiteLLM: Primary consumer of database
    - Backup storage: /data/postgres-migration

Usage:
    # Check migration prerequisites
    uv run scripts/migrate_db.py check
    
    # Run full migration
    uv run scripts/migrate_db.py migrate
    
    # Backup only
    uv run scripts/migrate_db.py backup
    
    # Verify migration
    uv run scripts/migrate_db.py verify

Example:
    >>> from migrate_db import DatabaseMigration
    >>> migration = DatabaseMigration()
    >>> await migration.check_prerequisites()
    >>> await migration.create_backup()
    >>> await migration.migrate_data()
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="shai-migrate",
    help="PostgreSQL database migration tools",
    no_args_is_help=True,
)
console = Console()


@dataclass
class MigrationConfig:
    """Configuration for database migration.
    
    Attributes:
        pg16_host: PostgreSQL 16 hostname
        pg16_port: PostgreSQL 16 port
        pg17_host: PostgreSQL 17 hostname
        pg17_port: PostgreSQL 17 port
        database: Database name to migrate
        user: PostgreSQL username
        password: PostgreSQL password
        backup_dir: Directory for migration backups
        pg16_container: Docker container name for PG16
        pg17_container: Docker container name for PG17
    """
    pg16_host: str = field(
        default_factory=lambda: os.environ.get("POSTGRES_16_HOST", "localhost")
    )
    pg16_port: int = field(
        default_factory=lambda: int(os.environ.get("POSTGRES_16_PORT", "5432"))
    )
    pg17_host: str = field(
        default_factory=lambda: os.environ.get("POSTGRES_17_HOST", "localhost")
    )
    pg17_port: int = field(
        default_factory=lambda: int(os.environ.get("POSTGRES_17_PORT", "5433"))
    )
    database: str = field(
        default_factory=lambda: os.environ.get("POSTGRES_DB", "litellm")
    )
    user: str = field(
        default_factory=lambda: os.environ.get("POSTGRES_USER", "litellm")
    )
    password: str = field(
        default_factory=lambda: os.environ.get("POSTGRES_PASSWORD", "")
    )
    backup_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("DATA_PATH", "/data")) / "postgres-migration"
    )
    pg16_container: str = "postgres-db"
    pg17_container: str = "postgres-17-db"


@dataclass
class MigrationResult:
    """Result of a migration operation.
    
    Attributes:
        success: Whether the operation succeeded
        message: Status message
        details: Additional details (row counts, etc.)
    """
    success: bool
    message: str
    details: dict = field(default_factory=dict)


class DatabaseMigration:
    """Manages PostgreSQL database migrations.
    
    This class handles the full migration lifecycle including backups,
    data transfer, and verification. It uses Docker exec to run pg_dump
    and psql commands in the respective containers.
    
    Why Docker Exec:
        The PostgreSQL instances run in Docker containers. Using docker exec
        ensures we use the correct client versions and have direct access
        to the database without network configuration complexity.
    
    Attributes:
        config: Migration configuration
        timestamp: Timestamp for backup naming
    """
    
    def __init__(self, config: MigrationConfig | None = None) -> None:
        """Initialize the migration manager.
        
        Args:
            config: Migration configuration. Uses defaults if None.
        """
        self.config = config or MigrationConfig()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _run_docker(
        self,
        container: str,
        cmd: list[str],
        input_data: str | None = None,
    ) -> subprocess.CompletedProcess:
        """Run a command in a Docker container.
        
        Args:
            container: Container name.
            cmd: Command and arguments.
            input_data: Optional stdin data.
            
        Returns:
            Completed process result.
        """
        docker_cmd = ["docker", "exec"]
        if input_data:
            docker_cmd.append("-i")
        docker_cmd.extend([container] + cmd)
        
        return subprocess.run(
            docker_cmd,
            input=input_data,
            capture_output=True,
            text=True,
        )
    
    def check_container_running(self, container: str) -> bool:
        """Check if a Docker container is running.
        
        Args:
            container: Container name to check.
            
        Returns:
            True if container is running.
        """
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        return container in result.stdout
    
    def check_postgres_ready(self, container: str) -> bool:
        """Check if PostgreSQL is accepting connections.
        
        Args:
            container: Container to check.
            
        Returns:
            True if PostgreSQL is ready.
        """
        result = self._run_docker(
            container,
            ["pg_isready", "-U", self.config.user],
        )
        return result.returncode == 0
    
    def check_prerequisites(self) -> list[MigrationResult]:
        """Check all prerequisites for migration.
        
        Returns:
            List of check results.
        """
        checks = []
        
        # Check PG16 container
        if self.check_container_running(self.config.pg16_container):
            checks.append(MigrationResult(
                success=True,
                message=f"PostgreSQL 16 container ({self.config.pg16_container}) running",
            ))
        else:
            checks.append(MigrationResult(
                success=False,
                message=f"PostgreSQL 16 container ({self.config.pg16_container}) not running",
            ))
        
        # Check PG17 container
        if self.check_container_running(self.config.pg17_container):
            checks.append(MigrationResult(
                success=True,
                message=f"PostgreSQL 17 container ({self.config.pg17_container}) running",
            ))
        else:
            checks.append(MigrationResult(
                success=False,
                message=f"PostgreSQL 17 container ({self.config.pg17_container}) not running",
                details={"hint": "Start with: docker compose --profile postgres-migration up -d postgres-17"},
            ))
        
        # Check PG16 ready
        if checks[0].success and self.check_postgres_ready(self.config.pg16_container):
            checks.append(MigrationResult(
                success=True,
                message="PostgreSQL 16 accepting connections",
            ))
        elif checks[0].success:
            checks.append(MigrationResult(
                success=False,
                message="PostgreSQL 16 not accepting connections",
            ))
        
        # Check PG17 ready
        if checks[1].success and self.check_postgres_ready(self.config.pg17_container):
            checks.append(MigrationResult(
                success=True,
                message="PostgreSQL 17 accepting connections",
            ))
        elif checks[1].success:
            checks.append(MigrationResult(
                success=False,
                message="PostgreSQL 17 not accepting connections",
            ))
        
        # Check password configured
        if self.config.password:
            checks.append(MigrationResult(
                success=True,
                message="Database password configured",
            ))
        else:
            checks.append(MigrationResult(
                success=False,
                message="POSTGRES_PASSWORD not set",
            ))
        
        return checks
    
    def create_backup(self) -> MigrationResult:
        """Create backup of PostgreSQL 16 database.
        
        Creates both a full database dump and globals dump.
        
        Returns:
            Result with backup file paths.
        """
        # Ensure backup directory exists
        self.config.backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = self.config.backup_dir / f"pg16_backup_{self.timestamp}.sql"
        globals_file = self.config.backup_dir / f"pg16_globals_{self.timestamp}.sql"
        
        # Full database dump
        result = self._run_docker(
            self.config.pg16_container,
            ["pg_dump", "-U", self.config.user, "-d", self.config.database],
        )
        
        if result.returncode != 0:
            return MigrationResult(
                success=False,
                message=f"pg_dump failed: {result.stderr}",
            )
        
        backup_file.write_text(result.stdout)
        
        # Globals dump
        result = self._run_docker(
            self.config.pg16_container,
            ["pg_dumpall", "-U", self.config.user, "--globals-only"],
        )
        
        globals_file.write_text(result.stdout)
        
        return MigrationResult(
            success=True,
            message="Backup created successfully",
            details={
                "backup_file": str(backup_file),
                "globals_file": str(globals_file),
                "size": backup_file.stat().st_size,
            },
        )
    
    def migrate_data(self) -> MigrationResult:
        """Migrate data from PostgreSQL 16 to 17.
        
        This method:
        1. Imports globals (roles, tablespaces)
        2. Drops and recreates target database
        3. Imports data dump
        
        Returns:
            Migration result.
        """
        backup_file = self.config.backup_dir / f"pg16_backup_{self.timestamp}.sql"
        globals_file = self.config.backup_dir / f"pg16_globals_{self.timestamp}.sql"
        
        if not backup_file.exists():
            return MigrationResult(
                success=False,
                message="Backup file not found. Run backup first.",
            )
        
        # Import globals
        globals_sql = globals_file.read_text() if globals_file.exists() else ""
        if globals_sql:
            self._run_docker(
                self.config.pg17_container,
                ["psql", "-U", self.config.user, "-d", "postgres"],
                input_data=globals_sql,
            )
        
        # Drop and recreate database
        self._run_docker(
            self.config.pg17_container,
            ["psql", "-U", self.config.user, "-d", "postgres", "-c",
             f"DROP DATABASE IF EXISTS {self.config.database};"],
        )
        
        self._run_docker(
            self.config.pg17_container,
            ["psql", "-U", self.config.user, "-d", "postgres", "-c",
             f"CREATE DATABASE {self.config.database} OWNER {self.config.user};"],
        )
        
        # Import data
        backup_sql = backup_file.read_text()
        result = self._run_docker(
            self.config.pg17_container,
            ["psql", "-U", self.config.user, "-d", self.config.database],
            input_data=backup_sql,
        )
        
        if result.returncode != 0:
            return MigrationResult(
                success=False,
                message=f"Data import failed: {result.stderr}",
            )
        
        return MigrationResult(
            success=True,
            message="Data migration completed",
        )
    
    def verify_migration(self) -> MigrationResult:
        """Verify data integrity after migration.
        
        Compares table counts between source and target databases.
        
        Returns:
            Verification result with comparison data.
        """
        # Get PG16 table count
        result16 = self._run_docker(
            self.config.pg16_container,
            ["psql", "-U", self.config.user, "-d", self.config.database, "-t", "-c",
             "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"],
        )
        pg16_count = int(result16.stdout.strip()) if result16.returncode == 0 else -1
        
        # Get PG17 table count
        result17 = self._run_docker(
            self.config.pg17_container,
            ["psql", "-U", self.config.user, "-d", self.config.database, "-t", "-c",
             "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"],
        )
        pg17_count = int(result17.stdout.strip()) if result17.returncode == 0 else -1
        
        # Get PG17 version
        version_result = self._run_docker(
            self.config.pg17_container,
            ["psql", "-U", self.config.user, "-d", self.config.database, "-t", "-c",
             "SELECT version();"],
        )
        pg17_version = version_result.stdout.strip() if version_result.returncode == 0 else "Unknown"
        
        matches = pg16_count == pg17_count and pg16_count >= 0
        
        return MigrationResult(
            success=matches,
            message="Table counts match" if matches else "Table counts mismatch - manual verification needed",
            details={
                "pg16_tables": pg16_count,
                "pg17_tables": pg17_count,
                "pg17_version": pg17_version,
            },
        )


# =============================================================================
# CLI Commands
# =============================================================================


@app.command()
def check() -> None:
    """Check migration prerequisites.
    
    Validates that both PostgreSQL instances are running and accessible.
    """
    console.print(Panel("[bold blue]Migration Prerequisites Check[/bold blue]"))
    
    migration = DatabaseMigration()
    results = migration.check_prerequisites()
    
    table = Table()
    table.add_column("Check")
    table.add_column("Status")
    
    all_passed = True
    for result in results:
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        if not result.success:
            all_passed = False
        table.add_row(result.message, status)
        
        if result.details.get("hint"):
            console.print(f"  [dim]Hint: {result.details['hint']}[/dim]")
    
    console.print(table)
    
    if not all_passed:
        console.print("\n[red]Some prerequisites not met. Fix issues before migrating.[/red]")
        raise typer.Exit(1)
    else:
        console.print("\n[green]All prerequisites met - ready to migrate![/green]")


@app.command()
def backup() -> None:
    """Create backup of source database.
    
    Creates a full pg_dump of the PostgreSQL 16 database.
    """
    console.print(Panel("[bold blue]Creating Database Backup[/bold blue]"))
    
    migration = DatabaseMigration()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Dumping database...", total=1)
        result = migration.create_backup()
        progress.update(task, completed=1)
    
    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
        console.print(f"  File: {result.details['backup_file']}")
        size_mb = result.details['size'] / (1024 * 1024)
        console.print(f"  Size: {size_mb:.1f} MB")
    else:
        console.print(f"[red]✗[/red] {result.message}")
        raise typer.Exit(1)


@app.command()
def migrate(
    skip_backup: Annotated[
        bool,
        typer.Option("--skip-backup", help="Skip backup (use existing)"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Run full database migration.
    
    Performs backup, data migration, and verification in sequence.
    """
    console.print(Panel(
        "[bold blue]PostgreSQL 16 → 17 Migration[/bold blue]\n"
        "[dim]Zero-downtime parallel deployment strategy[/dim]",
    ))
    
    migration = DatabaseMigration()
    
    # Check prerequisites
    console.print("\n[bold]Phase 1: Prerequisites[/bold]")
    results = migration.check_prerequisites()
    
    failed = [r for r in results if not r.success]
    if failed:
        for r in failed:
            console.print(f"[red]✗[/red] {r.message}")
        raise typer.Exit(1)
    
    console.print("[green]✓[/green] All prerequisites met")
    
    # Confirmation
    if not yes:
        if not typer.confirm("\nStart migration?"):
            console.print("[yellow]Migration cancelled[/yellow]")
            raise typer.Exit(0)
    
    # Backup
    if not skip_backup:
        console.print("\n[bold]Phase 2: Backup[/bold]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating backup...", total=1)
            result = migration.create_backup()
            progress.update(task, completed=1)
        
        if result.success:
            console.print(f"[green]✓[/green] Backup: {result.details['backup_file']}")
        else:
            console.print(f"[red]✗[/red] Backup failed: {result.message}")
            raise typer.Exit(1)
    
    # Migrate
    console.print("\n[bold]Phase 3: Data Migration[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Migrating data...", total=1)
        result = migration.migrate_data()
        progress.update(task, completed=1)
    
    if result.success:
        console.print("[green]✓[/green] Data migration complete")
    else:
        console.print(f"[red]✗[/red] Migration failed: {result.message}")
        raise typer.Exit(1)
    
    # Verify
    console.print("\n[bold]Phase 4: Verification[/bold]")
    result = migration.verify_migration()
    
    console.print(f"  PostgreSQL 16 tables: {result.details['pg16_tables']}")
    console.print(f"  PostgreSQL 17 tables: {result.details['pg17_tables']}")
    
    if result.success:
        console.print("[green]✓[/green] Verification passed")
    else:
        console.print("[yellow]⚠[/yellow] " + result.message)
    
    # Next steps
    console.print(Panel(
        "[bold]Next Steps:[/bold]\n\n"
        "1. Update LiteLLM configuration to use PostgreSQL 17:\n"
        "   DATABASE_URL=postgresql://user:pass@postgres-17:5432/litellm\n\n"
        "2. Restart LiteLLM to use new database\n\n"
        "3. Verify application functionality\n\n"
        "4. After 24h verification, decommission PostgreSQL 16",
        title="Migration Complete",
        border_style="green",
    ))


@app.command()
def verify() -> None:
    """Verify migration integrity.
    
    Compares table counts between source and target databases.
    """
    console.print(Panel("[bold blue]Verifying Migration[/bold blue]"))
    
    migration = DatabaseMigration()
    result = migration.verify_migration()
    
    table = Table()
    table.add_column("Database")
    table.add_column("Tables")
    
    table.add_row("PostgreSQL 16", str(result.details["pg16_tables"]))
    table.add_row("PostgreSQL 17", str(result.details["pg17_tables"]))
    
    console.print(table)
    console.print(f"\nPostgreSQL 17 version: {result.details['pg17_version']}")
    
    if result.success:
        console.print("\n[green]✓[/green] Verification passed - table counts match")
    else:
        console.print(f"\n[yellow]⚠[/yellow] {result.message}")


@app.command()
def status() -> None:
    """Show migration status and backup info.
    
    Lists available backups and current database states.
    """
    console.print(Panel("[bold blue]Migration Status[/bold blue]"))
    
    config = MigrationConfig()
    
    # List backups
    console.print("[bold]Available Backups:[/bold]")
    if config.backup_dir.exists():
        backups = sorted(config.backup_dir.glob("pg16_backup_*.sql"), reverse=True)
        if backups:
            for backup in backups[:5]:
                size_mb = backup.stat().st_size / (1024 * 1024)
                console.print(f"  {backup.name} ({size_mb:.1f} MB)")
        else:
            console.print("  [dim]No backups found[/dim]")
    else:
        console.print(f"  [dim]Backup directory not found: {config.backup_dir}[/dim]")


def main() -> None:
    """Entry point for the database migration CLI."""
    app()


if __name__ == "__main__":
    main()
