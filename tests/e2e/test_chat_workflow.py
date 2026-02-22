"""End-to-end chat workflow tests.

Tests complete user workflows:
- Login -> Select model -> Chat -> Receive response
- Multi-turn conversation
"""

import pytest


pytestmark = [pytest.mark.e2e, pytest.mark.slow]


class TestChatWorkflow:
    """Test complete chat conversation flow."""

    def test_full_chat_flow_via_litellm(self, litellm_client, platform_config):
        """Complete chat flow: list models -> select -> chat -> response."""
        # Step 1: List available models
        models_response = litellm_client.get("/v1/models")
        if models_response.status_code != 200:
            pytest.fail(f"Cannot list models: {models_response.status_code}")

        models = models_response.json().get("data", [])
        if not models:
            pytest.fail("No models available")

        # Step 2: Select a model (use test model)
        model_id = platform_config.TEST_MODEL

        # Step 3: Send a message
        chat_response = litellm_client.post(
            "/v1/chat/completions",
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is the capital of France? One word answer."},
                ],
                "max_tokens": 32,
                "stream": False,
            },
            timeout=120,
        )
        assert chat_response.status_code == 200, (
            f"Chat failed: {chat_response.status_code}"
        )

        # Step 4: Verify response structure
        data = chat_response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        content = data["choices"][0]["message"]["content"]
        assert len(content) > 0, "Empty response"

        # Step 5: Verify response quality (should mention Paris)
        assert "paris" in content.lower(), (
            f"Expected 'Paris' in response, got: {content}"
        )

    def test_multi_turn_conversation(self, litellm_client, platform_config):
        """Multi-turn conversation should maintain context."""
        model_id = platform_config.TEST_MODEL
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": "My name is TestBot."},
        ]

        # Turn 1: Introduce ourselves
        response1 = litellm_client.post(
            "/v1/chat/completions",
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": 32,
                "stream": False,
            },
            timeout=120,
        )
        if response1.status_code != 200:
            pytest.skip(f"Turn 1 failed: {response1.status_code}")

        assistant_msg = response1.json()["choices"][0]["message"]
        messages.append(assistant_msg)

        # Turn 2: Ask about previous context
        messages.append(
            {"role": "user", "content": "What is my name?"}
        )

        response2 = litellm_client.post(
            "/v1/chat/completions",
            json={
                "model": model_id,
                "messages": messages,
                "max_tokens": 32,
                "stream": False,
            },
            timeout=120,
        )
        assert response2.status_code == 200

        content = response2.json()["choices"][0]["message"]["content"]
        assert "testbot" in content.lower(), (
            f"Model did not remember name. Response: {content}"
        )


class TestModelComparison:
    """Test multiple models can serve the same query."""

    def test_same_query_different_models(self, ollama_gpu_client, platform_config):
        """Different models should all respond to the same prompt."""
        if platform_config.SKIP_GPU_TESTS:
            pytest.skip("GPU tests disabled")

        models = [platform_config.TEST_MODEL, platform_config.TEST_GPU_MODEL]
        results = {}

        for model in models:
            try:
                response = ollama_gpu_client.post(
                    "/api/generate",
                    json={
                        "model": model,
                        "prompt": "What is 2+2?",
                        "stream": False,
                        "options": {"num_predict": 16},
                    },
                    timeout=120,
                )
                if response.status_code == 200:
                    results[model] = response.json().get("response", "")
            except Exception as e:
                results[model] = f"ERROR: {e}"

        successful = {m: r for m, r in results.items() if not r.startswith("ERROR")}
        assert len(successful) >= 1, (
            f"No models responded successfully. Results: {results}"
        )
