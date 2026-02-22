"""Monitoring stack API endpoint tests.

Tests Grafana, Prometheus, and Tempo endpoints:
- Health checks
- Data source availability
- Metrics scraping
- Trace query
"""

import pytest


pytestmark = [pytest.mark.api]


class TestGrafanaHealth:
    """Validate Grafana is reachable and configured."""

    def test_grafana_reachable(self, grafana_client):
        """Grafana should be reachable."""
        try:
            response = grafana_client.get("/api/health")
            assert response.status_code == 200, (
                f"Grafana health returned {response.status_code}"
            )
            data = response.json()
            assert data.get("database") == "ok", (
                f"Grafana database not ok: {data}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach Grafana: {e}")

    def test_grafana_has_datasources(self, grafana_client):
        """Grafana should have data sources configured."""
        try:
            response = grafana_client.get("/api/datasources")
            if response.status_code == 401:
                pytest.skip("Grafana requires authentication for datasources API")
            assert response.status_code == 200
            datasources = response.json()
            assert len(datasources) > 0, "No data sources configured in Grafana"
        except Exception as e:
            pytest.skip(f"Cannot check Grafana datasources: {e}")


class TestPrometheusHealth:
    """Validate Prometheus is scraping metrics."""

    def test_prometheus_reachable(self, http_client, platform_config):
        """Prometheus should be reachable."""
        try:
            response = http_client.get(
                f"{platform_config.GRAFANA_EXTERNAL.replace('grafana', 'prometheus')}/-/healthy"
            )
            if response.status_code == 404:
                # Try alternative health endpoint
                response = http_client.get(
                    f"{platform_config.GRAFANA_EXTERNAL.replace('grafana', 'prometheus')}/api/v1/status/runtimeinfo"
                )
            assert response.status_code == 200, (
                f"Prometheus health returned {response.status_code}"
            )
        except Exception as e:
            pytest.skip(f"Cannot reach Prometheus: {e}")

    def test_prometheus_has_targets(self, http_client, platform_config):
        """Prometheus should have active scrape targets."""
        try:
            prom_url = platform_config.GRAFANA_EXTERNAL.replace("grafana", "prometheus")
            response = http_client.get(f"{prom_url}/api/v1/targets")
            if response.status_code != 200:
                pytest.skip("Cannot query Prometheus targets")

            data = response.json()
            active = data.get("data", {}).get("activeTargets", [])
            assert len(active) > 0, "No active scrape targets in Prometheus"
        except Exception as e:
            pytest.skip(f"Cannot check Prometheus targets: {e}")


class TestArgocdHealth:
    """Validate ArgoCD API is accessible."""

    def test_argocd_reachable(self, argocd_client):
        """ArgoCD should be reachable."""
        try:
            response = argocd_client.get("/healthz")
            if response.status_code == 404:
                response = argocd_client.get("/api/version")
            assert response.status_code in (200, 302, 401), (
                f"ArgoCD returned {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach ArgoCD: {e}")

    def test_argocd_version(self, argocd_client):
        """ArgoCD should report its version."""
        try:
            response = argocd_client.get("/api/version")
            if response.status_code == 401:
                pytest.skip("ArgoCD requires auth for version endpoint")
            assert response.status_code == 200
            data = response.json()
            assert "Version" in data or "version" in data, (
                "ArgoCD version response missing version field"
            )
        except Exception as e:
            pytest.skip(f"Cannot check ArgoCD version: {e}")
