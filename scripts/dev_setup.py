#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
Development Environment Setup for Self-Hosted AI Platform.

This module automates the setup of a complete development environment
including Python agent framework, Rust runtime, and pre-commit hooks.

Why This Script Exists:
    Setting up a development environment manually is tedious and
    inconsistent across team members. This script ensures:
    - Correct Python version validation
    - Virtual environment creation with all dependencies
    - Rust toolchain compilation (if available)
    - Pre-commit hooks for code quality
    - Consistent setup across all developers

Components:
    - Python Agents: agents/ directory with pydantic-ai framework
    - Rust Runtime: rust-agents/ with high-performance execution
    - Pre-commit: Ruff, black, mypy, and conventional commits
    - Tests: pytest with coverage reporting

Usage:
    # Full setup with all components
    uv run scripts/dev_setup.py setup
    
    # Check environment without making changes
    uv run scripts/dev_setup.py check
    
    # Setup specific components
    uv run scripts/dev_setup.py setup --python-only
    uv run scripts/dev_setup.py setup --rust-only

Example:
    >>> from dev_setup import DevelopmentSetup
    >>> setup = DevelopmentSetup()
    >>> setup.check_python_version()  # Validates Python >= 3.12
    >>> setup.install_python_agents()  # Creates venv, installs deps
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="shai-dev",
    help="Setup development environment for Self-Hosted AI",
    no_args_is_help=True,
)
console = Console()


@dataclass
class DevConfig:
    """Configuration for development environment setup.
    
    Attributes:
        project_root: Root directory of the project
        agents_dir: Path to Python agents package
        rust_dir: Path to Rust agents package
        min_python_version: Minimum required Python version tuple
    """
    project_root: Path = field(
        default_factory=lambda: Path(__file__).parent.parent
    )
    agents_dir: Path = field(default=None)
    rust_dir: Path = field(default=None)
    min_python_version: tuple[int, int] = (3, 12)
    
    def __post_init__(self):
        """Initialize derived paths."""
        if self.agents_dir is None:
            self.agents_dir = self.project_root / "agents"
        if self.rust_dir is None:
            self.rust_dir = self.project_root / "rust-agents"


@dataclass
class CheckResult:
    """Result of an environment check.
    
    Attributes:
        name: What was checked
        passed: Whether the check passed
        message: Status message
        version: Version string if applicable
    """
    name: str
    passed: bool
    message: str = ""
    version: str = ""


class DevelopmentSetup:
    """Manages development environment setup.
    
    This class provides methods for validating and installing
    development dependencies. It ensures a consistent environment
    across all developer machines.
    
    Why Virtual Environments:
        Each project should have isolated dependencies to prevent
        conflicts between projects. The agents/ package has its
        own pyproject.toml with specific versions.
    
    Attributes:
        config: Development configuration
    """
    
    def __init__(self, config: DevConfig | None = None) -> None:
        """Initialize development setup.
        
        Args:
            config: Development configuration. Uses defaults if None.
        """
        self.config = config or DevConfig()
    
    def check_python_version(self) -> CheckResult:
        """Verify Python version meets requirements.
        
        Returns:
            CheckResult with version validation status.
        """
        current = sys.version_info[:2]
        required = self.config.min_python_version
        
        if current >= required:
            return CheckResult(
                name="Python Version",
                passed=True,
                version=f"{current[0]}.{current[1]}",
                message=f"Python {current[0]}.{current[1]} meets requirement",
            )
        else:
            return CheckResult(
                name="Python Version",
                passed=False,
                version=f"{current[0]}.{current[1]}",
                message=f"Python {required[0]}.{required[1]}+ required",
            )
    
    def check_uv(self) -> CheckResult:
        """Check if uv is installed.
        
        Returns:
            CheckResult with uv availability status.
        """
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version = result.stdout.strip().split()[-1]
            return CheckResult(
                name="uv",
                passed=True,
                version=version,
                message="uv package manager available",
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return CheckResult(
                name="uv",
                passed=False,
                message="uv not installed (https://github.com/astral-sh/uv)",
            )
    
    def check_rust(self) -> CheckResult:
        """Check if Rust toolchain is installed.
        
        Returns:
            CheckResult with Rust availability status.
        """
        try:
            result = subprocess.run(
                ["cargo", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version = result.stdout.strip().split()[1]
            return CheckResult(
                name="Rust",
                passed=True,
                version=version,
                message="Cargo available for Rust builds",
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return CheckResult(
                name="Rust",
                passed=False,
                message="Rust not installed (https://rustup.rs)",
            )
    
    def check_precommit(self) -> CheckResult:
        """Check if pre-commit is installed.
        
        Returns:
            CheckResult with pre-commit availability status.
        """
        try:
            result = subprocess.run(
                ["pre-commit", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version = result.stdout.strip().split()[-1]
            return CheckResult(
                name="Pre-commit",
                passed=True,
                version=version,
                message="Pre-commit hooks available",
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return CheckResult(
                name="Pre-commit",
                passed=False,
                message="pre-commit not installed",
            )
    
    def run_all_checks(self) -> list[CheckResult]:
        """Run all environment checks.
        
        Returns:
            List of check results.
        """
        return [
            self.check_python_version(),
            self.check_uv(),
            self.check_rust(),
            self.check_precommit(),
        ]
    
    def install_python_agents(self) -> bool:
        """Install Python agent framework.
        
        Creates virtual environment if needed and installs all
        dependencies from agents/pyproject.toml.
        
        Returns:
            True if installation succeeded.
        """
        agents_dir = self.config.agents_dir
        
        if not agents_dir.exists():
            console.print(f"[red]Agents directory not found:[/red] {agents_dir}")
            return False
        
        venv_path = agents_dir / "venv"
        
        # Create venv if it doesn't exist
        if not venv_path.exists():
            console.print("[dim]Creating virtual environment...[/dim]")
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                console.print(f"[red]Failed to create venv:[/red] {result.stderr}")
                return False
        
        # Determine pip path
        pip_path = venv_path / "bin" / "pip"
        
        # Upgrade pip
        subprocess.run(
            [str(pip_path), "install", "--upgrade", "pip", "setuptools", "wheel"],
            capture_output=True,
            check=True,
        )
        
        # Install package in editable mode with dev dependencies
        result = subprocess.run(
            [str(pip_path), "install", "-e", ".[dev]"],
            cwd=str(agents_dir),
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            console.print(f"[red]Installation failed:[/red] {result.stderr}")
            return False
        
        return True
    
    def build_rust_runtime(self) -> bool:
        """Build Rust agent runtime.
        
        Compiles the Rust workspace in release mode.
        
        Returns:
            True if build succeeded.
        """
        rust_dir = self.config.rust_dir
        
        if not rust_dir.exists():
            console.print(f"[yellow]Rust directory not found:[/yellow] {rust_dir}")
            return False
        
        # Check for cargo
        if not self.check_rust().passed:
            console.print("[yellow]Skipping Rust build (cargo not available)[/yellow]")
            return False
        
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=str(rust_dir),
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            console.print(f"[red]Rust build failed:[/red] {result.stderr}")
            return False
        
        return True
    
    def install_precommit_hooks(self) -> bool:
        """Install pre-commit hooks.
        
        Sets up pre-commit hooks for code quality and
        conventional commit message validation.
        
        Returns:
            True if installation succeeded.
        """
        project_root = self.config.project_root
        
        # Check if .pre-commit-config.yaml exists
        config_file = project_root / ".pre-commit-config.yaml"
        if not config_file.exists():
            console.print("[yellow]No .pre-commit-config.yaml found[/yellow]")
            return False
        
        # Install hooks
        result = subprocess.run(
            ["pre-commit", "install"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            console.print(f"[red]Pre-commit install failed:[/red] {result.stderr}")
            return False
        
        # Install commit-msg hook
        subprocess.run(
            ["pre-commit", "install", "--hook-type", "commit-msg"],
            cwd=str(project_root),
            capture_output=True,
        )
        
        return True
    
    def run_tests(self) -> bool:
        """Run test suite to verify installation.
        
        Returns:
            True if all tests pass.
        """
        agents_dir = self.config.agents_dir
        venv_pytest = agents_dir / "venv" / "bin" / "pytest"
        
        if not venv_pytest.exists():
            console.print("[yellow]pytest not found in venv[/yellow]")
            return False
        
        result = subprocess.run(
            [str(venv_pytest), "tests/", "-v", "--tb=short"],
            cwd=str(agents_dir),
            capture_output=True,
            text=True,
        )
        
        console.print(result.stdout)
        
        return result.returncode == 0


# =============================================================================
# CLI Commands
# =============================================================================


@app.command()
def check() -> None:
    """Check development environment status.
    
    Validates that all required tools are installed without
    making any changes. Use this to diagnose setup issues.
    """
    console.print(Panel("[bold blue]Development Environment Check[/bold blue]"))
    
    setup = DevelopmentSetup()
    results = setup.run_all_checks()
    
    table = Table()
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("Notes")
    
    all_passed = True
    for result in results:
        status = "[green]✓[/green]" if result.passed else "[red]✗[/red]"
        if not result.passed:
            all_passed = False
        
        table.add_row(
            result.name,
            status,
            result.version or "-",
            result.message,
        )
    
    console.print(table)
    
    if not all_passed:
        console.print("\n[yellow]Some checks failed. Run 'setup' to fix.[/yellow]")
        raise typer.Exit(1)
    else:
        console.print("\n[green]All checks passed![/green]")


@app.command()
def setup(
    python_only: Annotated[
        bool,
        typer.Option("--python-only", help="Only setup Python agents"),
    ] = False,
    rust_only: Annotated[
        bool,
        typer.Option("--rust-only", help="Only build Rust runtime"),
    ] = False,
    skip_tests: Annotated[
        bool,
        typer.Option("--skip-tests", help="Skip running tests after setup"),
    ] = False,
) -> None:
    """Setup complete development environment.
    
    Installs all development dependencies:
    - Python virtual environment with agent framework
    - Rust runtime compilation
    - Pre-commit hooks for code quality
    """
    console.print(Panel("[bold blue]Setting up Development Environment[/bold blue]"))
    
    setup_mgr = DevelopmentSetup()
    
    # Check Python version first
    python_check = setup_mgr.check_python_version()
    if not python_check.passed:
        console.print(f"[red]✗[/red] {python_check.message}")
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] Python {python_check.version}")
    
    # Install components based on flags
    install_all = not python_only and not rust_only
    
    if install_all or python_only:
        console.print("\n[bold]Installing Python Agents...[/bold]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Installing dependencies...", total=1)
            success = setup_mgr.install_python_agents()
            progress.update(task, completed=1)
        
        if success:
            console.print("[green]✓[/green] Python agents installed")
        else:
            console.print("[red]✗[/red] Python agents installation failed")
    
    if install_all or rust_only:
        console.print("\n[bold]Building Rust Runtime...[/bold]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Compiling...", total=1)
            success = setup_mgr.build_rust_runtime()
            progress.update(task, completed=1)
        
        if success:
            console.print("[green]✓[/green] Rust runtime built")
        else:
            console.print("[yellow]⚠[/yellow] Rust runtime skipped")
    
    if install_all:
        console.print("\n[bold]Installing Pre-commit Hooks...[/bold]")
        if setup_mgr.check_precommit().passed:
            success = setup_mgr.install_precommit_hooks()
            if success:
                console.print("[green]✓[/green] Pre-commit hooks installed")
            else:
                console.print("[yellow]⚠[/yellow] Pre-commit hooks failed")
        else:
            console.print("[yellow]⚠[/yellow] pre-commit not available")
    
    # Summary
    console.print(Panel(
        "[green]Setup Complete![/green]\n\n"
        "[bold]Next steps:[/bold]\n"
        "1. Activate venv: source agents/venv/bin/activate\n"
        "2. Run tests: cd agents && pytest tests/\n"
        "3. Check formatting: pre-commit run --all-files",
        title="✓ Development Environment Ready",
        border_style="green",
    ))
    
    # Optionally run tests
    if not skip_tests and (install_all or python_only):
        if typer.confirm("\nRun tests now?", default=False):
            console.print("\n[bold]Running Tests...[/bold]")
            success = setup_mgr.run_tests()
            if success:
                console.print("[green]✓[/green] All tests passed")
            else:
                console.print("[yellow]⚠[/yellow] Some tests failed")


@app.command()
def test() -> None:
    """Run the test suite.
    
    Executes pytest on the agents/ test directory.
    """
    console.print(Panel("[bold blue]Running Tests[/bold blue]"))
    
    setup_mgr = DevelopmentSetup()
    success = setup_mgr.run_tests()
    
    if not success:
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the development setup CLI."""
    app()


if __name__ == "__main__":
    main()
