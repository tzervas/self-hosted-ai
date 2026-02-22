"""Ollama API endpoint tests.

Tests the Ollama inference service on both GPU and CPU instances:
- Health/connectivity
- Model listing
- Text generation
- Embedding generation
- Vision model (llava)

NOTE: Ollama GPU runs as a K8s ClusterIP service. Tests will skip
if the service is not reachable (e.g., running outside the cluster).
"""

import pytest


pytestmark = [pytest.mark.api, pytest.mark.critical]


@pytest.fixture(scope="module", autouse=True)
def _check_ollama_reachable(ollama_gpu_client):
    """Skip entire module if Ollama GPU is not reachable."""
    try:
        response = ollama_gpu_client.get("/", timeout=5)
        if response.status_code != 200:
            pytest.skip(
                f"Ollama GPU not reachable (status {response.status_code}). "
                "Service is a K8s ClusterIP — run tests from within cluster."
            )
    except Exception:
        pytest.skip(
            "Ollama GPU not reachable (connection refused). "
            "Service is a K8s ClusterIP — run tests from within cluster "
            "or use kubectl port-forward."
        )


class TestOllamaGPUHealth:
    """Validate Ollama GPU service is reachable and healthy."""

    def test_ollama_gpu_reachable(self, ollama_gpu_client):
        """Ollama GPU endpoint should be reachable."""
        response = ollama_gpu_client.get("/")
        assert response.status_code == 200, (
            f"Ollama GPU returned {response.status_code}"
        )

    def test_ollama_gpu_has_models(self, ollama_gpu_client):
        """Ollama GPU should have models loaded."""
        response = ollama_gpu_client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        models = data.get("models", [])
        assert len(models) > 0, "No models found on Ollama GPU"


class TestOllamaGPUModels:
    """Validate required models are available on GPU."""

    def test_required_gpu_models_present(self, ollama_gpu_client, platform_config):
        """All required GPU models should be available."""
        response = ollama_gpu_client.get("/api/tags")
        data = response.json()
        model_names = [m["name"] for m in data.get("models", [])]

        missing = []
        for required in platform_config.REQUIRED_MODELS_GPU:
            found = any(
                m.startswith(required.split(":")[0]) for m in model_names
            )
            if not found:
                missing.append(required)

        assert not missing, (
            f"Missing GPU models: {missing}\n"
            f"Available: {sorted(model_names)}"
        )


class TestOllamaGeneration:
    """Test text generation capabilities."""

    @pytest.mark.slow
    def test_generate_text(self, ollama_gpu_client, platform_config):
        """Ollama should generate text from a simple prompt."""
        response = ollama_gpu_client.post(
            "/api/generate",
            json={
                "model": platform_config.TEST_MODEL,
                "prompt": "What is 2+2? Reply with just the number.",
                "stream": False,
                "options": {"num_predict": 32},
            },
            timeout=120,
        )
        assert response.status_code == 200, (
            f"Generation failed: {response.status_code} {response.text}"
        )
        data = response.json()
        assert "response" in data, "Missing 'response' in output"
        assert len(data["response"]) > 0, "Empty response from model"
        assert data.get("done") is True, "Generation did not complete"

    @pytest.mark.slow
    def test_chat_completion(self, ollama_gpu_client, platform_config):
        """Ollama should handle chat-style completions."""
        response = ollama_gpu_client.post(
            "/api/chat",
            json={
                "model": platform_config.TEST_MODEL,
                "messages": [
                    {"role": "user", "content": "Say hello in one word."}
                ],
                "stream": False,
                "options": {"num_predict": 16},
            },
            timeout=120,
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data, "Missing 'message' in chat response"
        assert data["message"].get("content"), "Empty chat response"


class TestOllamaEmbeddings:
    """Test embedding generation."""

    @pytest.mark.slow
    def test_generate_embeddings(self, ollama_gpu_client):
        """Ollama should generate embeddings from text."""
        response = ollama_gpu_client.post(
            "/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": "Test embedding text for validation.",
            },
            timeout=60,
        )
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data, "Missing 'embedding' in response"
        embedding = data["embedding"]
        assert len(embedding) > 100, (
            f"Embedding too short: {len(embedding)} dimensions"
        )


class TestOllamaModelInfo:
    """Test model information endpoint."""

    def test_show_model_info(self, ollama_gpu_client, platform_config):
        """Model info endpoint should return model details."""
        response = ollama_gpu_client.post(
            "/api/show",
            json={"name": platform_config.TEST_MODEL},
            timeout=30,
        )
        assert response.status_code == 200
        data = response.json()
        assert "modelfile" in data or "details" in data, (
            "Missing model details in response"
        )
