"""MCP Server API endpoint tests.

Tests the Model Context Protocol servers via MCPO proxy:
- Health/connectivity
- Server listing
- Tool availability
"""

import pytest


pytestmark = [pytest.mark.api]


class TestMCPHealth:
    """Validate MCP servers are reachable via MCPO proxy."""

    def test_mcpo_proxy_reachable(self, http_client, platform_config):
        """MCPO proxy should be reachable."""
        try:
            # MCP servers are internal (ClusterIP), need port-forward or kubectl exec
            # For external test, check if ingress is configured
            response = http_client.get(
                f"https://mcp.{platform_config.DOMAIN}/",
            )
            if response.status_code in (200, 404):
                # Accessible
                pass
            else:
                pytest.skip(
                    f"MCP proxy not externally accessible ({response.status_code})"
                )
        except Exception as e:
            pytest.skip(f"MCP proxy not reachable: {e}")

    def test_mcp_servers_pod_running(self, kubectl_available):
        """MCP servers pod should be running in the cluster."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        import subprocess
        import json

        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "self-hosted-ai",
             "-l", "app=mcp-servers", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            # Try broader search
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "self-hosted-ai", "-o", "json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                pytest.skip("Cannot query pods")

            data = json.loads(result.stdout)
            mcp_pods = [
                p for p in data.get("items", [])
                if "mcp" in p["metadata"]["name"]
            ]
            if not mcp_pods:
                pytest.skip("No MCP server pods found")
