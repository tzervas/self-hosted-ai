"""
Configuration Management
========================
Centralized settings with environment variable support and validation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable binding."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        env_prefix="SHAI_",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------
    # Cluster Configuration
    # -------------------------
    kubeconfig: Path | None = Field(
        default=None,
        description="Path to kubeconfig file (uses default if not set)",
    )
    context: str | None = Field(
        default=None,
        description="Kubernetes context to use",
    )
    namespace_default: str = Field(
        default="self-hosted-ai",
        description="Default namespace for operations",
    )

    # -------------------------
    # Domain & Networking
    # -------------------------
    domain: str = Field(
        default="vectorweight.com",
        description="Primary domain for services",
    )
    cluster_ip: str = Field(
        default="192.168.1.170",
        description="Main cluster node IP",
    )
    gpu_worker_ip: str = Field(
        default="192.168.1.99",
        description="GPU worker node IP",
    )
    traefik_https_port: int = Field(
        default=443,
        description="Traefik HTTPS NodePort",
    )

    # -------------------------
    # Service Endpoints
    # -------------------------
    argocd_url: str = Field(default="https://argocd.vectorweight.com")
    openwebui_url: str = Field(default="https://ai.vectorweight.com")
    litellm_url: str = Field(default="https://llm.vectorweight.com")
    n8n_url: str = Field(default="https://n8n.vectorweight.com")
    grafana_url: str = Field(default="https://grafana.vectorweight.com")
    prometheus_url: str = Field(default="https://prometheus.vectorweight.com")
    searxng_url: str = Field(default="https://search.vectorweight.com")
    gitlab_url: str = Field(default="https://git.vectorweight.com")

    # -------------------------
    # Paths
    # -------------------------
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Root directory of the project",
    )
    secrets_dir: Path = Field(
        default_factory=lambda: Path.home() / "Documents" / ".secret",
        description="Directory for sensitive files",
    )
    backup_dir: Path = Field(
        default_factory=lambda: Path.home() / "backups" / "self-hosted-ai",
        description="Directory for backups",
    )

    # -------------------------
    # Behavior Flags
    # -------------------------
    dry_run: bool = Field(
        default=False,
        description="Preview changes without applying",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    # -------------------------
    # Secrets Configuration
    # -------------------------
    secrets_mode: Literal["generate", "rotate", "from-env"] = Field(
        default="generate",
        description="How to handle secrets",
    )
    sealed_secrets_cert: Path | None = Field(
        default=None,
        description="Path to SealedSecrets public cert",
    )

    # -------------------------
    # Validators
    # -------------------------
    @field_validator("kubeconfig", mode="before")
    @classmethod
    def expand_kubeconfig_path(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        return Path(v).expanduser().resolve()

    @field_validator("project_root", "secrets_dir", "backup_dir", mode="before")
    @classmethod
    def expand_paths(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    # -------------------------
    # Computed Properties
    # -------------------------
    @property
    def helm_dir(self) -> Path:
        return self.project_root / "helm"

    @property
    def argocd_dir(self) -> Path:
        return self.project_root / "argocd"

    @property
    def config_dir(self) -> Path:
        return self.project_root / "config"

    @property
    def models_manifest(self) -> Path:
        return self.config_dir / "models-manifest.yml"

    @property
    def credentials_doc(self) -> Path:
        return self.project_root / "ADMIN_CREDENTIALS.local.md"

    def service_url(self, service: str) -> str:
        """Get URL for a service by name."""
        urls = {
            "argocd": self.argocd_url,
            "openwebui": self.openwebui_url,
            "open-webui": self.openwebui_url,
            "litellm": self.litellm_url,
            "n8n": self.n8n_url,
            "grafana": self.grafana_url,
            "prometheus": self.prometheus_url,
            "searxng": self.searxng_url,
            "gitlab": self.gitlab_url,
        }
        return urls.get(service.lower(), f"https://{service}.{self.domain}")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
