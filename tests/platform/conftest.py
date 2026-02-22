"""Platform test fixtures requiring cluster access."""

import json
import subprocess

import pytest


@pytest.fixture(scope="module")
def cluster_nodes(kubectl_available, kubectl):
    """Get cluster node information."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    return kubectl("nodes")


@pytest.fixture(scope="module")
def cluster_pods(kubectl_available, kubectl):
    """Get all pods across namespaces."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    return kubectl("pods", all_namespaces=True)


@pytest.fixture(scope="module")
def cluster_namespaces(kubectl_available, kubectl):
    """Get all namespaces."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    return kubectl("namespaces")


@pytest.fixture(scope="module")
def argocd_apps(kubectl_available):
    """Get ArgoCD application statuses."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    try:
        result = subprocess.run(
            ["kubectl", "get", "applications", "-n", "argocd", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            pytest.skip(f"Cannot get ArgoCD apps: {result.stderr}")
        return json.loads(result.stdout)
    except Exception as e:
        pytest.skip(f"ArgoCD query failed: {e}")


@pytest.fixture(scope="module")
def cluster_certificates(kubectl_available):
    """Get certificate resources."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    try:
        result = subprocess.run(
            ["kubectl", "get", "certificates", "-A", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"items": []}
        return json.loads(result.stdout)
    except Exception:
        return {"items": []}


@pytest.fixture(scope="module")
def cluster_secrets(kubectl_available, kubectl):
    """Get all secrets (names only, not data)."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    result = subprocess.run(
        ["kubectl", "get", "secrets", "-A",
         "-o", "jsonpath={range .items[*]}{.metadata.namespace}/{.metadata.name}{'\\n'}{end}"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        pytest.skip("Cannot list secrets")
    return result.stdout.strip().split("\n")


@pytest.fixture(scope="module")
def resource_quotas(kubectl_available):
    """Get resource quotas across namespaces."""
    if not kubectl_available:
        pytest.skip("kubectl not available or cluster not reachable")
    try:
        result = subprocess.run(
            ["kubectl", "get", "resourcequotas", "-A", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"items": []}
        return json.loads(result.stdout)
    except Exception:
        return {"items": []}
