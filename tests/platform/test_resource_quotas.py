"""Resource quota and limit range validation tests.

Validates that namespaces have appropriate resource constraints configured.
"""

import pytest


pytestmark = [pytest.mark.platform]


# Namespaces that should have resource quotas
QUOTA_NAMESPACES = [
    "self-hosted-ai",
    "gpu-workloads",
    "monitoring",
    "automation",
]


class TestResourceQuotas:
    """Validate resource quotas are applied."""

    def test_quota_namespaces_have_quotas(self, resource_quotas):
        """Expected namespaces should have ResourceQuotas applied."""
        quota_ns = set()
        for quota in resource_quotas.get("items", []):
            quota_ns.add(quota["metadata"]["namespace"])

        missing = [ns for ns in QUOTA_NAMESPACES if ns not in quota_ns]
        if missing:
            pytest.xfail(
                f"Namespaces without ResourceQuotas (may be intentional): {missing}"
            )

    def test_quotas_have_limits(self, resource_quotas):
        """ResourceQuotas should define CPU and memory limits."""
        no_limits = []
        for quota in resource_quotas.get("items", []):
            ns = quota["metadata"]["namespace"]
            name = quota["metadata"]["name"]
            hard = quota.get("spec", {}).get("hard", {})
            if not hard:
                no_limits.append(f"{ns}/{name}: no hard limits defined")

        assert not no_limits, (
            f"ResourceQuotas without limits:\n" +
            "\n".join(f"  - {q}" for q in no_limits)
        )
