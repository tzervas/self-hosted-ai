"""Pod Security Standards (PSS) compliance tests.

Validates that pods follow the PSS baseline profile:
- No privileged containers
- No host namespace access
- Proper security contexts
"""

import json
import subprocess

import pytest


pytestmark = [pytest.mark.security]


# Namespaces that should enforce PSS baseline
PSS_NAMESPACES = [
    "self-hosted-ai",
    "gpu-workloads",
    "automation",
]


class TestPodSecurityContext:
    """Validate pod security contexts."""

    def test_no_privileged_pods(self, kubectl_available):
        """No pods in AI namespaces should run as privileged."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        privileged = []
        for ns in PSS_NAMESPACES:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", ns, "-o", "json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                continue

            data = json.loads(result.stdout)
            for pod in data.get("items", []):
                name = pod["metadata"]["name"]
                spec = pod.get("spec", {})

                # Check init containers and regular containers
                for container in (
                    spec.get("containers", []) +
                    spec.get("initContainers", [])
                ):
                    sc = container.get("securityContext", {})
                    if sc.get("privileged"):
                        privileged.append(f"{ns}/{name}/{container['name']}")

        assert not privileged, (
            f"Privileged containers found:\n" +
            "\n".join(f"  - {p}" for p in privileged)
        )

    def test_no_host_network(self, kubectl_available):
        """Pods should not use host networking."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        host_net = []
        for ns in PSS_NAMESPACES:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", ns, "-o", "json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                continue

            data = json.loads(result.stdout)
            for pod in data.get("items", []):
                name = pod["metadata"]["name"]
                if pod.get("spec", {}).get("hostNetwork"):
                    host_net.append(f"{ns}/{name}")

        assert not host_net, (
            f"Pods using host network:\n" +
            "\n".join(f"  - {p}" for p in host_net)
        )

    def test_containers_drop_all_capabilities(self, kubectl_available):
        """Containers should drop ALL capabilities."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        missing_drop = []
        for ns in PSS_NAMESPACES:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", ns, "-o", "json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                continue

            data = json.loads(result.stdout)
            for pod in data.get("items", []):
                name = pod["metadata"]["name"]
                for container in pod.get("spec", {}).get("containers", []):
                    sc = container.get("securityContext", {})
                    caps = sc.get("capabilities", {})
                    drop = caps.get("drop", [])
                    if "ALL" not in drop:
                        missing_drop.append(
                            f"{ns}/{name}/{container['name']}"
                        )

        if missing_drop:
            pytest.xfail(
                f"Containers not dropping ALL capabilities (PSS recommendation):\n" +
                "\n".join(f"  - {m}" for m in missing_drop[:10])
            )


class TestPSSLabels:
    """Validate PSS label enforcement on namespaces."""

    def test_namespaces_have_pss_labels(self, kubectl_available):
        """AI namespaces should have PSS enforcement labels."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        missing_pss = []
        for ns in PSS_NAMESPACES:
            result = subprocess.run(
                ["kubectl", "get", "namespace", ns, "-o", "json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                missing_pss.append(f"{ns}: namespace not found")
                continue

            data = json.loads(result.stdout)
            labels = data.get("metadata", {}).get("labels", {})

            # Check for pod-security.kubernetes.io labels
            pss_labels = {
                k: v for k, v in labels.items()
                if "pod-security.kubernetes.io" in k
            }
            if not pss_labels:
                missing_pss.append(f"{ns}: no PSS labels")

        if missing_pss:
            pytest.xfail(
                f"Namespaces without PSS labels:\n" +
                "\n".join(f"  - {m}" for m in missing_pss)
            )
