"""API test fixtures.

Provides pre-configured HTTP clients for each service endpoint.
Tests in this module require cluster access (services must be reachable).
"""

import os
import subprocess

import pytest
import httpx


def _port_forward_or_skip(namespace, service, local_port, remote_port):
    """Attempt to set up port-forward; skip if not possible."""
    # For CI/CD, services might be directly reachable via ClusterIP
    # For local dev, we would need port-forwarding
    pass


@pytest.fixture(scope="module")
def ollama_gpu_client(platform_config):
    """HTTP client targeting Ollama GPU service."""
    client = httpx.Client(
        base_url=platform_config.GPU_WORKER_OLLAMA,
        timeout=httpx.Timeout(60.0, connect=10.0),
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def litellm_client(platform_config):
    """HTTP client targeting LiteLLM proxy."""
    headers = {}
    if platform_config.LITELLM_MASTER_KEY:
        headers["Authorization"] = f"Bearer {platform_config.LITELLM_MASTER_KEY}"
    client = httpx.Client(
        base_url=platform_config.LITELLM_EXTERNAL,
        timeout=httpx.Timeout(60.0, connect=10.0),
        headers=headers,
        verify=False,
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def openwebui_client(platform_config):
    """HTTP client targeting Open WebUI."""
    client = httpx.Client(
        base_url=platform_config.OPENWEBUI_EXTERNAL,
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=False,
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def searxng_client(platform_config):
    """HTTP client targeting SearXNG."""
    client = httpx.Client(
        base_url=platform_config.SEARXNG_EXTERNAL,
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=False,
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def grafana_client(platform_config):
    """HTTP client targeting Grafana."""
    client = httpx.Client(
        base_url=platform_config.GRAFANA_EXTERNAL,
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=False,
    )
    yield client
    client.close()


@pytest.fixture(scope="module")
def argocd_client(platform_config):
    """HTTP client targeting ArgoCD."""
    client = httpx.Client(
        base_url=platform_config.ARGOCD_EXTERNAL,
        timeout=httpx.Timeout(30.0, connect=10.0),
        verify=False,
    )
    yield client
    client.close()
