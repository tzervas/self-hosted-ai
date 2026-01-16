#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
#     "semver>=3.0.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
Release Management for Self-Hosted AI Platform.

This module handles semantic versioning, git tagging, and GitHub release
creation for the self-hosted-ai project. It integrates with GitHub CLI
and supports both GHCR and Docker Hub registries.

Why This Script Exists:
    Manual version management is error-prone and inconsistent. This script
    provides:
    - Semantic versioning with automatic bumping (major/minor/patch)
    - Pre-release validation (clean working directory, main branch, etc.)
    - Automatic release notes generation from commit history
    - GitHub release creation via gh CLI

Versioning Strategy:
    We follow Semantic Versioning (semver.org):
    - MAJOR: Breaking changes to APIs or configurations
    - MINOR: New features, backward compatible
    - PATCH: Bug fixes, documentation updates
    
    Pre-release versions: 1.0.0-rc1, 1.0.0-beta2, etc.

Registries:
    - GHCR: ghcr.io/tzervas/self-hosted-ai
    - Docker Hub: tzervas01/self-hosted-ai

Usage:
    # Bump patch version and release
    uv run scripts/release.py bump patch
    
    # Bump minor version
    uv run scripts/release.py bump minor
    
    # Tag specific version
    uv run scripts/release.py tag 1.0.0-rc1
    
    # Show current version and status
    uv run scripts/release.py status

Example:
    >>> from release import ReleaseManager
    >>> manager = ReleaseManager()
    >>> manager.bump_version("patch")  # 0.1.0 -> 0.1.1
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated

import semver
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="shai-release",
    help="Manage releases with semantic versioning",
    no_args_is_help=True,
)
console = Console()


class BumpType(str, Enum):
    """Types of version bumps following semver."""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class ReleaseConfig:
    """Configuration for release management.
    
    Attributes:
        project_root: Root directory of the project
        version_file: Path to VERSION file
        github_repo: GitHub repository (owner/repo)
        dockerhub_repo: Docker Hub repository
    """
    project_root: Path = field(
        default_factory=lambda: Path(__file__).parent.parent
    )
    version_file: Path = field(default=None)
    github_repo: str = "tzervas/self-hosted-ai"
    dockerhub_repo: str = "tzervas01/self-hosted-ai"
    
    def __post_init__(self):
        """Set version_file after project_root is known."""
        if self.version_file is None:
            self.version_file = self.project_root / "VERSION"
    
    @property
    def ghcr_repo(self) -> str:
        """Get GitHub Container Registry URL."""
        return f"ghcr.io/{self.github_repo}"


@dataclass
class ReleaseResult:
    """Result of a release operation.
    
    Attributes:
        success: Whether the release succeeded
        version: The released version
        tag: The git tag created
        message: Status message
        release_url: URL to the GitHub release
    """
    success: bool
    version: str
    tag: str = ""
    message: str = ""
    release_url: str = ""


class ReleaseManager:
    """Manages the release lifecycle for the project.
    
    This class handles version bumping, git operations, and GitHub
    release creation. It ensures releases follow best practices:
    - Only from main branch
    - Clean working directory
    - Proper semantic versioning
    
    Why Validate Before Release:
        Releasing from a dirty working directory or non-main branch
        leads to inconsistencies between tagged versions and actual
        code. Pre-release checks catch these issues early.
    
    Attributes:
        config: Release configuration
    """
    
    def __init__(self, config: ReleaseConfig | None = None) -> None:
        """Initialize the release manager.
        
        Args:
            config: Release configuration. Uses defaults if None.
        """
        self.config = config or ReleaseConfig()
    
    def get_version(self) -> str:
        """Read current version from VERSION file.
        
        Returns:
            Current version string (e.g., "0.1.0").
        """
        if self.config.version_file.exists():
            return self.config.version_file.read_text().strip()
        return "0.0.0"
    
    def save_version(self, version: str) -> None:
        """Write version to VERSION file.
        
        Args:
            version: Version string to save.
        """
        self.config.version_file.write_text(f"{version}\n")
    
    def bump_semver(self, current: str, bump_type: BumpType) -> str:
        """Bump version according to semver rules.
        
        Args:
            current: Current version string.
            bump_type: Type of bump (major/minor/patch).
            
        Returns:
            New version string.
        """
        # Parse current version, stripping 'v' prefix if present
        current = current.lstrip("v")
        
        # Handle versions without prerelease/build metadata
        try:
            ver = semver.Version.parse(current)
        except ValueError:
            # If parsing fails, try to construct from parts
            parts = current.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch_str = parts[2].split("-")[0] if len(parts) > 2 else "0"
            patch = int(patch_str)
            ver = semver.Version(major=major, minor=minor, patch=patch)
        
        # Apply bump
        if bump_type == BumpType.MAJOR:
            return str(ver.bump_major())
        elif bump_type == BumpType.MINOR:
            return str(ver.bump_minor())
        else:
            return str(ver.bump_patch())
    
    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the project root.
        
        Args:
            args: Git command arguments.
            check: Raise exception on non-zero exit.
            
        Returns:
            Completed process result.
        """
        return subprocess.run(
            ["git", "-C", str(self.config.project_root)] + list(args),
            capture_output=True,
            text=True,
            check=check,
        )
    
    def check_prerequisites(self) -> list[str]:
        """Validate prerequisites for creating a release.
        
        Checks:
        - On main branch
        - No uncommitted changes
        - Up to date with remote
        - Docker available
        - GitHub CLI authenticated
        
        Returns:
            List of error messages (empty if all checks pass).
        """
        errors = []
        
        # Check branch
        result = self._run_git("branch", "--show-current", check=False)
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch != "main":
                errors.append(f"Must be on main branch (current: {branch})")
        else:
            errors.append("Cannot determine current branch")
        
        # Check for uncommitted changes
        result = self._run_git("diff", "--quiet", "HEAD", check=False)
        if result.returncode != 0:
            errors.append("Working directory has uncommitted changes")
        
        # Check sync with remote
        self._run_git("fetch", "origin", "main", check=False)
        local_sha = self._run_git("rev-parse", "HEAD", check=False).stdout.strip()
        remote_sha = self._run_git("rev-parse", "origin/main", check=False).stdout.strip()
        
        if local_sha and remote_sha and local_sha != remote_sha:
            errors.append("Local main is not up to date with origin/main")
        
        # Check gh CLI
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                errors.append("Not authenticated with GitHub CLI (run: gh auth login)")
        except FileNotFoundError:
            errors.append("GitHub CLI (gh) not installed")
        
        return errors
    
    def get_release_notes(self, since_tag: str | None = None) -> str:
        """Generate release notes from commit history.
        
        Args:
            since_tag: Generate notes since this tag. If None, uses last tag.
            
        Returns:
            Markdown-formatted release notes.
        """
        # Find previous tag
        if not since_tag:
            result = self._run_git(
                "describe", "--tags", "--abbrev=0", "HEAD^",
                check=False,
            )
            since_tag = result.stdout.strip() if result.returncode == 0 else None
        
        if since_tag:
            # Get commits since tag
            result = self._run_git(
                "log", f"{since_tag}..HEAD",
                "--pretty=format:- %s",
                "--no-merges",
                check=False,
            )
            notes = result.stdout.strip()
        else:
            notes = "Initial release"
        
        return notes if notes else "Bug fixes and improvements"
    
    def get_latest_tags(self, count: int = 5) -> list[str]:
        """Get the most recent git tags.
        
        Args:
            count: Number of tags to return.
            
        Returns:
            List of tag names, most recent first.
        """
        result = self._run_git(
            "tag", "-l", "--sort=-version:refname",
            check=False,
        )
        if result.returncode == 0:
            tags = result.stdout.strip().split("\n")
            return [t for t in tags[:count] if t]
        return []
    
    def create_release(
        self,
        version: str,
        dry_run: bool = False,
    ) -> ReleaseResult:
        """Create a new release.
        
        This method:
        1. Updates VERSION file
        2. Commits the change
        3. Creates annotated git tag
        4. Pushes to origin
        5. Creates GitHub release
        
        Args:
            version: Version to release.
            dry_run: If True, show what would happen without doing it.
            
        Returns:
            ReleaseResult with success status and details.
        """
        tag = f"v{version}"
        
        if dry_run:
            return ReleaseResult(
                success=True,
                version=version,
                tag=tag,
                message=f"[DRY RUN] Would release {version}",
            )
        
        try:
            # Update VERSION file
            self.save_version(version)
            console.print(f"[green]✓[/green] Updated VERSION to {version}")
            
            # Commit
            self._run_git("add", "VERSION")
            self._run_git("commit", "-m", f"chore: bump version to {version}")
            self._run_git("push", "origin", "main")
            console.print("[green]✓[/green] Committed and pushed version bump")
            
            # Create tag
            self._run_git("tag", "-a", tag, "-m", f"Release {version}")
            self._run_git("push", "origin", tag)
            console.print(f"[green]✓[/green] Created and pushed tag {tag}")
            
            # Create GitHub release
            notes = self.get_release_notes()
            result = subprocess.run(
                [
                    "gh", "release", "create", tag,
                    "--repo", self.config.github_repo,
                    "--title", f"Release {version}",
                    "--notes", notes,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            
            release_url = result.stdout.strip()
            console.print(f"[green]✓[/green] Created GitHub release: {release_url}")
            
            return ReleaseResult(
                success=True,
                version=version,
                tag=tag,
                message=f"Released {version}",
                release_url=release_url,
            )
            
        except subprocess.CalledProcessError as e:
            return ReleaseResult(
                success=False,
                version=version,
                tag=tag,
                message=f"Release failed: {e.stderr}",
            )
        except Exception as e:
            return ReleaseResult(
                success=False,
                version=version,
                message=f"Release failed: {e}",
            )


# =============================================================================
# CLI Commands
# =============================================================================


@app.command()
def bump(
    bump_type: Annotated[
        BumpType,
        typer.Argument(help="Type of version bump"),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be done"),
    ] = False,
) -> None:
    """Bump version and create release.
    
    Increments the version according to semantic versioning rules:
    - major: Breaking changes (1.0.0 -> 2.0.0)
    - minor: New features (1.0.0 -> 1.1.0)
    - patch: Bug fixes (1.0.0 -> 1.0.1)
    """
    console.print(Panel(f"[bold blue]Bump Version ({bump_type.value})[/bold blue]"))
    
    manager = ReleaseManager()
    
    # Check prerequisites
    if not dry_run:
        errors = manager.check_prerequisites()
        if errors:
            console.print("[red]Pre-release checks failed:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)
        console.print("[green]✓[/green] All pre-release checks passed")
    
    # Calculate new version
    current = manager.get_version()
    new_version = manager.bump_semver(current, bump_type)
    
    console.print(f"\nVersion: {current} → [bold]{new_version}[/bold]\n")
    
    # Create release
    result = manager.create_release(new_version, dry_run)
    
    if result.success:
        console.print(Panel(
            f"[green]Released version {result.version}[/green]\n\n"
            f"Tag: {result.tag}\n"
            f"URL: {result.release_url or 'N/A'}",
            title="✓ Release Complete",
            border_style="green",
        ))
    else:
        console.print(f"[red]Release failed:[/red] {result.message}")
        raise typer.Exit(1)


@app.command()
def tag(
    version: Annotated[
        str,
        typer.Argument(help="Specific version to tag (e.g., 1.0.0-rc1)"),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be done"),
    ] = False,
) -> None:
    """Tag a specific version and create release.
    
    Use this for pre-release versions or when you need to set
    a specific version number rather than bumping.
    """
    console.print(Panel(f"[bold blue]Tag Version: {version}[/bold blue]"))
    
    manager = ReleaseManager()
    
    # Check prerequisites
    if not dry_run:
        errors = manager.check_prerequisites()
        if errors:
            console.print("[red]Pre-release checks failed:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)
        console.print("[green]✓[/green] All pre-release checks passed")
    
    # Create release
    result = manager.create_release(version, dry_run)
    
    if result.success:
        console.print(Panel(
            f"[green]Released version {result.version}[/green]\n\n"
            f"Tag: {result.tag}\n"
            f"URL: {result.release_url or 'N/A'}",
            title="✓ Release Complete",
            border_style="green",
        ))
    else:
        console.print(f"[red]Release failed:[/red] {result.message}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show current version and release status.
    
    Displays the current version from VERSION file, recent tags,
    and configured registries.
    """
    manager = ReleaseManager()
    
    current = manager.get_version()
    tags = manager.get_latest_tags()
    
    console.print(Panel(f"[bold]Current Version:[/bold] {current}"))
    console.print()
    
    # Recent tags
    table = Table(title="Recent Tags")
    table.add_column("Tag")
    
    if tags:
        for tag in tags:
            table.add_row(tag)
    else:
        table.add_row("[dim]No tags yet[/dim]")
    
    console.print(table)
    console.print()
    
    # Registries
    console.print("[bold]Registries:[/bold]")
    console.print(f"  GHCR: {manager.config.ghcr_repo}")
    console.print(f"  Docker Hub: {manager.config.dockerhub_repo}")


@app.command()
def check() -> None:
    """Run pre-release checks.
    
    Validates that all prerequisites are met for creating a release:
    - On main branch
    - No uncommitted changes
    - Up to date with remote
    - GitHub CLI authenticated
    """
    console.print(Panel("[bold blue]Pre-Release Checks[/bold blue]"))
    
    manager = ReleaseManager()
    errors = manager.check_prerequisites()
    
    checks = [
        ("Main branch", "On main branch" not in str(errors)),
        ("Clean working directory", "uncommitted changes" not in str(errors)),
        ("Synced with remote", "not up to date" not in str(errors)),
        ("GitHub CLI", "gh" not in str(errors).lower()),
    ]
    
    for name, passed in checks:
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {status} {name}")
    
    if errors:
        console.print()
        console.print("[red]Issues found:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)
    else:
        console.print()
        console.print("[green]All checks passed - ready to release[/green]")


def main() -> None:
    """Entry point for the release CLI."""
    app()


if __name__ == "__main__":
    main()
