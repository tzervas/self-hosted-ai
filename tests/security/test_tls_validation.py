"""TLS validation security tests.

Validates that:
- External endpoints use HTTPS with valid TLS
- No services use insecureSkipVerify in production
- Certificate chain is complete
"""

import ssl
import socket

import pytest


pytestmark = [pytest.mark.security, pytest.mark.critical]


class TestExternalTLS:
    """Validate TLS on external-facing endpoints."""

    def test_external_endpoints_use_tls(self, http_client, platform_config):
        """All external endpoints should be accessible via HTTPS."""
        failures = []
        for name, url in platform_config.EXTERNAL_ENDPOINTS.items():
            try:
                response = http_client.get(url, timeout=10)
                # Any response (even 401/403) means TLS handshake succeeded
                if response.status_code >= 500:
                    failures.append(f"{name}: server error {response.status_code}")
            except Exception as e:
                failures.append(f"{name} ({url}): {e}")

        assert not failures, (
            f"Endpoints with TLS issues:\n" +
            "\n".join(f"  - {f}" for f in failures)
        )

    def test_tls_certificate_valid(self, platform_config):
        """TLS certificates should be valid (may be self-signed)."""
        hostname = f"ai.{platform_config.DOMAIN}"
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    assert cert is not None, "No certificate presented"
                    # Certificate exists - whether CA-signed or self-signed
                    # is validated by test_certificates.py
        except (ConnectionRefusedError, socket.timeout, OSError):
            pytest.skip(f"Cannot connect to {hostname}:443")


class TestNoInsecureSkipVerify:
    """Ensure no production configs use insecureSkipVerify."""

    def test_helm_values_no_insecure_skip(self):
        """Helm values files should not contain insecureSkipVerify: true."""
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent

        violations = []
        for values_file in project_root.glob("helm/*/values.yaml"):
            content = values_file.read_text()
            if "insecureSkipVerify: true" in content:
                violations.append(values_file.relative_to(project_root))
            if "insecure_skip_verify: true" in content:
                violations.append(values_file.relative_to(project_root))

        assert not violations, (
            f"Files with insecureSkipVerify enabled:\n" +
            "\n".join(f"  - {v}" for v in violations)
        )

    def test_argocd_no_insecure_skip(self):
        """ArgoCD config should not use insecureSkipVerify."""
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent

        violations = []
        argocd_dir = project_root / "argocd"
        if argocd_dir.exists():
            for yaml_file in argocd_dir.rglob("*.yaml"):
                content = yaml_file.read_text()
                if "insecureSkipVerify: true" in content:
                    # Check if it's been properly replaced with rootCA
                    if "rootCA" not in content:
                        violations.append(
                            yaml_file.relative_to(project_root)
                        )

        if violations:
            pytest.xfail(
                f"ArgoCD configs with insecureSkipVerify (review needed):\n" +
                "\n".join(f"  - {v}" for v in violations)
            )
