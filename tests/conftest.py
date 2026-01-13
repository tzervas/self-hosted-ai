"""Pytest fixtures for agent testing."""

import pytest
from unittest.mock import AsyncMock, Mock
import httpx

from agents.core.base import AgentConfig
from agents.specialized.research import ResearchAgent
from agents.specialized.development import DevelopmentAgent
from agents.specialized.code_review import CodeReviewAgent
from agents.specialized.testing import TestingAgent
from agents.specialized.documentation import DocumentationAgent


@pytest.fixture
def agent_config():
    """Create a default agent configuration for testing."""
    return AgentConfig(
        name="test-agent",
        agent_type="test",
        model="qwen2.5-coder:14b",
        ollama_url="http://localhost:11434",
        temperature=0.7,
        timeout_seconds=60,
    )


@pytest.fixture
def research_agent(agent_config):
    """Create a Research agent instance."""
    return ResearchAgent(agent_config)


@pytest.fixture
def development_agent(agent_config):
    """Create a Development agent instance."""
    return DevelopmentAgent(agent_config)


@pytest.fixture
def code_review_agent(agent_config):
    """Create a Code Review agent instance."""
    return CodeReviewAgent(agent_config)


@pytest.fixture
def testing_agent(agent_config):
    """Create a Testing agent instance."""
    return TestingAgent(agent_config)


@pytest.fixture
def documentation_agent(agent_config):
    """Create a Documentation agent instance."""
    return DocumentationAgent(agent_config)


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "response": "This is a mock response from Ollama",
        "created_at": "2026-01-10T12:00:00Z",
        "model": "qwen2.5-coder:14b",
        "done": True,
    }


@pytest.fixture
def mock_httpx_client(mock_ollama_response):
    """Mock httpx AsyncClient for API calls."""
    mock_response = Mock()
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = Mock()
    
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    return mock_client


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''


@pytest.fixture
def sample_rust_code():
    """Sample Rust code for testing."""
    return '''fn fibonacci(n: u32) -> u32 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}
'''
