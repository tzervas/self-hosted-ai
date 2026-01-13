"""Tests for core agent functionality."""

import pytest
from datetime import datetime

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


class TestAgentConfig:
    """Test AgentConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AgentConfig(name="test", agent_type="test")
        assert config.name == "test"
        assert config.agent_type == "test"
        assert config.model == "qwen2.5-coder:14b"
        assert config.temperature == 0.7
        assert config.timeout_seconds == 300

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AgentConfig(
            name="custom",
            agent_type="custom",
            model="phi4:latest",
            temperature=0.5,
            timeout_seconds=600,
        )
        assert config.model == "phi4:latest"
        assert config.temperature == 0.5
        assert config.timeout_seconds == 600

    def test_metadata(self):
        """Test metadata storage."""
        config = AgentConfig(
            name="test",
            agent_type="test",
            metadata={"key1": "value1", "key2": "value2"},
        )
        assert config.metadata["key1"] == "value1"
        assert config.metadata["key2"] == "value2"


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_success_check(self):
        """Test success status check."""
        result = AgentResult(
            agent_id="test-id",
            agent_name="test",
            status=AgentStatus.COMPLETED,
        )
        assert result.is_success()
        assert not result.is_failure()

    def test_failure_check(self):
        """Test failure status check."""
        for status in [AgentStatus.FAILED, AgentStatus.TIMEOUT, AgentStatus.CANCELLED]:
            result = AgentResult(
                agent_id="test-id",
                agent_name="test",
                status=status,
            )
            assert result.is_failure()
            assert not result.is_success()

    def test_metrics_storage(self):
        """Test metrics storage."""
        metrics = {"duration": 1.5, "tokens": 1000}
        result = AgentResult(
            agent_id="test-id",
            agent_name="test",
            status=AgentStatus.COMPLETED,
            metrics=metrics,
        )
        assert result.metrics["duration"] == 1.5
        assert result.metrics["tokens"] == 1000


class TestAgent:
    """Test base Agent class."""

    def test_agent_initialization(self, agent_config):
        """Test agent initialization."""
        # We need a concrete implementation to test
        class TestAgent(Agent):
            def _get_default_system_prompt(self) -> str:
                return "Test prompt"

            async def execute(self, task: str, context=None):
                return self._create_result(AgentStatus.COMPLETED)

        agent = TestAgent(agent_config)
        assert agent.config == agent_config
        assert agent.agent_id is not None
        assert len(agent.agent_id) > 0

    @pytest.mark.asyncio
    async def test_validate_input_empty_task(self, agent_config):
        """Test input validation with empty task."""
        class TestAgent(Agent):
            def _get_default_system_prompt(self) -> str:
                return "Test prompt"

            async def execute(self, task: str, context=None):
                return self._create_result(AgentStatus.COMPLETED)

        agent = TestAgent(agent_config)
        with pytest.raises(ValueError, match="Task cannot be empty"):
            await agent.validate_input("")

    @pytest.mark.asyncio
    async def test_validate_input_valid_task(self, agent_config):
        """Test input validation with valid task."""
        class TestAgent(Agent):
            def _get_default_system_prompt(self) -> str:
                return "Test prompt"

            async def execute(self, task: str, context=None):
                return self._create_result(AgentStatus.COMPLETED)

        agent = TestAgent(agent_config)
        result = await agent.validate_input("Valid task")
        assert result is True

    def test_system_prompt_custom(self, agent_config):
        """Test custom system prompt."""
        config = AgentConfig(
            name="test",
            agent_type="test",
            system_prompt="Custom prompt",
        )

        class TestAgent(Agent):
            def _get_default_system_prompt(self) -> str:
                return "Default prompt"

            async def execute(self, task: str, context=None):
                return self._create_result(AgentStatus.COMPLETED)

        agent = TestAgent(config)
        assert agent.get_system_prompt() == "Custom prompt"

    def test_system_prompt_default(self, agent_config):
        """Test default system prompt."""
        class TestAgent(Agent):
            def _get_default_system_prompt(self) -> str:
                return "Default prompt"

            async def execute(self, task: str, context=None):
                return self._create_result(AgentStatus.COMPLETED)

        agent = TestAgent(agent_config)
        assert agent.get_system_prompt() == "Default prompt"
