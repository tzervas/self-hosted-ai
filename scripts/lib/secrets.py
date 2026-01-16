"""
Secrets Manager
===============
Secure credential generation, rotation, and documentation.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Template
from rich.console import Console

from lib.config import Settings, get_settings

console = Console()


@dataclass
class ServiceCredential:
    """Represents credentials for a service."""

    service: str
    namespace: str
    secret_name: str
    keys: dict[str, str] = field(default_factory=dict)
    urls: list[str] = field(default_factory=list)
    notes: str = ""


def generate_password(length: int = 32, special: bool = True) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits
    if special:
        alphabet += "!@#$%^&*"
    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    if special:
        password.append(secrets.choice("!@#$%^&*"))
    # Fill rest randomly
    password.extend(secrets.choice(alphabet) for _ in range(length - len(password)))
    # Shuffle
    result = list(password)
    secrets.SystemRandom().shuffle(result)
    return "".join(result)


def generate_api_key(prefix: str = "sk") -> str:
    """Generate an API key with prefix."""
    return f"{prefix}-{secrets.token_urlsafe(32)}"


def generate_encryption_key() -> str:
    """Generate a base64 encryption key."""
    import base64
    return base64.b64encode(secrets.token_bytes(32)).decode()


class SecretsManager:
    """Manage secrets for all services."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.credentials: list[ServiceCredential] = []

    def generate_all(self) -> list[ServiceCredential]:
        """Generate credentials for all services."""
        self.credentials = [
            self._generate_argocd(),
            self._generate_openwebui(),
            self._generate_litellm(),
            self._generate_postgresql(),
            self._generate_redis(),
            self._generate_n8n(),
            self._generate_grafana(),
            self._generate_searxng(),
            self._generate_gitlab(),
        ]
        return self.credentials

    def _generate_argocd(self) -> ServiceCredential:
        return ServiceCredential(
            service="ArgoCD",
            namespace="argocd",
            secret_name="argocd-initial-admin-secret",
            keys={
                "username": "admin",
                "password": generate_password(24),
            },
            urls=[f"https://argocd.{self.settings.domain}"],
            notes="GitOps deployment dashboard. Password auto-generated on first install.",
        )

    def _generate_openwebui(self) -> ServiceCredential:
        return ServiceCredential(
            service="Open WebUI",
            namespace="self-hosted-ai",
            secret_name="webui-secret",
            keys={
                "admin-email": f"admin@{self.settings.domain}",
                "admin-password": generate_password(24),
                "secret-key": generate_api_key("webui"),
            },
            urls=[f"https://ai.{self.settings.domain}"],
            notes="AI chat interface. First signup becomes admin.",
        )

    def _generate_litellm(self) -> ServiceCredential:
        return ServiceCredential(
            service="LiteLLM",
            namespace="self-hosted-ai",
            secret_name="litellm-secret",
            keys={
                "master-key": generate_api_key("llm"),
                "database-url": "",  # Set after PostgreSQL
            },
            urls=[f"https://llm.{self.settings.domain}"],
            notes="OpenAI-compatible API proxy. Use master-key for admin operations.",
        )

    def _generate_postgresql(self) -> ServiceCredential:
        pg_password = generate_password(32, special=False)  # No special chars for URLs
        return ServiceCredential(
            service="PostgreSQL",
            namespace="self-hosted-ai",
            secret_name="postgresql-secret",
            keys={
                "postgres-password": pg_password,
                "password": pg_password,
                "database": "litellm",
                "username": "litellm",
            },
            urls=["postgresql://litellm:PASSWORD@postgresql:5432/litellm"],
            notes="Internal database. Not exposed externally.",
        )

    def _generate_redis(self) -> ServiceCredential:
        return ServiceCredential(
            service="Redis",
            namespace="self-hosted-ai",
            secret_name="redis-secret",
            keys={
                "redis-password": generate_password(32, special=False),
            },
            urls=["redis://:PASSWORD@redis-master:6379"],
            notes="Internal cache. Not exposed externally.",
        )

    def _generate_n8n(self) -> ServiceCredential:
        return ServiceCredential(
            service="n8n",
            namespace="automation",
            secret_name="n8n-secret",
            keys={
                "N8N_ENCRYPTION_KEY": generate_encryption_key(),
                "N8N_BASIC_AUTH_USER": "admin",
                "N8N_BASIC_AUTH_PASSWORD": generate_password(24),
            },
            urls=[f"https://n8n.{self.settings.domain}"],
            notes="Workflow automation. API access requires API key from settings.",
        )

    def _generate_grafana(self) -> ServiceCredential:
        return ServiceCredential(
            service="Grafana",
            namespace="monitoring",
            secret_name="grafana-secret",
            keys={
                "admin-user": "admin",
                "admin-password": generate_password(24),
            },
            urls=[f"https://grafana.{self.settings.domain}"],
            notes="Monitoring dashboards. Pre-configured with Prometheus datasource.",
        )

    def _generate_searxng(self) -> ServiceCredential:
        return ServiceCredential(
            service="SearXNG",
            namespace="self-hosted-ai",
            secret_name="searxng-secret",
            keys={
                "secret-key": generate_api_key("searx"),
            },
            urls=[f"https://search.{self.settings.domain}"],
            notes="Privacy-focused search. No authentication required.",
        )

    def _generate_gitlab(self) -> ServiceCredential:
        return ServiceCredential(
            service="GitLab",
            namespace="gitlab",
            secret_name="gitlab-initial-root-password",
            keys={
                "username": "root",
                "password": generate_password(24),
            },
            urls=[f"https://git.{self.settings.domain}"],
            notes="Self-hosted Git. Password set on first boot.",
        )

    def update_litellm_database_url(self) -> None:
        """Update LiteLLM database URL with PostgreSQL password."""
        pg_cred = next((c for c in self.credentials if c.service == "PostgreSQL"), None)
        llm_cred = next((c for c in self.credentials if c.service == "LiteLLM"), None)
        if pg_cred and llm_cred:
            pg_pass = pg_cred.keys.get("password", "")
            llm_cred.keys["database-url"] = (
                f"postgresql://litellm:{pg_pass}@postgresql:5432/litellm"
            )

    def export_to_yaml(self, path: Path | None = None) -> str:
        """Export credentials to YAML format."""
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "domain": self.settings.domain,
            "services": {},
        }
        for cred in self.credentials:
            data["services"][cred.service.lower().replace(" ", "_")] = {
                "namespace": cred.namespace,
                "secret_name": cred.secret_name,
                "urls": cred.urls,
                "credentials": cred.keys,
                "notes": cred.notes,
            }

        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
        if path:
            path.write_text(yaml_str)
        return yaml_str

    def export_to_markdown(self, path: Path | None = None) -> str:
        """Export credentials to agent-discoverable Markdown with YAML."""
        template = Template(CREDENTIALS_TEMPLATE)
        content = template.render(
            generated_at=datetime.now(timezone.utc).isoformat(),
            domain=self.settings.domain,
            cluster_ip=self.settings.cluster_ip,
            gpu_worker_ip=self.settings.gpu_worker_ip,
            credentials=self.credentials,
        )
        if path:
            path.write_text(content)
        return content


CREDENTIALS_TEMPLATE = '''---
# =============================================================================
# ADMIN_CREDENTIALS.local.md
# =============================================================================
# Self-Hosted AI Platform - Administrative Credentials
# Generated: {{ generated_at }}
# Domain: {{ domain }}
#
# ⚠️  SECURITY NOTICE: This file contains sensitive credentials.
#     - DO NOT commit to version control
#     - Store securely (encrypted backup recommended)
#     - Rotate credentials periodically
#
# 🤖 AGENT DISCOVERY: This document is structured for AI agent consumption.
#    Parse the YAML blocks below for programmatic access.
# =============================================================================

# Cluster Information

```yaml
cluster:
  domain: {{ domain }}
  control_plane_ip: {{ cluster_ip }}
  gpu_worker_ip: {{ gpu_worker_ip }}
  generated_at: {{ generated_at }}
```

---

# Service Credentials

{% for cred in credentials %}
## {{ cred.service }}

**Namespace:** `{{ cred.namespace }}`
**Secret Name:** `{{ cred.secret_name }}`
**URLs:**
{% for url in cred.urls %}
- {{ url }}
{% endfor %}

{% if cred.notes %}
> {{ cred.notes }}
{% endif %}

```yaml
{{ cred.service.lower().replace(" ", "_") }}:
  namespace: {{ cred.namespace }}
  secret_name: {{ cred.secret_name }}
  urls:
{% for url in cred.urls %}
    - "{{ url }}"
{% endfor %}
  credentials:
{% for key, value in cred.keys.items() %}
    {{ key }}: "{{ value }}"
{% endfor %}
```

---

{% endfor %}
# Quick Access Commands

## Connect to Services

```bash
# ArgoCD CLI login
argocd login argocd.{{ domain }} --username admin --password '<argocd-password>'

# PostgreSQL
kubectl exec -it -n self-hosted-ai deploy/postgresql -- psql -U litellm

# Redis
kubectl exec -it -n self-hosted-ai deploy/redis-master -- redis-cli -a '<redis-password>'

# Port-forward for local access
kubectl port-forward -n self-hosted-ai svc/postgresql 5432:5432
kubectl port-forward -n monitoring svc/grafana 3000:80
```

## Rotate Secrets

```bash
# Regenerate all secrets
uv run shai-secrets rotate --all

# Rotate specific service
uv run shai-secrets rotate --service litellm
```

## Backup Credentials

```bash
# Encrypt and backup
gpg --symmetric --cipher-algo AES256 ADMIN_CREDENTIALS.local.md

# Restore
gpg --decrypt ADMIN_CREDENTIALS.local.md.gpg > ADMIN_CREDENTIALS.local.md
```

---

# Agent Discovery Index

```yaml
# Machine-readable service index for AI agents
services_index:
{% for cred in credentials %}
  - name: {{ cred.service }}
    type: {{ cred.service.lower().replace(" ", "-") }}
    namespace: {{ cred.namespace }}
    urls:
{% for url in cred.urls %}
      - {{ url }}
{% endfor %}
    auth_type: {% if "api" in cred.keys or "master-key" in cred.keys %}api_key{% elif "password" in cred.keys or "admin-password" in cred.keys %}password{% else %}none{% endif %}

{% endfor %}
```

---

*Document generated by `shai-secrets` - Self-Hosted AI Platform*
'''
