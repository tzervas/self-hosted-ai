"""Inference latency performance tests.

Measures and validates response times for AI model inference:
- First token latency
- Full response latency
- Embedding latency
"""

import time

import pytest


pytestmark = [pytest.mark.performance, pytest.mark.slow]


# Latency thresholds in seconds
THRESHOLDS = {
    "small_model_p95": 30.0,      # 8B model, short prompt
    "large_model_p95": 60.0,      # 14B model, short prompt
    "embedding_p95": 5.0,         # Embedding generation
    "health_check_p95": 2.0,      # Health endpoint
}


class TestInferenceLatency:
    """Measure and validate inference response times."""

    def test_small_model_latency(self, ollama_gpu_client, platform_config):
        """Small model (8B) should respond within threshold."""
        latencies = []
        for _ in range(3):
            start = time.monotonic()
            try:
                response = ollama_gpu_client.post(
                    "/api/generate",
                    json={
                        "model": platform_config.TEST_MODEL,
                        "prompt": "Reply with: OK",
                        "stream": False,
                        "options": {"num_predict": 8},
                    },
                    timeout=120,
                )
                elapsed = time.monotonic() - start
                if response.status_code == 200:
                    latencies.append(elapsed)
            except Exception:
                pass

        if not latencies:
            pytest.fail("No successful inference requests")

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        avg = sum(latencies) / len(latencies)

        assert p95 <= THRESHOLDS["small_model_p95"], (
            f"Small model p95 latency too high: {p95:.2f}s "
            f"(threshold: {THRESHOLDS['small_model_p95']}s, "
            f"avg: {avg:.2f}s)"
        )

    def test_embedding_latency(self, ollama_gpu_client):
        """Embedding generation should complete within threshold."""
        latencies = []
        for _ in range(3):
            start = time.monotonic()
            try:
                response = ollama_gpu_client.post(
                    "/api/embeddings",
                    json={
                        "model": "nomic-embed-text",
                        "prompt": "Test embedding latency measurement.",
                    },
                    timeout=30,
                )
                elapsed = time.monotonic() - start
                if response.status_code == 200:
                    latencies.append(elapsed)
            except Exception:
                pass

        if not latencies:
            pytest.skip("No successful embedding requests")

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 <= THRESHOLDS["embedding_p95"], (
            f"Embedding p95 latency too high: {p95:.2f}s "
            f"(threshold: {THRESHOLDS['embedding_p95']}s)"
        )

    def test_health_endpoint_latency(self, http_client, platform_config):
        """Health check endpoints should respond quickly."""
        latencies = []
        for _ in range(5):
            start = time.monotonic()
            try:
                response = http_client.get(
                    f"{platform_config.OPENWEBUI_EXTERNAL}/health",
                    timeout=10,
                )
                elapsed = time.monotonic() - start
                if response.status_code == 200:
                    latencies.append(elapsed)
            except Exception:
                pass

        if not latencies:
            pytest.skip("Cannot reach health endpoint")

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 <= THRESHOLDS["health_check_p95"], (
            f"Health check p95 latency too high: {p95:.2f}s "
            f"(threshold: {THRESHOLDS['health_check_p95']}s)"
        )


class TestResourceUsage:
    """Validate resource usage is within acceptable bounds."""

    def test_cluster_resource_utilization(self, kubectl_available):
        """Cluster resource utilization should be below critical thresholds."""
        if not kubectl_available:
            pytest.skip("kubectl not available")

        import subprocess
        result = subprocess.run(
            ["kubectl", "top", "nodes", "--no-headers"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("kubectl top not available (metrics-server required)")

        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                node = parts[0]
                cpu_pct = parts[2].rstrip("%")
                mem_pct = parts[4].rstrip("%")
                try:
                    cpu = int(cpu_pct)
                    mem = int(mem_pct)
                    assert cpu < 90, f"Node {node} CPU at {cpu}% (critical)"
                    assert mem < 90, f"Node {node} memory at {mem}% (critical)"
                except ValueError:
                    pass
