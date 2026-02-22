"""Pytest fixtures for agent testing and platform validation.

Root conftest providing:
- Agent unit test fixtures (mocked, no cluster required)
- Platform configuration for cluster-based tests
- HTTP client factories for API testing
"""

import os
import subprocess

import pytest
from unittest.mock import AsyncMock, Mock

import httpx

from agents.core.base import AgentConfig
from agents.specialized.research import ResearchAgent
from agents.specialized.development import DevelopmentAgent
from agents.specialized.code_review import CodeReviewAgent
from agents.specialized.testing import TestingAgent
from agents.specialized.documentation import DocumentationAgent


# =============================================================================
# Platform Configuration
# =============================================================================

class PlatformConfig:
    """Central configuration for all platform tests.

    Reads from environment variables with sensible defaults for the
    self-hosted-ai homelab cluster.
    """

    # Cluster
    KUBECONFIG = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config"))
    CLUSTER_CONTEXT = os.environ.get("CLUSTER_CONTEXT", "default")

    # Domain
    DOMAIN = os.environ.get("PLATFORM_DOMAIN", "vectorweight.com")

    # Internal service URLs (ClusterIP)
    OLLAMA_GPU_URL = os.environ.get(
        "OLLAMA_GPU_URL", "http://ollama-gpu.gpu-workloads:11434"
    )
    OLLAMA_CPU_URL = os.environ.get(
        "OLLAMA_CPU_URL", "http://ollama.ai-services:11434"
    )
    LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm.ai-services:4000")
    OPENWEBUI_URL = os.environ.get(
        "OPENWEBUI_URL", "http://open-webui.ai-services:8080"
    )
    SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://searxng.ai-services:8080")
    N8N_URL = os.environ.get("N8N_URL", "http://n8n.automation:5678")
    KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://keycloak.auth:8080")
    MCP_URL = os.environ.get("MCP_URL", "http://mcp-servers.ai-services:8000")
    GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://grafana.monitoring:80")
    PROMETHEUS_URL = os.environ.get(
        "PROMETHEUS_URL", "http://prometheus.monitoring:9090"
    )
    TEMPO_URL = os.environ.get("TEMPO_URL", "http://tempo.monitoring:3100")
    POSTGRESQL_HOST = os.environ.get(
        "POSTGRESQL_HOST", "postgresql.ai-services"
    )
    REDIS_HOST = os.environ.get("REDIS_HOST", "redis.ai-services")

    # External URLs (via Traefik ingress)
    OPENWEBUI_EXTERNAL = os.environ.get(
        "OPENWEBUI_EXTERNAL", f"https://ai.{DOMAIN}"
    )
    LITELLM_EXTERNAL = os.environ.get(
        "LITELLM_EXTERNAL", f"https://llm.{DOMAIN}"
    )
    ARGOCD_EXTERNAL = os.environ.get(
        "ARGOCD_EXTERNAL", f"https://argocd.{DOMAIN}"
    )
    N8N_EXTERNAL = os.environ.get("N8N_EXTERNAL", f"https://n8n.{DOMAIN}")
    GRAFANA_EXTERNAL = os.environ.get(
        "GRAFANA_EXTERNAL", f"https://grafana.{DOMAIN}"
    )
    SEARXNG_EXTERNAL = os.environ.get(
        "SEARXNG_EXTERNAL", f"https://search.{DOMAIN}"
    )

    # GPU worker (standalone)
    GPU_WORKER_HOST = os.environ.get("GPU_WORKER_HOST", "192.168.1.99")
    GPU_WORKER_OLLAMA = os.environ.get(
        "GPU_WORKER_OLLAMA", f"http://192.168.1.99:11434"
    )

    # Credentials (from env or sealed secrets)
    LITELLM_MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "")
    WEBUI_ADMIN_EMAIL = os.environ.get(
        "WEBUI_ADMIN_EMAIL", "admin@vectorweight.com"
    )
    WEBUI_ADMIN_PASSWORD = os.environ.get("WEBUI_ADMIN_PASSWORD", "")

    # Test settings
    TEST_TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "300"))
    TEST_MODEL = os.environ.get("TEST_MODEL", "llama3.1:8b")
    TEST_GPU_MODEL = os.environ.get("TEST_GPU_MODEL", "qwen2.5-coder:14b")
    SKIP_SLOW_TESTS = os.environ.get("SKIP_SLOW_TESTS", "false").lower() == "true"
    SKIP_GPU_TESTS = os.environ.get("SKIP_GPU_TESTS", "false").lower() == "true"

    # Expected cluster state
    EXPECTED_NODES = ["akula-prime", "homelab"]
    EXPECTED_NAMESPACES = [
        "argocd",
        "cert-manager",
        "ai-services",
        "gpu-workloads",
        "monitoring",
        "auth",
        "automation",
    ]
    CRITICAL_SERVICES = {
        "ai-services": [
            "open-webui", "litellm", "ollama", "postgresql", "redis", "searxng",
        ],
        "gpu-workloads": ["ollama-gpu"],
        "monitoring": ["prometheus", "grafana"],
        "auth": ["keycloak"],
        "automation": ["n8n"],
        "argocd": ["argocd-server"],
    }
    REQUIRED_MODELS_GPU = [
        "qwen2.5-coder:14b",
        "phi4:latest",
        "llama3.1:8b",
        "llava:13b",
        "nomic-embed-text",
    ]
    REQUIRED_MODELS_CPU = ["mistral:7b", "nomic-embed-text"]

    EXTERNAL_ENDPOINTS = {
        "Open WebUI": f"https://ai.{DOMAIN}",
        "LiteLLM": f"https://llm.{DOMAIN}",
        "ArgoCD": f"https://argocd.{DOMAIN}",
        "n8n": f"https://n8n.{DOMAIN}",
        "Grafana": f"https://grafana.{DOMAIN}",
        "SearXNG": f"https://search.{DOMAIN}",
    }


@pytest.fixture(scope="session")
def platform_config():
    """Provide platform configuration for all tests."""
    return PlatformConfig()


@pytest.fixture(scope="session")
def kubectl_available():
    """Check if kubectl is available and configured."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def kubectl_get_json(resource, namespace=None, all_namespaces=False):
    """Run kubectl get and return parsed JSON output.

    Args:
        resource: K8s resource type (e.g., 'pods', 'nodes', 'deployments')
        namespace: Target namespace (optional)
        all_namespaces: If True, query across all namespaces

    Returns:
        Parsed JSON dict from kubectl output
    """
    cmd = ["kubectl", "get", resource, "-o", "json"]
    if all_namespaces:
        cmd.append("-A")
    elif namespace:
        cmd.extend(["-n", namespace])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"kubectl failed: {result.stderr}")

    import json
    return json.loads(result.stdout)


@pytest.fixture(scope="session")
def kubectl():
    """Provide kubectl helper function."""
    return kubectl_get_json


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def http_client():
    """Create a shared httpx client for API tests.

    Uses verify=False for self-signed certificates in the homelab.
    """
    client = httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=False,
        follow_redirects=True,
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def async_http_client():
    """Create a shared async httpx client for API tests."""
    import asyncio

    client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=False,
        follow_redirects=True,
    )
    yield client
    asyncio.get_event_loop().run_until_complete(client.aclose())


# =============================================================================
# Agent Unit Test Fixtures (no cluster required)
# =============================================================================

@pytest.fixture
def agent_config():
    """Create a default agent configuration for testing."""
    return AgentConfig(
        name="test-agent",
        agent_type="test",
        model="qwen2.5-coder:14b",
        ollama_url="http://localhost:11434",
        temperature=0.7,
        timeout_seconds=60,
    )


@pytest.fixture
def research_agent(agent_config):
    """Create a Research agent instance."""
    return ResearchAgent(agent_config)


@pytest.fixture
def development_agent(agent_config):
    """Create a Development agent instance."""
    return DevelopmentAgent(agent_config)


@pytest.fixture
def code_review_agent(agent_config):
    """Create a Code Review agent instance."""
    return CodeReviewAgent(agent_config)


@pytest.fixture
def testing_agent(agent_config):
    """Create a Testing agent instance."""
    return TestingAgent(agent_config)


@pytest.fixture
def documentation_agent(agent_config):
    """Create a Documentation agent instance."""
    return DocumentationAgent(agent_config)


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "response": "This is a mock response from Ollama",
        "created_at": "2026-01-10T12:00:00Z",
        "model": "qwen2.5-coder:14b",
        "done": True,
    }


@pytest.fixture
def mock_httpx_client(mock_ollama_response):
    """Mock httpx AsyncClient for API calls."""
    mock_response = Mock()
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    return mock_client


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''


@pytest.fixture
def sample_rust_code():
    """Sample Rust code for testing."""
    return '''fn fibonacci(n: u32) -> u32 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}
'''
