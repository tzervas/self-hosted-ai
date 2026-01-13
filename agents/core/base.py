"""Base agent abstractions and interfaces."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for an agent instance.

    Attributes:
        name: Human-readable agent name
        agent_type: Type/category of agent
        model: LLM model to use (e.g., 'qwen2.5-coder:14b')
        ollama_url: Ollama API endpoint
        temperature: Model temperature (0.0-2.0)
        max_tokens: Maximum tokens for generation
        timeout_seconds: Execution timeout
        retry_attempts: Number of retry attempts on failure
        context_window: Maximum context window size
        system_prompt: Custom system prompt
        metadata: Additional configuration key-value pairs
    """

    name: str
    agent_type: str
    model: str = "qwen2.5-coder:14b"
    ollama_url: str = "http://192.168.1.99:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_seconds: int = 300
    retry_attempts: int = 3
    context_window: int = 32768
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from agent execution.

    Attributes:
        agent_id: Unique agent execution ID
        agent_name: Name of the agent
        status: Execution status
        output: Agent output/result
        error: Error message if failed
        metrics: Performance metrics
        context: Execution context and state
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        duration_seconds: Execution duration
    """

    agent_id: str
    agent_name: str
    status: AgentStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == AgentStatus.COMPLETED

    def is_failure(self) -> bool:
        """Check if execution failed."""
        return self.status in (AgentStatus.FAILED, AgentStatus.TIMEOUT, AgentStatus.CANCELLED)


class Agent(ABC):
    """Abstract base class for all agents.

    All specialized agents must inherit from this class and implement
    the execute() method.
    """

    def __init__(self, config: AgentConfig):
        """Initialize agent with configuration.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.logger = logging.getLogger(f"{__name__}.{config.name}")

    @abstractmethod
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent's task.

        Args:
            task: Task description or prompt
            context: Optional execution context

        Returns:
            AgentResult containing execution outcome

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement execute()")

    def _create_result(
        self,
        status: AgentStatus,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Create an AgentResult instance.

        Args:
            status: Execution status
            output: Agent output
            error: Error message
            metrics: Performance metrics
            context: Execution context

        Returns:
            Configured AgentResult instance
        """
        return AgentResult(
            agent_id=self.agent_id,
            agent_name=self.config.name,
            status=status,
            output=output,
            error=error,
            metrics=metrics or {},
            context=context or {},
        )

    async def validate_input(self, task: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Validate input before execution.

        Args:
            task: Task to validate
            context: Execution context

        Returns:
            True if input is valid

        Raises:
            ValueError: If input validation fails
        """
        if not task or not task.strip():
            raise ValueError("Task cannot be empty")
        return True

    def get_system_prompt(self) -> str:
        """Get system prompt for this agent.

        Returns:
            System prompt string
        """
        if self.config.system_prompt:
            return self.config.system_prompt
        return self._get_default_system_prompt()

    @abstractmethod
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for this agent type.

        Returns:
            Default system prompt string

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement _get_default_system_prompt()")
