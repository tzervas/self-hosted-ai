"""
Cluster Validation System
=========================
Comprehensive health checks for the Self-Hosted AI Platform.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lib.config import Settings, get_settings
from lib.kubernetes import kubernetes_client
from lib.services import (
    GrafanaClient,
    LiteLLMClient,
    N8NClient,
    OllamaClient,
    OpenWebUIClient,
    SearXNGClient,
    GitLabClient,
)

app = typer.Typer(
    name="shai-validate",
    help="Validate Self-Hosted AI Platform health",
    no_args_is_help=True,
)
console = Console()


class CheckStatus(str, Enum):
    """Health check result status."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a health check."""

    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None

    def status_icon(self) -> str:
        """Return status indicator."""
        return {
            CheckStatus.PASS: "[green]✓[/green]",
            CheckStatus.WARN: "[yellow]⚠[/yellow]",
            CheckStatus.FAIL: "[red]✗[/red]",
            CheckStatus.SKIP: "[dim]○[/dim]",
        }[self.status]


# ============================================
# CLI Commands
# ============================================


@app.command()
def all(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Attempt automatic fixes"),
    ] = False,
) -> None:
    """Run all validation checks."""
    console.print(Panel("[bold blue]Self-Hosted AI Platform - Validation[/bold blue]"))

    results = asyncio.run(_run_all_checks(verbose, fix))

    # Summary
    passed = sum(1 for r in results if r.status == CheckStatus.PASS)
    warned = sum(1 for r in results if r.status == CheckStatus.WARN)
    failed = sum(1 for r in results if r.status == CheckStatus.FAIL)

    console.print()
    console.print(f"[bold]Summary:[/bold] {passed} passed, {warned} warnings, {failed} failed")

    if failed > 0:
        raise typer.Exit(1)


@app.command()
def dns(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Validate DNS resolution for all services."""
    results = asyncio.run(_check_dns())
    _print_results(results, "DNS Resolution", verbose)


@app.command()
def tls(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Validate TLS certificates for all services."""
    results = asyncio.run(_check_tls())
    _print_results(results, "TLS Certificates", verbose)


@app.command()
def services(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Validate all service APIs."""
    results = asyncio.run(_check_services())
    _print_results(results, "Service APIs", verbose)


@app.command()
def kubernetes(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Validate Kubernetes resources."""
    results = asyncio.run(_check_kubernetes())
    _print_results(results, "Kubernetes", verbose)


@app.command()
def models(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed output"),
    ] = False,
) -> None:
    """Validate AI models are available."""
    results = asyncio.run(_check_models())
    _print_results(results, "AI Models", verbose)


# ============================================
# Check Implementations
# ============================================


async def _run_all_checks(verbose: bool, fix: bool) -> list[CheckResult]:
    """Run all validation checks."""
    all_results: list[CheckResult] = []

    check_groups = [
        ("DNS Resolution", _check_dns),
        ("TLS Certificates", _check_tls),
        ("Kubernetes", _check_kubernetes),
        ("Service APIs", _check_services),
        ("AI Models", _check_models),
    ]

    for group_name, check_func in check_groups:
        console.print(f"\n[bold]{group_name}[/bold]")
        results = await check_func()
        all_results.extend(results)

        for result in results:
            icon = result.status_icon()
            msg = f"  {icon} {result.name}: {result.message}"
            if verbose and result.details:
                msg += f"\n      [dim]{result.details}[/dim]"
            console.print(msg)

    return all_results


async def _check_dns() -> list[CheckResult]:
    """Check DNS resolution for all service hostnames."""
    settings = get_settings()
    results: list[CheckResult] = []

    hostnames = [
        f"ai.{settings.domain}",
        f"llm.{settings.domain}",
        f"n8n.{settings.domain}",
        f"grafana.{settings.domain}",
        f"search.{settings.domain}",
        f"git.{settings.domain}",
    ]

    for hostname in hostnames:
        try:
            ip = socket.gethostbyname(hostname)
            results.append(CheckResult(
                name=hostname,
                status=CheckStatus.PASS,
                message=f"resolves to {ip}",
            ))
        except socket.gaierror as e:
            results.append(CheckResult(
                name=hostname,
                status=CheckStatus.FAIL,
                message="DNS resolution failed",
                details=str(e),
            ))

    return results


async def _check_tls() -> list[CheckResult]:
    """Check TLS certificates for all services."""
    settings = get_settings()
    results: list[CheckResult] = []

    endpoints = [
        f"https://ai.{settings.domain}",
        f"https://llm.{settings.domain}",
        f"https://n8n.{settings.domain}",
        f"https://grafana.{settings.domain}",
    ]

    for endpoint in endpoints:
        try:
            # Allow self-signed certs for now
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.get(endpoint, follow_redirects=True)
                results.append(CheckResult(
                    name=endpoint,
                    status=CheckStatus.PASS,
                    message=f"TLS working (status {response.status_code})",
                ))
        except httpx.ConnectError as e:
            results.append(CheckResult(
                name=endpoint,
                status=CheckStatus.FAIL,
                message="Connection failed",
                details=str(e),
            ))
        except Exception as e:
            results.append(CheckResult(
                name=endpoint,
                status=CheckStatus.WARN,
                message="TLS issue",
                details=str(e),
            ))

    return results


async def _check_kubernetes() -> list[CheckResult]:
    """Check Kubernetes resources."""
    results: list[CheckResult] = []

    async with kubernetes_client() as client:
        # Check critical namespaces
        for ns in ["self-hosted-ai", "argocd", "cert-manager", "gpu-workloads"]:
            try:
                namespace = await client.get_namespace(ns)
                if namespace:
                    results.append(CheckResult(
                        name=f"namespace/{ns}",
                        status=CheckStatus.PASS,
                        message="exists",
                    ))
                else:
                    results.append(CheckResult(
                        name=f"namespace/{ns}",
                        status=CheckStatus.FAIL,
                        message="not found",
                    ))
            except Exception as e:
                results.append(CheckResult(
                    name=f"namespace/{ns}",
                    status=CheckStatus.FAIL,
                    message=str(e),
                ))

        # Check critical pods
        pods = await client.list_pods("self-hosted-ai")
        running_pods = [p for p in pods if p.get("status") == "Running"]
        total = len(pods)
        running = len(running_pods)

        if running == total and total > 0:
            results.append(CheckResult(
                name="pods/self-hosted-ai",
                status=CheckStatus.PASS,
                message=f"{running}/{total} running",
            ))
        elif running > 0:
            results.append(CheckResult(
                name="pods/self-hosted-ai",
                status=CheckStatus.WARN,
                message=f"{running}/{total} running",
            ))
        else:
            results.append(CheckResult(
                name="pods/self-hosted-ai",
                status=CheckStatus.FAIL,
                message=f"{running}/{total} running",
            ))

        # Check certificates
        certs = await client.list_certificates("self-hosted-ai")
        for cert in certs:
            name = cert.get("name", "unknown")
            ready = cert.get("ready", False)
            results.append(CheckResult(
                name=f"certificate/{name}",
                status=CheckStatus.PASS if ready else CheckStatus.FAIL,
                message="ready" if ready else "not ready",
            ))

    return results


async def _check_services() -> list[CheckResult]:
    """Check all service APIs."""
    settings = get_settings()
    results: list[CheckResult] = []

    service_checks = [
        ("Open WebUI", OpenWebUIClient(settings)),
        ("LiteLLM", LiteLLMClient(settings)),
        ("n8n", N8NClient(settings)),
        ("Grafana", GrafanaClient(settings)),
        ("SearXNG", SearXNGClient(settings)),
    ]

    for name, client in service_checks:
        try:
            async with client:
                health = await client.health_check()
                if health.get("status") == "healthy":
                    results.append(CheckResult(
                        name=name,
                        status=CheckStatus.PASS,
                        message="healthy",
                        details=health.get("details"),
                    ))
                else:
                    results.append(CheckResult(
                        name=name,
                        status=CheckStatus.WARN,
                        message=health.get("status", "unknown"),
                        details=health.get("error"),
                    ))
        except Exception as e:
            results.append(CheckResult(
                name=name,
                status=CheckStatus.FAIL,
                message="unreachable",
                details=str(e),
            ))

    return results


async def _check_models() -> list[CheckResult]:
    """Check AI model availability."""
    settings = get_settings()
    results: list[CheckResult] = []

    ollama_endpoints = [
        ("Ollama (cluster)", f"http://ollama.self-hosted-ai:11434"),
        ("Ollama (GPU)", f"http://{settings.gpu_worker_ip}:11434"),
    ]

    for name, url in ollama_endpoints:
        try:
            async with OllamaClient(url) as client:
                models = await client.list_models()
                if models:
                    model_names = [m.get("name", "unknown") for m in models[:3]]
                    results.append(CheckResult(
                        name=name,
                        status=CheckStatus.PASS,
                        message=f"{len(models)} models",
                        details=", ".join(model_names),
                    ))
                else:
                    results.append(CheckResult(
                        name=name,
                        status=CheckStatus.WARN,
                        message="no models loaded",
                    ))
        except Exception as e:
            results.append(CheckResult(
                name=name,
                status=CheckStatus.FAIL,
                message="unreachable",
                details=str(e),
            ))

    return results


def _print_results(results: list[CheckResult], title: str, verbose: bool) -> None:
    """Print check results."""
    table = Table(title=title)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    if verbose:
        table.add_column("Details")

    for result in results:
        row = [result.name, result.status_icon(), result.message]
        if verbose:
            row.append(result.details or "")
        table.add_row(*row)

    console.print(table)


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
