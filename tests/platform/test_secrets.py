"""Secret validation tests.

Validates that required Kubernetes secrets exist in the correct namespaces.
Does NOT read secret data -- only checks existence.
"""

import pytest


pytestmark = [pytest.mark.platform, pytest.mark.critical]


# Secrets required for core platform functionality
REQUIRED_SECRETS = {
    "self-hosted-ai": [
        "webui-secret",
        "postgresql-secret",
    ],
    "sso": [
        "keycloak-oidc-secret",
    ],
}

# Secrets that should exist but are not blocking
RECOMMENDED_SECRETS = {
    "self-hosted-ai": [
        "litellm-secret",
        "keycloak-oidc-secret",
    ],
    "automation": [
        "n8n-secret",
    ],
    "monitoring": [
        "grafana-secret",
    ],
}


class TestRequiredSecrets:
    """Validate required secrets exist."""

    def test_required_secrets_present(self, cluster_secrets, platform_config):
        """All required secrets should exist in their namespaces."""
        missing = []
        for ns, secrets in REQUIRED_SECRETS.items():
            for secret_name in secrets:
                key = f"{ns}/{secret_name}"
                if key not in cluster_secrets:
                    missing.append(key)

        assert not missing, (
            f"Missing required secrets:\n" +
            "\n".join(f"  - {m}" for m in missing)
        )

    def test_recommended_secrets_present(self, cluster_secrets):
        """Recommended secrets should exist (warning only)."""
        missing = []
        for ns, secrets in RECOMMENDED_SECRETS.items():
            for secret_name in secrets:
                key = f"{ns}/{secret_name}"
                if key not in cluster_secrets:
                    missing.append(key)

        if missing:
            pytest.xfail(
                f"Missing recommended secrets (non-blocking):\n" +
                "\n".join(f"  - {m}" for m in missing)
            )


class TestSealedSecretsController:
    """Validate SealedSecrets controller is operational."""

    def test_sealed_secrets_controller_running(self, cluster_pods):
        """SealedSecrets controller should be running."""
        controller_pods = [
            p for p in cluster_pods["items"]
            if "sealed-secrets" in p["metadata"]["name"]
            and p["metadata"]["namespace"] in ("kube-system", "sealed-secrets")
        ]
        assert controller_pods, "SealedSecrets controller pod not found"
        for pod in controller_pods:
            phase = pod["status"].get("phase", "Unknown")
            assert phase == "Running", (
                f"SealedSecrets controller is {phase}, expected Running"
            )
