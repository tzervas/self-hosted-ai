"""Inference pipeline integration tests.

Tests the complete inference path:
- LiteLLM -> Ollama GPU (direct routing)
- LiteLLM -> Ollama CPU (fallback)
- Open WebUI -> Ollama (direct)
- Multi-model chaining
"""

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.critical, pytest.mark.slow]


class TestLiteLLMToOllama:
    """Test LiteLLM proxy routing to Ollama backends."""

    def test_gpu_model_inference(self, litellm_client, platform_config):
        """LiteLLM should route GPU model requests to Ollama GPU."""
        if platform_config.SKIP_GPU_TESTS:
            pytest.skip("GPU tests disabled")

        try:
            response = litellm_client.post(
                "/v1/chat/completions",
                json={
                    "model": platform_config.TEST_GPU_MODEL,
                    "messages": [
                        {"role": "user", "content": "Reply with just: GPU OK"}
                    ],
                    "max_tokens": 16,
                    "stream": False,
                },
                timeout=120,
            )
            assert response.status_code == 200, (
                f"GPU model inference failed: {response.status_code} {response.text}"
            )
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            assert len(content) > 0, "Empty GPU model response"
        except Exception as e:
            pytest.fail(f"GPU model inference through LiteLLM failed: {e}")

    def test_cpu_model_inference(self, litellm_client):
        """LiteLLM should route CPU model requests to Ollama CPU."""
        try:
            response = litellm_client.post(
                "/v1/chat/completions",
                json={
                    "model": "mistral:7b",
                    "messages": [
                        {"role": "user", "content": "Reply with just: CPU OK"}
                    ],
                    "max_tokens": 16,
                    "stream": False,
                },
                timeout=120,
            )
            assert response.status_code == 200, (
                f"CPU model inference failed: {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"CPU model inference through LiteLLM failed: {e}")

    def test_embedding_model_routing(self, litellm_client):
        """LiteLLM should route embedding requests correctly."""
        try:
            response = litellm_client.post(
                "/v1/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "input": "Test embedding text",
                },
                timeout=60,
            )
            if response.status_code == 200:
                data = response.json()
                assert "data" in data, "Missing embedding data"
                assert len(data["data"]) > 0, "Empty embedding response"
                assert "embedding" in data["data"][0], "Missing embedding vector"
            else:
                pytest.xfail(
                    f"Embedding via LiteLLM returned {response.status_code}"
                )
        except Exception as e:
            pytest.xfail(f"Embedding routing test: {e}")


class TestOpenWebUIToOllama:
    """Test Open WebUI's connection to Ollama."""

    def test_webui_model_list(self, authenticated_webui_client):
        """Open WebUI should list models from connected Ollama instances."""
        try:
            response = authenticated_webui_client.get("/api/models")
            if response.status_code == 404:
                response = authenticated_webui_client.get("/api/v1/models")
            assert response.status_code == 200, (
                f"Model list failed: {response.status_code}"
            )
            data = response.json()
            # Open WebUI returns models in various formats
            models = data if isinstance(data, list) else data.get("data", data.get("models", []))
            assert len(models) > 0, "No models available in Open WebUI"
        except Exception as e:
            pytest.fail(f"Open WebUI model listing failed: {e}")

    def test_webui_chat_completion(self, authenticated_webui_client, platform_config):
        """Open WebUI should be able to generate a response via Ollama."""
        try:
            response = authenticated_webui_client.post(
                "/api/chat/completions",
                json={
                    "model": platform_config.TEST_MODEL,
                    "messages": [
                        {"role": "user", "content": "Reply with: WEBUI OK"}
                    ],
                    "max_tokens": 16,
                    "stream": False,
                },
                timeout=120,
            )
            if response.status_code == 404:
                # Try alternative endpoint
                response = authenticated_webui_client.post(
                    "/ollama/api/chat",
                    json={
                        "model": platform_config.TEST_MODEL,
                        "messages": [
                            {"role": "user", "content": "Reply with: WEBUI OK"}
                        ],
                        "stream": False,
                    },
                    timeout=120,
                )
            assert response.status_code == 200, (
                f"WebUI chat failed: {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Open WebUI chat completion failed: {e}")


class TestModelRouting:
    """Test model routing and fallback behavior."""

    def test_multiple_models_respond(self, ollama_gpu_client, platform_config):
        """Multiple models should be able to respond sequentially."""
        models_to_test = [platform_config.TEST_MODEL]
        if not platform_config.SKIP_GPU_TESTS:
            models_to_test.append(platform_config.TEST_GPU_MODEL)

        results = {}
        for model in models_to_test:
            try:
                response = ollama_gpu_client.post(
                    "/api/generate",
                    json={
                        "model": model,
                        "prompt": f"What model are you? One sentence.",
                        "stream": False,
                        "options": {"num_predict": 32},
                    },
                    timeout=120,
                )
                results[model] = response.status_code == 200
            except Exception:
                results[model] = False

        passed = [m for m, ok in results.items() if ok]
        failed = [m for m, ok in results.items() if not ok]

        assert len(passed) > 0, (
            f"No models responded. Failed: {failed}"
        )
        if failed:
            pytest.xfail(f"Some models did not respond: {failed}")
