#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typer>=0.12.0",
#     "rich>=13.9.0",
#     "asyncpg>=0.29.0",
#     "httpx>=0.27.0",
# ]
# [tool.uv]
# exclude-newer = "2026-01-01"
# ///
"""
API Key Management System for Self-Hosted AI Agent Server.

This module provides comprehensive API key lifecycle management including
generation, rotation, revocation, and monitoring. Keys support tiered
rate limiting and automatic 90-day rotation policies.

Why This Script Exists:
    The agent server requires API authentication for external consumers.
    Manual key management is error-prone and doesn't track expiration.
    This script provides:
    - Cryptographically secure key generation (sk_xxx format)
    - Automatic rotation reminders before expiration
    - Prometheus metrics export for observability
    - Audit trail for key lifecycle events

Security Model:
    - Keys are hashed (SHA-256) before storage - original never persisted
    - Key prefix (first 12 chars) stored for identification
    - Tier-based rate limiting (free: 10/min, standard: 60/min, premium: 1000/min)
    - 90-day automatic rotation policy with 80-day warning

Usage:
    # Generate a new API key
    uv run scripts/api_keys.py generate --name "production-api" --tier premium
    
    # List all keys with status
    uv run scripts/api_keys.py list
    
    # Rotate a key (generates new key, invalidates old)
    uv run scripts/api_keys.py rotate --key-prefix sk_abc123
    
    # Check for keys needing rotation
    uv run scripts/api_keys.py check
    
    # Export Prometheus metrics
    uv run scripts/api_keys.py metrics > /var/lib/prometheus/keys.prom

Example:
    >>> from api_keys import APIKeyManager
    >>> manager = APIKeyManager()
    >>> key = await manager.generate_key("my-service", tier=KeyTier.STANDARD)
    >>> print(f"Save this key: {key.secret}")
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated

import asyncpg
import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="shai-keys",
    help="Manage API keys for the Self-Hosted AI agent server",
    no_args_is_help=True,
)
console = Console()


class KeyTier(str, Enum):
    """API key access tiers with different rate limits.
    
    Each tier has progressively higher rate limits for different use cases:
    - FREE: Testing and personal projects
    - STANDARD: Production applications
    - PREMIUM: High-throughput services
    """
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


# Rate limits per tier (requests per minute)
TIER_RATE_LIMITS = {
    KeyTier.FREE: 10,
    KeyTier.STANDARD: 60,
    KeyTier.PREMIUM: 1000,
}


@dataclass
class KeyConfig:
    """Configuration for API key management.
    
    Attributes:
        database_url: PostgreSQL connection string
        rotation_days: Days until key expires (default 90)
        warning_days: Days before expiration to warn (default 80)
        agent_server_url: Agent server URL for API-based management
    """
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql://agents:agents@localhost:5432/agents"
        )
    )
    rotation_days: int = field(
        default_factory=lambda: int(os.environ.get("KEY_ROTATION_DAYS", "90"))
    )
    warning_days: int = field(
        default_factory=lambda: int(os.environ.get("KEY_WARNING_DAYS", "80"))
    )
    agent_server_url: str = field(
        default_factory=lambda: os.environ.get("AGENT_SERVER_URL", "http://localhost:8080")
    )


@dataclass
class APIKey:
    """Represents an API key record.
    
    Attributes:
        key_prefix: First 12 characters for identification
        key_hash: SHA-256 hash of the full key
        name: Human-readable key name
        tier: Access tier (free/standard/premium)
        rate_limit: Requests per minute allowed
        is_active: Whether key is currently valid
        created_at: When key was generated
        expires_at: When key becomes invalid
        rotated_at: When key was last rotated
        revoked_at: When key was revoked (if applicable)
        secret: The actual key value (only set during generation)
    """
    key_prefix: str
    key_hash: str
    name: str
    tier: KeyTier
    rate_limit: int
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    secret: str | None = None  # Only populated during generation
    
    @property
    def days_until_expiry(self) -> int | None:
        """Calculate days until key expires."""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)
    
    @property
    def is_expiring_soon(self) -> bool:
        """Check if key is within warning period."""
        days = self.days_until_expiry
        return days is not None and days <= 10


class APIKeyManager:
    """Manages API key lifecycle operations.
    
    This class provides methods for generating, rotating, revoking, and
    querying API keys. Keys are stored with hashed values for security.
    
    Why Hash Keys:
        API keys are sensitive credentials. By storing only the hash,
        even database compromise doesn't reveal actual keys. The prefix
        allows identification without exposing the full key.
    
    Attributes:
        config: Key management configuration
        pool: Database connection pool (created lazily)
    """
    
    def __init__(self, config: KeyConfig | None = None) -> None:
        """Initialize the API key manager.
        
        Args:
            config: Key configuration. Uses defaults from environment if None.
        """
        self.config = config or KeyConfig()
        self._pool: asyncpg.Pool | None = None
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create database connection pool.
        
        Returns:
            Connection pool for database operations.
        """
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=1,
                max_size=5,
            )
        return self._pool
    
    async def close(self) -> None:
        """Close database connections."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    @staticmethod
    def generate_key_value() -> str:
        """Generate a cryptographically secure API key.
        
        Key format: sk_<base64url-encoded-32-bytes>
        The 'sk_' prefix identifies it as a secret key.
        
        Returns:
            New API key string.
        """
        random_bytes = secrets.token_bytes(32)
        encoded = base64.urlsafe_b64encode(random_bytes).decode().rstrip("=")
        return f"sk_{encoded}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash a key for secure storage.
        
        Args:
            key: The API key to hash.
            
        Returns:
            SHA-256 hex digest of the key.
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    async def generate_key(
        self,
        name: str,
        tier: KeyTier = KeyTier.STANDARD,
        rate_limit: int | None = None,
        expires_days: int | None = None,
    ) -> APIKey:
        """Generate a new API key.
        
        Creates a new key with the specified parameters and stores
        the hashed version in the database.
        
        Args:
            name: Human-readable key name/description
            tier: Access tier for rate limiting
            rate_limit: Custom rate limit (uses tier default if None)
            expires_days: Days until expiration (uses config default if None)
            
        Returns:
            APIKey with the secret field populated (save this!)
        """
        key_value = self.generate_key_value()
        key_hash = self.hash_key(key_value)
        key_prefix = key_value[:12]
        
        if rate_limit is None:
            rate_limit = TIER_RATE_LIMITS[tier]
        
        if expires_days is None:
            expires_days = self.config.rotation_days
        
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        pool = await self._get_pool()
        
        await pool.execute("""
            INSERT INTO api_keys (
                key_hash, key_prefix, name, tier, rate_limit_per_minute,
                expires_at, created_at, is_active
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), true)
        """, key_hash, key_prefix, name, tier.value, rate_limit, expires_at)
        
        return APIKey(
            key_prefix=key_prefix,
            key_hash=key_hash,
            name=name,
            tier=tier,
            rate_limit=rate_limit,
            expires_at=expires_at,
            secret=key_value,  # Only time we have the actual key
        )
    
    async def rotate_key(self, key_prefix: str) -> APIKey:
        """Rotate an existing API key.
        
        Generates a new key value while preserving the key's name,
        tier, and rate limit settings. The old key becomes invalid.
        
        Args:
            key_prefix: First 12 characters of the key to rotate.
            
        Returns:
            APIKey with new secret (save this!)
            
        Raises:
            ValueError: If key not found.
        """
        pool = await self._get_pool()
        
        # Get existing key info
        row = await pool.fetchrow("""
            SELECT name, tier, rate_limit_per_minute 
            FROM api_keys 
            WHERE key_prefix = $1 AND is_active = true
        """, key_prefix)
        
        if not row:
            raise ValueError(f"Active key not found: {key_prefix}")
        
        # Generate new key
        new_key_value = self.generate_key_value()
        new_key_hash = self.hash_key(new_key_value)
        new_key_prefix = new_key_value[:12]
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.config.rotation_days)
        
        # Update in database
        await pool.execute("""
            UPDATE api_keys SET
                key_hash = $1,
                key_prefix = $2,
                expires_at = $3,
                rotated_at = NOW()
            WHERE key_prefix = $4
        """, new_key_hash, new_key_prefix, expires_at, key_prefix)
        
        return APIKey(
            key_prefix=new_key_prefix,
            key_hash=new_key_hash,
            name=row["name"],
            tier=KeyTier(row["tier"]),
            rate_limit=row["rate_limit_per_minute"],
            expires_at=expires_at,
            secret=new_key_value,
        )
    
    async def revoke_key(self, key_prefix: str) -> str:
        """Revoke an API key.
        
        Marks the key as inactive. Revoked keys cannot be used
        for authentication but are retained for audit purposes.
        
        Args:
            key_prefix: First 12 characters of the key to revoke.
            
        Returns:
            Name of the revoked key.
            
        Raises:
            ValueError: If key not found or already revoked.
        """
        pool = await self._get_pool()
        
        result = await pool.fetchval("""
            UPDATE api_keys 
            SET is_active = false, revoked_at = NOW()
            WHERE key_prefix = $1 AND is_active = true
            RETURNING name
        """, key_prefix)
        
        if not result:
            raise ValueError(f"Active key not found: {key_prefix}")
        
        return result
    
    async def list_keys(self) -> list[APIKey]:
        """List all API keys.
        
        Returns:
            List of all keys (active and inactive).
        """
        pool = await self._get_pool()
        
        rows = await pool.fetch("""
            SELECT key_prefix, key_hash, name, tier, rate_limit_per_minute,
                   is_active, created_at, expires_at, rotated_at, revoked_at
            FROM api_keys
            ORDER BY created_at DESC
        """)
        
        return [
            APIKey(
                key_prefix=row["key_prefix"],
                key_hash=row["key_hash"],
                name=row["name"],
                tier=KeyTier(row["tier"]),
                rate_limit=row["rate_limit_per_minute"],
                is_active=row["is_active"],
                created_at=row["created_at"].replace(tzinfo=timezone.utc) if row["created_at"] else None,
                expires_at=row["expires_at"].replace(tzinfo=timezone.utc) if row["expires_at"] else None,
                rotated_at=row["rotated_at"].replace(tzinfo=timezone.utc) if row["rotated_at"] else None,
                revoked_at=row["revoked_at"].replace(tzinfo=timezone.utc) if row["revoked_at"] else None,
            )
            for row in rows
        ]
    
    async def check_expiring(self) -> list[APIKey]:
        """Find keys expiring within warning period.
        
        Returns:
            List of active keys expiring soon.
        """
        pool = await self._get_pool()
        warning_date = datetime.now(timezone.utc) + timedelta(days=self.config.warning_days)
        
        rows = await pool.fetch("""
            SELECT key_prefix, key_hash, name, tier, rate_limit_per_minute,
                   is_active, created_at, expires_at
            FROM api_keys
            WHERE is_active = true AND expires_at <= $1
            ORDER BY expires_at
        """, warning_date)
        
        return [
            APIKey(
                key_prefix=row["key_prefix"],
                key_hash=row["key_hash"],
                name=row["name"],
                tier=KeyTier(row["tier"]),
                rate_limit=row["rate_limit_per_minute"],
                is_active=row["is_active"],
                expires_at=row["expires_at"].replace(tzinfo=timezone.utc) if row["expires_at"] else None,
            )
            for row in rows
        ]
    
    async def cleanup_expired(self) -> int:
        """Remove expired and revoked keys older than 30 days.
        
        Returns:
            Number of keys deleted.
        """
        pool = await self._get_pool()
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        
        result = await pool.execute("""
            DELETE FROM api_keys
            WHERE (is_active = false AND revoked_at < $1)
               OR (expires_at < $1)
        """, cutoff)
        
        # Parse "DELETE N" response
        return int(result.split()[-1])
    
    async def get_metrics(self) -> dict:
        """Get Prometheus-format metrics about keys.
        
        Returns:
            Dictionary with metric values.
        """
        pool = await self._get_pool()
        
        stats = await pool.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE is_active) as active_keys,
                COUNT(*) FILTER (WHERE NOT is_active) as revoked_keys,
                COUNT(*) FILTER (WHERE is_active AND expires_at <= NOW() + INTERVAL '10 days') as expiring_soon,
                COUNT(*) FILTER (WHERE tier = 'free') as free_tier,
                COUNT(*) FILTER (WHERE tier = 'standard') as standard_tier,
                COUNT(*) FILTER (WHERE tier = 'premium') as premium_tier
            FROM api_keys
        """)
        
        return dict(stats)


# =============================================================================
# CLI Commands
# =============================================================================


@app.command()
def generate(
    name: Annotated[str, typer.Option("--name", "-n", help="Key name/description")],
    tier: Annotated[
        KeyTier,
        typer.Option("--tier", "-t", help="Access tier"),
    ] = KeyTier.STANDARD,
    rate_limit: Annotated[
        int | None,
        typer.Option("--rate-limit", "-l", help="Custom rate limit per minute"),
    ] = None,
    expires: Annotated[
        int,
        typer.Option("--expires", "-e", help="Days until expiration"),
    ] = 90,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Only output the key"),
    ] = False,
) -> None:
    """Generate a new API key.
    
    Creates a cryptographically secure API key with the specified
    settings. The key is only shown once - save it immediately.
    """
    async def _generate():
        manager = APIKeyManager()
        try:
            key = await manager.generate_key(
                name=name,
                tier=tier,
                rate_limit=rate_limit,
                expires_days=expires,
            )
            return key
        finally:
            await manager.close()
    
    if not quiet:
        console.print(Panel("[bold blue]Generating API Key[/bold blue]"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=quiet,
    ) as progress:
        task = progress.add_task("Generating...", total=1)
        key = asyncio.run(_generate())
        progress.update(task, completed=1)
    
    if quiet:
        print(key.secret)
    else:
        console.print()
        console.print(Panel(
            f"[bold red]IMPORTANT:[/bold red] Save this key now. It cannot be retrieved later.\n\n"
            f"[bold]Key:[/bold] {key.secret}\n"
            f"[bold]Name:[/bold] {key.name}\n"
            f"[bold]Tier:[/bold] {key.tier.value}\n"
            f"[bold]Rate Limit:[/bold] {key.rate_limit}/min\n"
            f"[bold]Expires:[/bold] {key.expires_at.isoformat() if key.expires_at else 'Never'}",
            title="[green]✓ Key Generated[/green]",
            border_style="green",
        ))


@app.command()
def rotate(
    key_prefix: Annotated[
        str,
        typer.Option("--key-prefix", "-k", help="Key prefix to rotate (first 12 chars)"),
    ],
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Only output the new key"),
    ] = False,
) -> None:
    """Rotate an existing API key.
    
    Generates a new key value while preserving settings.
    Update your applications with the new key immediately.
    """
    async def _rotate():
        manager = APIKeyManager()
        try:
            return await manager.rotate_key(key_prefix)
        finally:
            await manager.close()
    
    if not quiet:
        console.print(Panel(f"[bold blue]Rotating Key: {key_prefix}[/bold blue]"))
    
    try:
        key = asyncio.run(_rotate())
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    
    if quiet:
        print(key.secret)
    else:
        console.print(Panel(
            f"[bold red]Update your applications with the new key.[/bold red]\n\n"
            f"[bold]New Key:[/bold] {key.secret}\n"
            f"[bold]Name:[/bold] {key.name}\n"
            f"[bold]Expires:[/bold] {key.expires_at.isoformat() if key.expires_at else 'Never'}",
            title="[green]✓ Key Rotated[/green]",
            border_style="green",
        ))


@app.command()
def revoke(
    key_prefix: Annotated[
        str,
        typer.Option("--key-prefix", "-k", help="Key prefix to revoke"),
    ],
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output"),
    ] = False,
) -> None:
    """Revoke an API key.
    
    Immediately invalidates the key. This cannot be undone.
    """
    async def _revoke():
        manager = APIKeyManager()
        try:
            return await manager.revoke_key(key_prefix)
        finally:
            await manager.close()
    
    try:
        name = asyncio.run(_revoke())
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    
    if not quiet:
        console.print(f"[green]✓[/green] Revoked key: {name}")


@app.command("list")
def list_keys(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """List all API keys with status."""
    async def _list():
        manager = APIKeyManager()
        try:
            return await manager.list_keys()
        finally:
            await manager.close()
    
    keys = asyncio.run(_list())
    
    if json_output:
        import json
        data = [
            {
                "key_prefix": k.key_prefix,
                "name": k.name,
                "tier": k.tier.value,
                "rate_limit": k.rate_limit,
                "is_active": k.is_active,
                "days_until_expiry": k.days_until_expiry,
            }
            for k in keys
        ]
        print(json.dumps(data, indent=2))
        return
    
    table = Table(title=f"API Keys ({len(keys)} total)")
    table.add_column("Prefix")
    table.add_column("Name")
    table.add_column("Tier")
    table.add_column("Active")
    table.add_column("Rate Limit")
    table.add_column("Expires In")
    
    for key in keys:
        active_status = "[green]Yes[/green]" if key.is_active else "[red]No[/red]"
        
        days = key.days_until_expiry
        if days is None:
            expiry_status = "N/A"
        elif days <= 10:
            expiry_status = f"[red]{days}d[/red]"
        elif days <= 30:
            expiry_status = f"[yellow]{days}d[/yellow]"
        else:
            expiry_status = f"{days}d"
        
        table.add_row(
            key.key_prefix,
            key.name[:22],
            key.tier.value,
            active_status,
            f"{key.rate_limit}/min",
            expiry_status,
        )
    
    console.print(table)


@app.command()
def check() -> None:
    """Check for keys needing rotation.
    
    Lists active keys that are expiring within the warning period
    (default 80 days). Use 'rotate' to generate new keys.
    """
    async def _check():
        manager = APIKeyManager()
        try:
            return await manager.check_expiring()
        finally:
            await manager.close()
    
    expiring = asyncio.run(_check())
    
    if not expiring:
        console.print("[green]✓[/green] No keys expiring soon")
        return
    
    console.print(Panel(
        f"[yellow]⚠ {len(expiring)} key(s) expiring soon[/yellow]",
        border_style="yellow",
    ))
    
    table = Table()
    table.add_column("Prefix")
    table.add_column("Name")
    table.add_column("Expires In")
    
    for key in expiring:
        days = key.days_until_expiry or 0
        table.add_row(
            key.key_prefix,
            key.name,
            f"[red]{days} days[/red]" if days <= 10 else f"{days} days",
        )
    
    console.print(table)
    console.print("\nUse 'shai-keys rotate --key-prefix <prefix>' to rotate these keys")


@app.command()
def metrics() -> None:
    """Export Prometheus-format metrics.
    
    Output can be written to a file for node_exporter textfile collector:
    
        uv run scripts/api_keys.py metrics > /var/lib/prometheus/keys.prom
    """
    async def _metrics():
        manager = APIKeyManager()
        try:
            return await manager.get_metrics()
        finally:
            await manager.close()
    
    stats = asyncio.run(_metrics())
    
    # Prometheus text format
    print("# HELP shai_api_keys_total Total number of API keys by status")
    print("# TYPE shai_api_keys_total gauge")
    print(f'shai_api_keys_total{{status="active"}} {stats["active_keys"]}')
    print(f'shai_api_keys_total{{status="revoked"}} {stats["revoked_keys"]}')
    print()
    print("# HELP shai_api_keys_expiring Keys expiring within 10 days")
    print("# TYPE shai_api_keys_expiring gauge")
    print(f"shai_api_keys_expiring {stats['expiring_soon']}")
    print()
    print("# HELP shai_api_keys_by_tier Keys by access tier")
    print("# TYPE shai_api_keys_by_tier gauge")
    print(f'shai_api_keys_by_tier{{tier="free"}} {stats["free_tier"]}')
    print(f'shai_api_keys_by_tier{{tier="standard"}} {stats["standard_tier"]}')
    print(f'shai_api_keys_by_tier{{tier="premium"}} {stats["premium_tier"]}')


@app.command()
def cleanup(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Show what would be deleted"),
    ] = False,
) -> None:
    """Remove expired and revoked keys older than 30 days.
    
    This cleans up old key records while maintaining recent audit history.
    """
    async def _cleanup():
        manager = APIKeyManager()
        try:
            if dry_run:
                # Just count what would be deleted
                pool = await manager._get_pool()
                from datetime import timezone
                cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                count = await pool.fetchval("""
                    SELECT COUNT(*) FROM api_keys
                    WHERE (is_active = false AND revoked_at < $1)
                       OR (expires_at < $1)
                """, cutoff)
                return count
            return await manager.cleanup_expired()
        finally:
            await manager.close()
    
    count = asyncio.run(_cleanup())
    
    if dry_run:
        console.print(f"Would delete {count} key(s)")
    else:
        console.print(f"[green]✓[/green] Deleted {count} expired/revoked key(s)")


def main() -> None:
    """Entry point for the API key management CLI."""
    app()


if __name__ == "__main__":
    main()
