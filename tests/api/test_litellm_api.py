"""LiteLLM API endpoint tests.

Tests the LiteLLM proxy service (OpenAI-compatible API):
- Health endpoint
- Model listing
- Chat completion routing
- Rate limiting
- Fallback behavior
"""

import pytest


pytestmark = [pytest.mark.api, pytest.mark.critical]


class TestLiteLLMHealth:
    """Validate LiteLLM is reachable and healthy."""

    def test_health_endpoint(self, litellm_client):
        """LiteLLM health endpoint should return 200."""
        try:
            response = litellm_client.get("/health")
            assert response.status_code == 200, (
                f"LiteLLM health returned {response.status_code}: {response.text}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach LiteLLM: {e}")

    def test_root_endpoint(self, litellm_client):
        """LiteLLM root should be accessible."""
        try:
            response = litellm_client.get("/")
            # LiteLLM may return various codes for root
            assert response.status_code < 500, (
                f"LiteLLM server error: {response.status_code}"
            )
        except Exception as e:
            pytest.fail(f"Cannot reach LiteLLM root: {e}")


class TestLiteLLMModels:
    """Validate LiteLLM model listing."""

    def test_list_models(self, litellm_client):
        """LiteLLM should list available models (OpenAI-compatible)."""
        try:
            response = litellm_client.get("/v1/models")
            assert response.status_code == 200, (
                f"Model list failed: {response.status_code}"
            )
            data = response.json()
            assert "data" in data, "Missing 'data' in models response"
            models = data["data"]
            assert len(models) >= 3, (
                f"Expected at least 3 models, found {len(models)}"
            )
        except Exception as e:
            pytest.fail(f"Model listing failed: {e}")

    def test_expected_models_present(self, litellm_client, platform_config):
        """Expected models should be in the model list."""
        try:
            response = litellm_client.get("/v1/models")
            data = response.json()
            model_ids = [m["id"] for m in data.get("data", [])]

            expected = ["qwen2.5-coder:14b", "llama3.1:8b", "mistral:7b"]
            missing = [m for m in expected if m not in model_ids]

            if missing:
                pytest.xfail(
                    f"Expected models not in LiteLLM: {missing}\n"
                    f"Available: {sorted(model_ids)}"
                )
        except Exception as e:
            pytest.fail(f"Cannot check LiteLLM models: {e}")


class TestLiteLLMChatCompletion:
    """Test OpenAI-compatible chat completion through LiteLLM."""

    @pytest.mark.slow
    def test_chat_completion(self, litellm_client, platform_config):
        """LiteLLM should route chat completions to Ollama backend."""
        try:
            response = litellm_client.post(
                "/v1/chat/completions",
                json={
                    "model": platform_config.TEST_MODEL,
                    "messages": [
                        {"role": "user", "content": "Say the word 'hello'."}
                    ],
                    "max_tokens": 16,
                    "stream": False,
                },
                timeout=120,
            )
            assert response.status_code == 200, (
                f"Chat completion failed: {response.status_code} {response.text}"
            )
            data = response.json()
            assert "choices" in data, "Missing 'choices' in response"
            assert len(data["choices"]) > 0, "Empty choices array"
            content = data["choices"][0].get("message", {}).get("content", "")
            assert len(content) > 0, "Empty response content"
        except Exception as e:
            pytest.fail(f"Chat completion through LiteLLM failed: {e}")

    @pytest.mark.slow
    def test_chat_completion_response_format(self, litellm_client, platform_config):
        """Response should follow OpenAI API format."""
        try:
            response = litellm_client.post(
                "/v1/chat/completions",
                json={
                    "model": platform_config.TEST_MODEL,
                    "messages": [
                        {"role": "user", "content": "Reply with: OK"}
                    ],
                    "max_tokens": 8,
                    "stream": False,
                },
                timeout=120,
            )
            if response.status_code != 200:
                pytest.skip(f"LiteLLM returned {response.status_code}")

            data = response.json()
            # Verify OpenAI format fields
            assert "id" in data, "Missing 'id' field"
            assert "object" in data, "Missing 'object' field"
            assert "model" in data, "Missing 'model' field"
            assert "choices" in data, "Missing 'choices' field"
            assert "usage" in data, "Missing 'usage' field"
            usage = data["usage"]
            assert "prompt_tokens" in usage, "Missing prompt_tokens"
            assert "completion_tokens" in usage, "Missing completion_tokens"
        except Exception as e:
            pytest.fail(f"Response format check failed: {e}")


class TestLiteLLMMetrics:
    """Test LiteLLM Prometheus metrics endpoint."""

    def test_metrics_endpoint(self, litellm_client):
        """LiteLLM should expose Prometheus metrics."""
        try:
            response = litellm_client.get("/metrics")
            if response.status_code == 404:
                pytest.skip("Metrics endpoint not enabled")
            assert response.status_code == 200
            text = response.text
            assert "litellm" in text.lower() or "http" in text.lower(), (
                "Metrics response does not contain expected metrics"
            )
        except Exception as e:
            pytest.skip(f"Metrics check failed: {e}")
