"""Integration test fixtures."""

import pytest
import httpx


@pytest.fixture(scope="module")
def authenticated_webui_client(platform_config):
    """Create an authenticated Open WebUI client.

    Logs in with admin credentials and uses the JWT token
    for subsequent requests.
    """
    if not platform_config.WEBUI_ADMIN_PASSWORD:
        pytest.skip("WEBUI_ADMIN_PASSWORD not set for integration tests")

    client = httpx.Client(
        base_url=platform_config.OPENWEBUI_EXTERNAL,
        timeout=httpx.Timeout(60.0, connect=10.0),
        verify=False,
    )

    try:
        response = client.post(
            "/api/v1/auths/signin",
            json={
                "email": platform_config.WEBUI_ADMIN_EMAIL,
                "password": platform_config.WEBUI_ADMIN_PASSWORD,
            },
        )
        if response.status_code != 200:
            pytest.skip(f"Cannot login to Open WebUI: {response.status_code}")

        token = response.json().get("token")
        if not token:
            pytest.skip("Login succeeded but no token returned")

        client.headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        client.close()
        pytest.skip(f"Authentication failed: {e}")

    yield client
    client.close()
