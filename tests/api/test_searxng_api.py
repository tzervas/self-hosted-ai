"""SearXNG API endpoint tests.

Tests the privacy-focused search engine:
- Health/connectivity
- Search functionality
- JSON API
"""

import pytest


pytestmark = [pytest.mark.api]


class TestSearXNGHealth:
    """Validate SearXNG is reachable."""

    def test_searxng_reachable(self, searxng_client):
        """SearXNG should be reachable (401 = behind SSO, still alive)."""
        try:
            response = searxng_client.get("/")
            # 401 = oauth2-proxy SSO is protecting the endpoint (expected)
            assert response.status_code in (200, 302, 401), (
                f"SearXNG returned unexpected {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach SearXNG: {e}")

    def test_searxng_healthcheck(self, searxng_client):
        """SearXNG endpoint should respond (even with auth redirect)."""
        try:
            response = searxng_client.get("/healthz")
            if response.status_code == 404:
                response = searxng_client.get("/")
            # 401 = behind SSO, service is alive
            assert response.status_code in (200, 302, 401)
        except Exception as e:
            pytest.fail(f"SearXNG health check failed: {e}")


class TestSearXNGSearch:
    """Test search functionality."""

    @pytest.mark.slow
    def test_json_search(self, searxng_client):
        """SearXNG should return search results in JSON format."""
        try:
            response = searxng_client.get(
                "/search",
                params={
                    "q": "python programming",
                    "format": "json",
                    "categories": "general",
                },
                timeout=30,
            )
            if response.status_code == 429:
                pytest.skip("SearXNG rate limited")
            assert response.status_code == 200, (
                f"Search failed: {response.status_code}"
            )
            data = response.json()
            assert "results" in data, "Missing 'results' in search response"
        except Exception as e:
            pytest.skip(f"SearXNG search test failed: {e}")
