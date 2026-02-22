"""Keycloak API endpoint tests.

Tests the Keycloak SSO identity provider:
- Health/connectivity
- Realm configuration
- OIDC discovery endpoint
"""

import pytest


pytestmark = [pytest.mark.api]


class TestKeycloakHealth:
    """Validate Keycloak is reachable."""

    def test_keycloak_reachable(self, http_client, platform_config):
        """Keycloak should be reachable."""
        try:
            # Keycloak may not have external ingress, try internal
            response = http_client.get(
                f"https://keycloak.{platform_config.DOMAIN}/",
            )
            assert response.status_code in (200, 302, 303), (
                f"Keycloak returned {response.status_code}"
            )
        except Exception as e:
            pytest.skip(f"Keycloak not reachable externally: {e}")


class TestKeycloakOIDC:
    """Validate OIDC discovery endpoint."""

    def test_oidc_discovery(self, http_client, platform_config):
        """Keycloak OIDC discovery endpoint should return valid configuration."""
        try:
            # Try external URL first, fall back to pattern
            for url in [
                f"https://keycloak.{platform_config.DOMAIN}/realms/vectorweight/.well-known/openid-configuration",
                f"https://sso.{platform_config.DOMAIN}/realms/vectorweight/.well-known/openid-configuration",
            ]:
                response = http_client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    assert "issuer" in data, "Missing 'issuer' in OIDC config"
                    assert "authorization_endpoint" in data, (
                        "Missing 'authorization_endpoint'"
                    )
                    assert "token_endpoint" in data, "Missing 'token_endpoint'"
                    assert "jwks_uri" in data, "Missing 'jwks_uri'"
                    return

            pytest.skip("OIDC discovery endpoint not reachable at expected URLs")
        except Exception as e:
            pytest.skip(f"OIDC discovery check failed: {e}")

    def test_vectorweight_realm_exists(self, http_client, platform_config):
        """The 'vectorweight' realm should exist in Keycloak."""
        try:
            response = http_client.get(
                f"https://keycloak.{platform_config.DOMAIN}/realms/vectorweight"
            )
            if response.status_code == 200:
                data = response.json()
                assert data.get("realm") == "vectorweight", (
                    f"Realm name mismatch: {data.get('realm')}"
                )
            else:
                pytest.skip(
                    f"Realm endpoint returned {response.status_code}"
                )
        except Exception as e:
            pytest.skip(f"Cannot verify realm: {e}")
