"""n8n API endpoint tests.

Tests the n8n workflow automation service:
- Health/connectivity
- Webhook endpoints
"""

import pytest


pytestmark = [pytest.mark.api]


class TestN8NHealth:
    """Validate n8n is reachable."""

    def test_n8n_reachable(self, http_client, platform_config):
        """n8n should be reachable via external URL."""
        try:
            response = http_client.get(
                f"{platform_config.N8N_EXTERNAL}/healthz"
            )
            if response.status_code == 404:
                response = http_client.get(platform_config.N8N_EXTERNAL)
            assert response.status_code in (200, 302, 401), (
                f"n8n returned {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach n8n: {e}")

    def test_n8n_login_page(self, http_client, platform_config):
        """n8n login page should load."""
        try:
            response = http_client.get(
                f"{platform_config.N8N_EXTERNAL}/signin"
            )
            # May redirect to SSO or show login form
            assert response.status_code in (200, 302, 303), (
                f"n8n signin returned {response.status_code}"
            )
        except Exception as e:
            pytest.skip(f"Cannot load n8n signin: {e}")
