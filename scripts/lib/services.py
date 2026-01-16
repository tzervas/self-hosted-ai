"""
Service API Clients
===================
Async HTTP clients for interacting with deployed services.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from rich.console import Console

from lib.config import Settings, get_settings

console = Console()


class ServiceClient:
    """Base async HTTP client for service APIs."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = False,  # Self-signed certs
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ServiceClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")
        return self._client

    async def health_check(self) -> dict[str, Any]:
        """Check service health."""
        try:
            response = await self.client.get("/health")
            return {"status": "healthy", "code": response.status_code}
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}


class OpenWebUIClient(ServiceClient):
    """Client for Open WebUI API."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        super().__init__(s.openwebui_url)
        self.api_key: str | None = None

    def set_api_key(self, key: str) -> None:
        self.api_key = key

    @property
    def headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def health_check(self) -> dict[str, Any]:
        """Check Open WebUI health."""
        try:
            response = await self.client.get("/health")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def create_admin_user(
        self,
        email: str,
        password: str,
        name: str = "Administrator",
    ) -> dict[str, Any]:
        """Create admin user (first signup becomes admin)."""
        try:
            response = await self.client.post(
                "/api/v1/auths/signup",
                json={"email": email, "password": password, "name": name},
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                data = response.json()
                self.api_key = data.get("token")
                return {"success": True, "user": data}
            return {"success": False, "error": response.text, "code": response.status_code}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}

    async def signin(self, email: str, password: str) -> dict[str, Any]:
        """Sign in and get API token."""
        try:
            response = await self.client.post(
                "/api/v1/auths/signin",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                data = response.json()
                self.api_key = data.get("token")
                return {"success": True, "token": data.get("token")}
            return {"success": False, "error": response.text}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}

    async def get_config(self) -> dict[str, Any]:
        """Get current configuration."""
        response = await self.client.get("/api/config", headers=self.headers)
        return response.json()

    async def update_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update configuration."""
        response = await self.client.post(
            "/api/config",
            json=config,
            headers=self.headers,
        )
        return response.json()

    async def get_models(self) -> list[dict[str, Any]]:
        """List available models."""
        response = await self.client.get("/api/models", headers=self.headers)
        return response.json()

    async def add_ollama_connection(self, url: str, name: str | None = None) -> dict[str, Any]:
        """Add Ollama connection."""
        response = await self.client.post(
            "/api/v1/configs/ollama",
            json={"url": url, "name": name},
            headers=self.headers,
        )
        return response.json()


class LiteLLMClient(ServiceClient):
    """Client for LiteLLM Proxy API."""

    def __init__(self, settings: Settings | None = None, master_key: str | None = None) -> None:
        s = settings or get_settings()
        super().__init__(s.litellm_url)
        self.master_key = master_key

    @property
    def headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.master_key:
            h["Authorization"] = f"Bearer {self.master_key}"
        return h

    async def health_check(self) -> dict[str, Any]:
        """Check LiteLLM health."""
        try:
            response = await self.client.get("/health")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        response = await self.client.get("/v1/models", headers=self.headers)
        data = response.json()
        return data.get("data", [])

    async def get_model_info(self) -> dict[str, Any]:
        """Get model configuration info."""
        response = await self.client.get("/model/info", headers=self.headers)
        return response.json()

    async def test_completion(self, model: str = "gpt-4", prompt: str = "Say hello") -> dict[str, Any]:
        """Test a completion request."""
        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                },
                headers=self.headers,
            )
            return {"success": True, "response": response.json()}
        except httpx.RequestError as e:
            return {"success": False, "error": str(e)}


class N8NClient(ServiceClient):
    """Client for n8n API."""

    def __init__(self, settings: Settings | None = None, api_key: str | None = None) -> None:
        s = settings or get_settings()
        super().__init__(s.n8n_url)
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-N8N-API-KEY"] = self.api_key
        return h

    async def health_check(self) -> dict[str, Any]:
        """Check n8n health."""
        try:
            response = await self.client.get("/healthz")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_workflows(self) -> list[dict[str, Any]]:
        """List all workflows."""
        response = await self.client.get("/api/v1/workflows", headers=self.headers)
        data = response.json()
        return data.get("data", [])

    async def import_workflow(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Import a workflow."""
        response = await self.client.post(
            "/api/v1/workflows",
            json=workflow,
            headers=self.headers,
        )
        return response.json()

    async def activate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Activate a workflow."""
        response = await self.client.patch(
            f"/api/v1/workflows/{workflow_id}",
            json={"active": True},
            headers=self.headers,
        )
        return response.json()


class GrafanaClient(ServiceClient):
    """Client for Grafana API."""

    def __init__(
        self,
        settings: Settings | None = None,
        admin_user: str = "admin",
        admin_password: str | None = None,
    ) -> None:
        s = settings or get_settings()
        super().__init__(s.grafana_url)
        self.admin_user = admin_user
        self.admin_password = admin_password

    @property
    def auth(self) -> tuple[str, str] | None:
        if self.admin_password:
            return (self.admin_user, self.admin_password)
        return None

    async def health_check(self) -> dict[str, Any]:
        """Check Grafana health."""
        try:
            response = await self.client.get("/api/health")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_datasources(self) -> list[dict[str, Any]]:
        """List configured datasources."""
        response = await self.client.get("/api/datasources", auth=self.auth)
        return response.json()

    async def add_datasource(self, datasource: dict[str, Any]) -> dict[str, Any]:
        """Add a datasource."""
        response = await self.client.post(
            "/api/datasources",
            json=datasource,
            auth=self.auth,
        )
        return response.json()

    async def list_dashboards(self) -> list[dict[str, Any]]:
        """List all dashboards."""
        response = await self.client.get("/api/search", auth=self.auth)
        return response.json()


class OllamaClient(ServiceClient):
    """Client for Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        super().__init__(base_url)

    async def health_check(self) -> dict[str, Any]:
        """Check Ollama health."""
        try:
            response = await self.client.get("/")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_models(self) -> list[dict[str, Any]]:
        """List local models."""
        response = await self.client.get("/api/tags")
        data = response.json()
        return data.get("models", [])

    async def pull_model(self, name: str) -> dict[str, Any]:
        """Pull a model."""
        response = await self.client.post(
            "/api/pull",
            json={"name": name},
            timeout=600.0,  # Models can take a while
        )
        return {"success": response.status_code == 200}

    async def model_exists(self, name: str) -> bool:
        """Check if a model exists locally."""
        models = await self.list_models()
        return any(m.get("name", "").startswith(name) for m in models)


class SearXNGClient(ServiceClient):
    """Client for SearXNG API."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        super().__init__(s.searxng_url)

    async def health_check(self) -> dict[str, Any]:
        """Check SearXNG health."""
        try:
            response = await self.client.get("/healthz")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def search(self, query: str, categories: str = "general") -> dict[str, Any]:
        """Perform a search."""
        response = await self.client.get(
            "/search",
            params={"q": query, "categories": categories, "format": "json"},
        )
        return response.json()


class GitLabClient(ServiceClient):
    """Client for GitLab API."""

    def __init__(self, settings: Settings | None = None, token: str | None = None) -> None:
        s = settings or get_settings()
        super().__init__(s.gitlab_url)
        self.token = token

    @property
    def headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["PRIVATE-TOKEN"] = self.token
        return h

    async def health_check(self) -> dict[str, Any]:
        """Check GitLab health."""
        try:
            response = await self.client.get("/-/health")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "code": response.status_code,
            }
        except httpx.RequestError as e:
            return {"status": "unhealthy", "error": str(e)}

    async def list_projects(self) -> list[dict[str, Any]]:
        """List accessible projects."""
        response = await self.client.get("/api/v4/projects", headers=self.headers)
        return response.json()

    async def get_version(self) -> dict[str, Any]:
        """Get GitLab version."""
        response = await self.client.get("/api/v4/version", headers=self.headers)
        return response.json()
