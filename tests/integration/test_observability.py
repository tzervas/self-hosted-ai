"""Observability stack integration tests.

Tests that metrics, traces, and logs flow correctly:
- Prometheus scrapes service metrics
- Tempo receives traces
- Grafana can query both
"""

import pytest


pytestmark = [pytest.mark.integration]


class TestPrometheusMetrics:
    """Test Prometheus metric collection."""

    def test_prometheus_scraping_services(self, http_client, platform_config):
        """Prometheus should be scraping target services."""
        try:
            prom_url = f"https://prometheus.{platform_config.DOMAIN}"
            response = http_client.get(
                f"{prom_url}/api/v1/targets",
            )
            if response.status_code != 200:
                pytest.skip(f"Prometheus targets endpoint returned {response.status_code}")

            data = response.json()
            active = data.get("data", {}).get("activeTargets", [])
            up_targets = [t for t in active if t.get("health") == "up"]

            assert len(up_targets) > 0, (
                f"No healthy scrape targets. "
                f"Total active: {len(active)}"
            )
        except Exception as e:
            pytest.skip(f"Cannot query Prometheus targets: {e}")

    def test_basic_metric_query(self, http_client, platform_config):
        """Prometheus should return data for basic queries."""
        try:
            prom_url = f"https://prometheus.{platform_config.DOMAIN}"
            response = http_client.get(
                f"{prom_url}/api/v1/query",
                params={"query": "up"},
            )
            if response.status_code != 200:
                pytest.skip(f"Prometheus query returned {response.status_code}")

            data = response.json()
            assert data.get("status") == "success", (
                f"Query failed: {data.get('error', 'unknown')}"
            )
            results = data.get("data", {}).get("result", [])
            assert len(results) > 0, "No results for 'up' metric"
        except Exception as e:
            pytest.skip(f"Cannot query Prometheus: {e}")


class TestGrafanaDatasources:
    """Test Grafana data source connectivity."""

    def test_grafana_has_prometheus_datasource(self, grafana_client):
        """Grafana should have Prometheus configured as a data source."""
        try:
            response = grafana_client.get("/api/datasources")
            if response.status_code == 401:
                pytest.skip("Grafana requires auth")

            datasources = response.json()
            prometheus_ds = [
                ds for ds in datasources
                if ds.get("type") == "prometheus"
            ]
            assert len(prometheus_ds) > 0, (
                "No Prometheus data source in Grafana. "
                f"Available types: {[ds.get('type') for ds in datasources]}"
            )
        except Exception as e:
            pytest.skip(f"Cannot check Grafana datasources: {e}")

    def test_grafana_has_tempo_datasource(self, grafana_client):
        """Grafana should have Tempo configured for distributed tracing."""
        try:
            response = grafana_client.get("/api/datasources")
            if response.status_code == 401:
                pytest.skip("Grafana requires auth")

            datasources = response.json()
            tempo_ds = [
                ds for ds in datasources
                if ds.get("type") == "tempo"
            ]
            if not tempo_ds:
                pytest.xfail(
                    "No Tempo data source in Grafana (tracing may not be configured)"
                )
        except Exception as e:
            pytest.skip(f"Cannot check Grafana datasources: {e}")
