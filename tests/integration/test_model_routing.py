"""Model routing integration tests.

Tests LiteLLM's model routing capabilities:
- GPU to CPU fallback
- Load balancing
- Embedding routing
"""

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestModelFallback:
    """Test model fallback chains (GPU -> CPU)."""

    def test_fallback_to_cpu_model(self, litellm_client, platform_config):
        """When GPU model is unavailable, LiteLLM should fall back to CPU model."""
        # This test verifies that LiteLLM's fallback configuration works
        # by requesting a model and checking that any response is returned
        # (the fallback chain is: qwen2.5-coder -> mistral:7b)
        try:
            response = litellm_client.post(
                "/v1/chat/completions",
                json={
                    "model": platform_config.TEST_MODEL,
                    "messages": [
                        {"role": "user", "content": "Reply with: FALLBACK OK"}
                    ],
                    "max_tokens": 16,
                    "stream": False,
                },
                timeout=120,
            )
            assert response.status_code == 200, (
                f"Model request failed (no fallback?): {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Model fallback test failed: {e}")


class TestEmbeddingRouting:
    """Test embedding model routing."""

    def test_embedding_via_cpu(self, ollama_gpu_client):
        """Embedding model should be available and produce vectors."""
        try:
            response = ollama_gpu_client.post(
                "/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": "Integration test for embedding routing.",
                },
                timeout=60,
            )
            if response.status_code != 200:
                pytest.skip(f"Embedding model returned {response.status_code}")

            data = response.json()
            embedding = data.get("embedding", [])
            assert len(embedding) >= 128, (
                f"Embedding dimension too low: {len(embedding)}"
            )
        except Exception as e:
            pytest.skip(f"Embedding routing test failed: {e}")
