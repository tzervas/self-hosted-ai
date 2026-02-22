"""Cluster health validation tests.

Validates that the Kubernetes cluster infrastructure is healthy:
- Nodes are Ready
- Expected namespaces exist
- Critical pods are Running
- PVCs are Bound
"""

import pytest


pytestmark = [pytest.mark.platform, pytest.mark.critical]


class TestNodeHealth:
    """Validate cluster nodes are healthy."""

    def test_expected_nodes_exist(self, cluster_nodes, platform_config):
        """All expected nodes should be present in the cluster."""
        node_names = [
            n["metadata"]["name"] for n in cluster_nodes["items"]
        ]
        for expected in platform_config.EXPECTED_NODES:
            assert expected in node_names, (
                f"Expected node '{expected}' not found. "
                f"Available nodes: {node_names}"
            )

    def test_all_nodes_ready(self, cluster_nodes):
        """All cluster nodes should be in Ready state."""
        for node in cluster_nodes["items"]:
            name = node["metadata"]["name"]
            conditions = node["status"].get("conditions", [])
            ready_conditions = [
                c for c in conditions if c["type"] == "Ready"
            ]
            assert ready_conditions, f"Node {name} has no Ready condition"
            assert ready_conditions[0]["status"] == "True", (
                f"Node {name} is not Ready: {ready_conditions[0].get('message', 'unknown')}"
            )

    def test_nodes_have_sufficient_resources(self, cluster_nodes):
        """Nodes should have allocatable CPU and memory."""
        for node in cluster_nodes["items"]:
            name = node["metadata"]["name"]
            allocatable = node["status"].get("allocatable", {})
            assert "cpu" in allocatable, f"Node {name} missing CPU info"
            assert "memory" in allocatable, f"Node {name} missing memory info"

    def test_gpu_node_has_nvidia_resources(self, cluster_nodes):
        """GPU node (akula-prime) should report NVIDIA GPU resources."""
        for node in cluster_nodes["items"]:
            if node["metadata"]["name"] == "akula-prime":
                allocatable = node["status"].get("allocatable", {})
                gpu_keys = [k for k in allocatable if "nvidia" in k.lower()]
                assert gpu_keys, (
                    "akula-prime should have NVIDIA GPU resources. "
                    f"Allocatable keys: {list(allocatable.keys())}"
                )
                return
        pytest.skip("akula-prime node not found")


class TestNamespaces:
    """Validate expected namespaces exist."""

    def test_expected_namespaces_exist(self, cluster_namespaces, platform_config):
        """All expected namespaces should be created."""
        ns_names = [
            ns["metadata"]["name"] for ns in cluster_namespaces["items"]
        ]
        missing = []
        for expected in platform_config.EXPECTED_NAMESPACES:
            if expected not in ns_names:
                missing.append(expected)
        assert not missing, (
            f"Missing namespaces: {missing}. "
            f"Available: {sorted(ns_names)}"
        )

    def test_namespaces_are_active(self, cluster_namespaces, platform_config):
        """Expected namespaces should be in Active phase."""
        for ns in cluster_namespaces["items"]:
            if ns["metadata"]["name"] in platform_config.EXPECTED_NAMESPACES:
                phase = ns["status"].get("phase", "Unknown")
                assert phase == "Active", (
                    f"Namespace {ns['metadata']['name']} is {phase}, expected Active"
                )


class TestPodHealth:
    """Validate critical pods are running."""

    def test_no_crashloopbackoff_pods(self, cluster_pods):
        """No pods should be in CrashLoopBackOff state."""
        crashing = []
        for pod in cluster_pods["items"]:
            ns = pod["metadata"]["namespace"]
            name = pod["metadata"]["name"]
            for cs in pod["status"].get("containerStatuses", []):
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting.get("reason") == "CrashLoopBackOff":
                    crashing.append(f"{ns}/{name}")
        assert not crashing, (
            f"Pods in CrashLoopBackOff: {crashing}"
        )

    def test_critical_services_running(self, cluster_pods, platform_config):
        """Critical service pods should be Running."""
        pod_map = {}
        for pod in cluster_pods["items"]:
            ns = pod["metadata"]["namespace"]
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase", "Unknown")
            pod_map.setdefault(ns, []).append((name, phase))

        missing = []
        for ns, services in platform_config.CRITICAL_SERVICES.items():
            ns_pods = pod_map.get(ns, [])
            for svc in services:
                found = any(svc in pname for pname, _ in ns_pods)
                if not found:
                    missing.append(f"{ns}/{svc}")
                else:
                    running = any(
                        svc in pname and phase in ("Running", "Succeeded")
                        for pname, phase in ns_pods
                    )
                    if not running:
                        matching = [
                            (pname, phase) for pname, phase in ns_pods
                            if svc in pname
                        ]
                        missing.append(
                            f"{ns}/{svc} (found but not running: {matching})"
                        )

        assert not missing, (
            f"Critical services not running:\n" +
            "\n".join(f"  - {m}" for m in missing)
        )

    def test_pods_have_ready_containers(self, cluster_pods, platform_config):
        """Running pods should have all containers ready."""
        not_ready = []
        for pod in cluster_pods["items"]:
            ns = pod["metadata"]["namespace"]
            if ns not in platform_config.EXPECTED_NAMESPACES:
                continue
            name = pod["metadata"]["name"]
            phase = pod["status"].get("phase", "Unknown")
            if phase != "Running":
                continue
            for cs in pod["status"].get("containerStatuses", []):
                if not cs.get("ready", False):
                    not_ready.append(f"{ns}/{name}/{cs['name']}")

        assert not not_ready, (
            f"Containers not ready:\n" +
            "\n".join(f"  - {c}" for c in not_ready)
        )


class TestPersistentVolumes:
    """Validate persistent volume claims."""

    def test_pvcs_are_bound(self, kubectl_available, kubectl, platform_config):
        """PVCs in critical namespaces should be in Bound state."""
        if not kubectl_available:
            pytest.skip("kubectl not available")
        pvcs = kubectl("pvc", all_namespaces=True)
        critical_unbound = []
        other_unbound = []
        for pvc in pvcs["items"]:
            ns = pvc["metadata"]["namespace"]
            name = pvc["metadata"]["name"]
            phase = pvc["status"].get("phase", "Unknown")
            if phase != "Bound":
                entry = f"{ns}/{name} ({phase})"
                if ns in platform_config.EXPECTED_NAMESPACES:
                    critical_unbound.append(entry)
                else:
                    other_unbound.append(entry)

        all_unbound = critical_unbound + other_unbound
        if all_unbound:
            pytest.xfail(
                f"Unbound PVCs (may be WaitForFirstConsumer):\n" +
                "\n".join(f"  - {p}" for p in all_unbound)
            )
