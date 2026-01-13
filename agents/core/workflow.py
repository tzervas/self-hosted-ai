"""Workflow orchestration for multi-agent collaboration."""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from agents.core.base import Agent, AgentResult
from agents.core.task import Task, TaskConfig, TaskResult, TaskStatus


logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL_SUCCESS = "partial_success"


@dataclass
class WorkflowConfig:
    """Configuration for a workflow.

    Attributes:
        name: Workflow name
        description: Workflow description
        max_parallel_tasks: Maximum concurrent tasks
        fail_fast: Stop on first failure
        timeout_seconds: Workflow timeout
        retry_failed_tasks: Retry failed tasks
        collect_metrics: Collect detailed metrics
        metadata: Additional workflow metadata
    """

    name: str
    description: str
    max_parallel_tasks: int = 5
    fail_fast: bool = False
    timeout_seconds: int = 3600
    retry_failed_tasks: bool = True
    collect_metrics: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result from workflow execution.

    Attributes:
        workflow_id: Unique workflow ID
        workflow_name: Workflow name
        status: Workflow status
        task_results: Results from all tasks
        metrics: Workflow metrics
        started_at: Start timestamp
        completed_at: Completion timestamp
        duration_seconds: Execution duration
    """

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    task_results: List[TaskResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    def get_successful_tasks(self) -> List[TaskResult]:
        """Get all successful task results."""
        return [r for r in self.task_results if r.is_success()]

    def get_failed_tasks(self) -> List[TaskResult]:
        """Get all failed task results."""
        return [r for r in self.task_results if r.is_failure()]

    def success_rate(self) -> float:
        """Calculate success rate."""
        if not self.task_results:
            return 0.0
        successful = len(self.get_successful_tasks())
        return successful / len(self.task_results)


class Workflow:
    """Represents a multi-agent workflow.

    A workflow is a directed acyclic graph (DAG) of tasks that can be
    executed by different agents. Tasks can have dependencies and are
    executed in the correct order.
    """

    def __init__(self, config: WorkflowConfig):
        """Initialize workflow.

        Args:
            config: Workflow configuration
        """
        self.workflow_id = str(uuid.uuid4())
        self.config = config
        self.tasks: List[Task] = []
        self.agents: Dict[str, Agent] = {}
        self.status = WorkflowStatus.PENDING
        self.logger = logging.getLogger(f"{__name__}.{config.name}")

    def add_task(self, task_config: TaskConfig, payload: Dict[str, Any]) -> Task:
        """Add a task to the workflow.

        Args:
            task_config: Task configuration
            payload: Task payload

        Returns:
            Created Task instance
        """
        task = Task(task_config, payload)
        self.tasks.append(task)
        self.logger.debug(f"Added task: {task_config.name}")
        return task

    def add_agent(self, agent_type: str, agent: Agent) -> None:
        """Register an agent for this workflow.

        Args:
            agent_type: Agent type identifier
            agent: Agent instance
        """
        self.agents[agent_type] = agent
        self.logger.debug(f"Registered agent: {agent_type}")

    def validate(self) -> bool:
        """Validate workflow configuration.

        Returns:
            True if workflow is valid

        Raises:
            ValueError: If workflow validation fails
        """
        if not self.tasks:
            raise ValueError("Workflow must have at least one task")

        # Check for circular dependencies
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = next((t for t in self.tasks if t.task_id == task_id), None)
            if task:
                for dep_id in task.config.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        for task in self.tasks:
            if task.task_id not in visited:
                if has_cycle(task.task_id):
                    raise ValueError("Workflow contains circular dependencies")

        # Validate required agents are registered
        required_agents = set()
        for task in self.tasks:
            required_agents.update(task.config.required_agents)

        missing_agents = required_agents - set(self.agents.keys())
        if missing_agents:
            raise ValueError(f"Missing required agents: {missing_agents}")

        return True


class WorkflowOrchestrator:
    """Orchestrates execution of multi-agent workflows.

    The orchestrator manages task scheduling, agent assignment,
    error handling, and workflow state.
    """

    def __init__(self):
        """Initialize orchestrator."""
        self.logger = logging.getLogger(__name__)
        self.active_workflows: Dict[str, Workflow] = {}

    async def execute_workflow(self, workflow: Workflow) -> WorkflowResult:
        """Execute a workflow.

        Args:
            workflow: Workflow to execute

        Returns:
            WorkflowResult with execution outcome
        """
        self.logger.info(f"Starting workflow: {workflow.config.name}")
        start_time = datetime.now()

        try:
            # Validate workflow
            workflow.validate()

            workflow.status = WorkflowStatus.RUNNING
            self.active_workflows[workflow.workflow_id] = workflow

            # Execute tasks
            task_results = await self._execute_tasks(workflow)

            # Determine workflow status
            failed_tasks = [r for r in task_results if r.is_failure()]
            if not failed_tasks:
                status = WorkflowStatus.COMPLETED
            elif len(failed_tasks) < len(task_results):
                status = WorkflowStatus.PARTIAL_SUCCESS
            else:
                status = WorkflowStatus.FAILED

            workflow.status = status

            # Create result
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = WorkflowResult(
                workflow_id=workflow.workflow_id,
                workflow_name=workflow.config.name,
                status=status,
                task_results=task_results,
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
            )

            self.logger.info(
                f"Workflow {workflow.config.name} completed with status {status} "
                f"in {duration:.2f}s. Success rate: {result.success_rate():.1%}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Workflow {workflow.config.name} failed: {e}", exc_info=True)
            workflow.status = WorkflowStatus.FAILED

            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                workflow_name=workflow.config.name,
                status=WorkflowStatus.FAILED,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        finally:
            # Cleanup
            self.active_workflows.pop(workflow.workflow_id, None)

    async def _execute_tasks(self, workflow: Workflow) -> List[TaskResult]:
        """Execute workflow tasks respecting dependencies.

        Args:
            workflow: Workflow containing tasks

        Returns:
            List of task results
        """
        completed_task_ids: List[str] = []
        task_results: List[TaskResult] = []
        pending_tasks = workflow.tasks.copy()

        while pending_tasks:
            # Find tasks ready to execute
            ready_tasks = [t for t in pending_tasks if t.can_execute(completed_task_ids)]

            if not ready_tasks:
                # No tasks ready and some pending = deadlock
                if pending_tasks:
                    self.logger.error("Deadlock detected: circular dependencies or missing tasks")
                break

            # Execute ready tasks (respecting parallelism limit)
            batch_size = min(len(ready_tasks), workflow.config.max_parallel_tasks)
            batch = ready_tasks[:batch_size]

            results = await asyncio.gather(
                *[self._execute_task(task, workflow) for task in batch],
                return_exceptions=True,
            )

            for task, result in zip(batch, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Task {task.config.name} raised exception: {result}")
                    result = task.mark_failed(str(result))
                
                # Type guard: only append and process valid TaskResult objects
                if not isinstance(result, Exception):
                    task_results.append(result)
                    
                    if result.is_success():
                        completed_task_ids.append(task.task_id)
                    elif workflow.config.fail_fast:
                        self.logger.warning("Fail-fast enabled, stopping workflow due to task failure")
                        return task_results

                pending_tasks.remove(task)

        return task_results

    async def _execute_task(self, task: Task, workflow: Workflow) -> TaskResult:
        """Execute a single task.

        Args:
            task: Task to execute
            workflow: Parent workflow

        Returns:
            TaskResult
        """
        task.mark_running()
        self.logger.info(f"Executing task: {task.config.name}")

        try:
            # Get agents for this task
            task_agents = [
                workflow.agents[agent_type]
                for agent_type in task.config.required_agents
                if agent_type in workflow.agents
            ]

            if not task_agents:
                return task.mark_failed("No agents available for task")

            # Execute with each agent
            agent_results: List[AgentResult] = []
            for agent in task_agents:
                result = await agent.execute(
                    task=task.payload.get("prompt", ""),
                    context=task.payload.get("context", {}),
                )
                agent_results.append(result)

            # Combine results
            successful_results = [r for r in agent_results if r.is_success()]
            if successful_results:
                output = {
                    "results": [r.output for r in successful_results],
                    "primary": successful_results[0].output,
                }
                return task.mark_completed(output, agent_results)
            else:
                errors = [r.error for r in agent_results if r.error]
                return task.mark_failed("; ".join(errors), agent_results)

        except Exception as e:
            self.logger.error(f"Task {task.config.name} failed: {e}", exc_info=True)
            return task.mark_failed(str(e))
