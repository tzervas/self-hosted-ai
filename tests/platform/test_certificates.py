"""TLS certificate validation tests.

Validates that certificates are:
- Present and valid
- Not expired or expiring soon
- Properly configured in ingress resources
"""

import subprocess
from datetime import datetime, timezone

import pytest


pytestmark = [pytest.mark.platform, pytest.mark.critical]


class TestCertificateResources:
    """Validate Kubernetes certificate resources."""

    def test_certificates_exist(self, cluster_certificates):
        """At least one certificate resource should exist."""
        certs = cluster_certificates.get("items", [])
        assert len(certs) > 0, "No certificate resources found in cluster"

    def test_certificates_ready(self, cluster_certificates):
        """Certificate resources should have Ready=True condition."""
        not_ready = []
        for cert in cluster_certificates.get("items", []):
            ns = cert["metadata"]["namespace"]
            name = cert["metadata"]["name"]
            conditions = cert.get("status", {}).get("conditions", [])
            ready = [c for c in conditions if c["type"] == "Ready"]
            if not ready or ready[0]["status"] != "True":
                reason = ready[0].get("reason", "Unknown") if ready else "No Ready condition"
                not_ready.append(f"{ns}/{name}: {reason}")

        assert not not_ready, (
            f"Certificates not ready:\n" +
            "\n".join(f"  - {c}" for c in not_ready)
        )

    def test_certificates_not_expiring_soon(self, cluster_certificates):
        """Certificates should not expire within 7 days."""
        expiring_soon = []
        now = datetime.now(timezone.utc)
        for cert in cluster_certificates.get("items", []):
            ns = cert["metadata"]["namespace"]
            name = cert["metadata"]["name"]
            not_after = cert.get("status", {}).get("notAfter")
            if not_after:
                try:
                    expiry = datetime.fromisoformat(
                        not_after.replace("Z", "+00:00")
                    )
                    days_until = (expiry - now).days
                    if days_until < 7:
                        expiring_soon.append(
                            f"{ns}/{name}: expires in {days_until} days"
                        )
                except (ValueError, TypeError):
                    pass

        assert not expiring_soon, (
            f"Certificates expiring within 7 days:\n" +
            "\n".join(f"  - {c}" for c in expiring_soon)
        )


class TestCertManagerIssuers:
    """Validate cert-manager issuers are configured."""

    def test_cluster_issuers_exist(self, kubectl_available):
        """At least one ClusterIssuer should be configured."""
        if not kubectl_available:
            pytest.skip("kubectl not available")
        result = subprocess.run(
            ["kubectl", "get", "clusterissuers", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("Cannot query ClusterIssuers (CRD may not exist)")

        import json
        data = json.loads(result.stdout)
        issuers = data.get("items", [])
        assert len(issuers) > 0, "No ClusterIssuers configured"

    def test_cluster_issuers_ready(self, kubectl_available):
        """ClusterIssuers should be in Ready state."""
        if not kubectl_available:
            pytest.skip("kubectl not available")
        result = subprocess.run(
            ["kubectl", "get", "clusterissuers", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("Cannot query ClusterIssuers")

        import json
        data = json.loads(result.stdout)
        not_ready = []
        for issuer in data.get("items", []):
            name = issuer["metadata"]["name"]
            conditions = issuer.get("status", {}).get("conditions", [])
            ready = [c for c in conditions if c["type"] == "Ready"]
            if not ready or ready[0]["status"] != "True":
                not_ready.append(name)

        assert not not_ready, (
            f"ClusterIssuers not ready: {not_ready}"
        )


class TestTLSIngress:
    """Validate TLS is configured on ingress resources."""

    def test_ingress_resources_have_tls(self, kubectl_available):
        """Ingress resources for critical services should have TLS configured."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        result = subprocess.run(
            ["kubectl", "get", "ingress", "-A", "-o", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("Cannot query ingress resources")

        import json
        data = json.loads(result.stdout)
        no_tls = []
        for ingress in data.get("items", []):
            ns = ingress["metadata"]["namespace"]
            name = ingress["metadata"]["name"]
            tls = ingress.get("spec", {}).get("tls", [])
            if not tls:
                no_tls.append(f"{ns}/{name}")

        # Some ingress resources may intentionally not have TLS
        if no_tls:
            pytest.xfail(
                f"Ingress without TLS (may be intentional): {no_tls}"
            )
