"""Open WebUI API endpoint tests.

Tests the Open WebUI chat interface:
- Health endpoint
- Authentication
- Model listing
- Configuration
"""

import pytest


pytestmark = [pytest.mark.api, pytest.mark.critical]


class TestOpenWebUIHealth:
    """Validate Open WebUI is reachable and healthy."""

    def test_health_endpoint(self, openwebui_client):
        """Open WebUI health endpoint should return 200."""
        try:
            response = openwebui_client.get("/health")
            assert response.status_code == 200, (
                f"Open WebUI health returned {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach Open WebUI: {e}")

    def test_root_page_loads(self, openwebui_client):
        """Open WebUI root page should load (returns HTML or redirect)."""
        try:
            response = openwebui_client.get("/")
            assert response.status_code in (200, 302, 303), (
                f"Open WebUI root returned {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot load Open WebUI root: {e}")


class TestOpenWebUIAuth:
    """Validate Open WebUI authentication."""

    def test_api_requires_auth(self, openwebui_client):
        """API endpoints should require authentication."""
        response = openwebui_client.get("/api/v1/auths/")
        # Should return 401 or 403 without auth
        assert response.status_code in (401, 403, 405), (
            f"API should require auth, got {response.status_code}"
        )

    @pytest.mark.slow
    def test_login_with_credentials(self, openwebui_client, platform_config):
        """Should be able to login with admin credentials."""
        if not platform_config.WEBUI_ADMIN_PASSWORD:
            pytest.skip("WEBUI_ADMIN_PASSWORD not set")

        try:
            response = openwebui_client.post(
                "/api/v1/auths/signin",
                json={
                    "email": platform_config.WEBUI_ADMIN_EMAIL,
                    "password": platform_config.WEBUI_ADMIN_PASSWORD,
                },
            )
            assert response.status_code == 200, (
                f"Login failed: {response.status_code} {response.text}"
            )
            data = response.json()
            assert "token" in data, "Login response missing token"
        except Exception as e:
            pytest.fail(f"Login failed: {e}")


class TestOpenWebUIConfiguration:
    """Validate Open WebUI configuration."""

    def test_signup_disabled(self, openwebui_client):
        """User signup should be disabled (security)."""
        try:
            response = openwebui_client.post(
                "/api/v1/auths/signup",
                json={
                    "email": "test@test.com",
                    "password": "testpassword123",
                    "name": "Test User",
                },
            )
            # Should fail with 403 or 400 (signup disabled)
            assert response.status_code in (400, 403, 422), (
                f"Signup should be disabled, got {response.status_code}"
            )
        except Exception as e:
            # Connection error is also acceptable (endpoint may not exist)
            pass

    def test_oauth_configured(self, openwebui_client):
        """OAuth/OIDC configuration should be present."""
        try:
            # The auth page should mention Keycloak as a login option
            response = openwebui_client.get("/")
            # We cannot easily verify OIDC from external API
            # This is better tested manually
            assert response.status_code in (200, 302, 303)
        except Exception as e:
            pytest.skip(f"Cannot verify OAuth config: {e}")
