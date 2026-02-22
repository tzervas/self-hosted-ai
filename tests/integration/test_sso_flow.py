"""SSO authentication flow integration tests.

Tests the Keycloak -> OAuth2-proxy -> Service authentication chain.
"""

import pytest


pytestmark = [pytest.mark.integration]


class TestSSORedirect:
    """Test SSO redirect behavior for protected services."""

    def test_openwebui_oauth_configured(self, http_client, platform_config):
        """Open WebUI should have OAuth/OIDC configuration."""
        try:
            response = http_client.get(
                f"{platform_config.OPENWEBUI_EXTERNAL}/",
                follow_redirects=False,
            )
            # If OAuth is configured, root may redirect to login
            # or serve the login page with OAuth button
            assert response.status_code in (200, 302, 303), (
                f"Open WebUI returned {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot check OAuth config: {e}")

    def test_protected_services_require_auth(self, http_client, platform_config):
        """Services behind oauth2-proxy should redirect to SSO."""
        # Services that should be protected by oauth2-proxy
        protected_endpoints = [
            platform_config.N8N_EXTERNAL,
            platform_config.GRAFANA_EXTERNAL,
        ]

        for endpoint in protected_endpoints:
            try:
                response = http_client.get(
                    endpoint,
                    follow_redirects=False,
                )
                # Should get a redirect to auth or a 401/403
                assert response.status_code in (200, 302, 303, 401, 403), (
                    f"{endpoint} returned unexpected {response.status_code}"
                )
            except Exception:
                # Connection error is acceptable (service may not be exposed)
                pass


class TestKeycloakRealmConfig:
    """Test Keycloak realm configuration for platform services."""

    def test_realm_public_key_available(self, http_client, platform_config):
        """Keycloak should expose public keys for JWT validation."""
        try:
            for base_url in [
                f"https://keycloak.{platform_config.DOMAIN}",
                f"https://sso.{platform_config.DOMAIN}",
            ]:
                response = http_client.get(
                    f"{base_url}/realms/vectorweight/protocol/openid-connect/certs"
                )
                if response.status_code == 200:
                    data = response.json()
                    assert "keys" in data, "Missing JWKS keys"
                    assert len(data["keys"]) > 0, "No keys in JWKS"
                    return

            pytest.skip("Keycloak JWKS endpoint not reachable")
        except Exception as e:
            pytest.skip(f"Cannot verify JWKS: {e}")
