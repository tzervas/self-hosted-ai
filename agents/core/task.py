"""Task management and execution."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskConfig:
    """Configuration for a task.

    Attributes:
        name: Task name
        description: Task description
        priority: Task priority
        timeout_seconds: Task timeout
        retry_on_failure: Whether to retry on failure
        max_retries: Maximum retry attempts
        required_agents: List of required agent types
        dependencies: List of task IDs this task depends on
        metadata: Additional task metadata
    """

    name: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: int = 300
    retry_on_failure: bool = True
    max_retries: int = 3
    required_agents: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result from task execution.

    Attributes:
        task_id: Unique task ID
        task_name: Task name
        status: Task status
        output: Task output
        error: Error message if failed
        agent_results: Results from agents that executed this task
        started_at: Start timestamp
        completed_at: Completion timestamp
        duration_seconds: Execution duration
        retry_count: Number of retries
    """

    task_id: str
    task_name: str
    status: TaskStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    agent_results: List[Any] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    retry_count: int = 0

    def is_success(self) -> bool:
        """Check if task completed successfully."""
        return self.status == TaskStatus.COMPLETED

    def is_failure(self) -> bool:
        """Check if task failed."""
        return self.status == TaskStatus.FAILED


class Task:
    """Represents a task to be executed by agents.

    Tasks encapsulate work items that can be assigned to one or more agents.
    They support dependencies, priorities, and retry logic.
    """

    def __init__(self, config: TaskConfig, payload: Dict[str, Any]):
        """Initialize task.

        Args:
            config: Task configuration
            payload: Task payload/input data
        """
        self.task_id = str(uuid.uuid4())
        self.config = config
        self.payload = payload
        self.status = TaskStatus.PENDING
        self.result: Optional[TaskResult] = None
        self.logger = logging.getLogger(f"{__name__}.{config.name}")

    def can_execute(self, completed_tasks: List[str]) -> bool:
        """Check if task dependencies are satisfied.

        Args:
            completed_tasks: List of completed task IDs

        Returns:
            True if all dependencies are satisfied
        """
        if not self.config.dependencies:
            return True
        return all(dep_id in completed_tasks for dep_id in self.config.dependencies)

    def mark_running(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.logger.info(f"Task {self.config.name} started")

    def mark_completed(self, output: Any, agent_results: List[Any]) -> TaskResult:
        """Mark task as completed.

        Args:
            output: Task output
            agent_results: Results from agents

        Returns:
            TaskResult instance
        """
        self.status = TaskStatus.COMPLETED
        self.result = TaskResult(
            task_id=self.task_id,
            task_name=self.config.name,
            status=TaskStatus.COMPLETED,
            output=output,
            agent_results=agent_results,
        )
        self.logger.info(f"Task {self.config.name} completed successfully")
        return self.result

    def mark_failed(self, error: str, agent_results: Optional[List[Any]] = None) -> TaskResult:
        """Mark task as failed.

        Args:
            error: Error message
            agent_results: Optional agent results

        Returns:
            TaskResult instance
        """
        self.status = TaskStatus.FAILED
        self.result = TaskResult(
            task_id=self.task_id,
            task_name=self.config.name,
            status=TaskStatus.FAILED,
            error=error,
            agent_results=agent_results or [],
        )
        self.logger.error(f"Task {self.config.name} failed: {error}")
        return self.result

    def should_retry(self) -> bool:
        """Check if task should be retried.

        Returns:
            True if task should be retried
        """
        if not self.config.retry_on_failure:
            return False
        if not self.result:
            return False
        return self.result.retry_count < self.config.max_retries
