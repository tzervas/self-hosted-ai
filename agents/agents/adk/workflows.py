"""ADK Workflow Execution

Multi-agent workflow orchestration using Google ADK patterns.
Supports parallel execution, dependencies, and data flow between agents.
"""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from loguru import logger

from agents.adk.base import ADKAgent, ADKConfig, ADKResult, AgentPriority
from agents.adk.agents import (
    DevelopmentADKAgent,
    CodeReviewADKAgent,
    TestingADKAgent,
    DocumentationADKAgent,
    ResearchADKAgent,
)


@dataclass
class WorkflowTask:
    """A task within a workflow."""
    id: str
    agent_type: str
    prompt: str
    depends_on: List[str] = field(default_factory=list)
    model: Optional[str] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class WorkflowResult:
    """Result of workflow execution."""
    workflow_name: str
    status: str
    outputs: Dict[str, Any]
    duration_seconds: float
    task_results: Dict[str, ADKResult]
    errors: List[str] = field(default_factory=list)


class ADKWorkflow:
    """Workflow definition and parser."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        tasks: Optional[List[WorkflowTask]] = None
    ):
        self.name = name
        self.description = description
        self.tasks = tasks or []
        self.logger = logger.bind(workflow=name)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "ADKWorkflow":
        """Load workflow from YAML file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            Parsed ADKWorkflow instance
        """
        with open(path) as f:
            data = yaml.safe_load(f)
        
        tasks = []
        for task_data in data.get("tasks", []):
            tasks.append(WorkflowTask(
                id=task_data["id"],
                agent_type=task_data.get("agent_type", "development"),
                prompt=task_data["prompt"],
                depends_on=task_data.get("depends_on", []),
                model=task_data.get("model"),
                temperature=task_data.get("temperature"),
                timeout=task_data.get("timeout"),
                context=task_data.get("context", {})
            ))
        
        return cls(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            tasks=tasks
        )
    
    def validate(self) -> List[str]:
        """Validate workflow for issues.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        task_ids = {t.id for t in self.tasks}
        
        for task in self.tasks:
            for dep in task.depends_on:
                if dep not in task_ids:
                    errors.append(f"Task '{task.id}' depends on unknown task '{dep}'")
        
        # Check for cycles
        visited: Set[str] = set()
        path: Set[str] = set()
        
        def has_cycle(task_id: str) -> bool:
            if task_id in path:
                return True
            if task_id in visited:
                return False
            
            visited.add(task_id)
            path.add(task_id)
            
            task = next((t for t in self.tasks if t.id == task_id), None)
            if task:
                for dep in task.depends_on:
                    if has_cycle(dep):
                        return True
            
            path.remove(task_id)
            return False
        
        for task in self.tasks:
            if has_cycle(task.id):
                errors.append(f"Circular dependency detected involving task '{task.id}'")
                break
        
        return errors


class WorkflowExecutor:
    """Executes ADK workflows with proper dependency handling."""
    
    AGENT_CLASSES = {
        "development": DevelopmentADKAgent,
        "code_review": CodeReviewADKAgent,
        "testing": TestingADKAgent,
        "documentation": DocumentationADKAgent,
        "research": ResearchADKAgent,
    }
    
    def __init__(
        self,
        litellm_url: str,
        litellm_api_key: str,
        default_model: str = "qwen2.5-coder:14b",
        priority: AgentPriority = AgentPriority.NORMAL
    ):
        """Initialize workflow executor.
        
        Args:
            litellm_url: LiteLLM proxy URL
            litellm_api_key: API key
            default_model: Default model to use
            priority: Default queue priority
        """
        self.litellm_url = litellm_url
        self.litellm_api_key = litellm_api_key
        self.default_model = default_model
        self.priority = priority
        self.logger = logger.bind(component="workflow_executor")
    
    def _create_agent(self, task: WorkflowTask, http_client) -> ADKAgent:
        """Create agent for a task.
        
        Args:
            task: Workflow task
            http_client: HTTP client to use
            
        Returns:
            Configured ADKAgent instance
        """
        agent_class = self.AGENT_CLASSES.get(task.agent_type, DevelopmentADKAgent)
        
        config = ADKConfig(
            name=f"{task.agent_type}_{task.id}",
            model=task.model or self.default_model,
            litellm_url=self.litellm_url,
            litellm_api_key=self.litellm_api_key,
            temperature=task.temperature or 0.7,
            timeout=task.timeout or 300,
            priority=self.priority
        )
        
        return agent_class(config, http_client)
    
    def _substitute_variables(
        self,
        prompt: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, str]
    ) -> str:
        """Substitute variables in prompt.
        
        Args:
            prompt: Original prompt with {{variables}}
            inputs: Workflow inputs
            outputs: Previous task outputs
            
        Returns:
            Prompt with substitutions made
        """
        result = prompt
        
        # Substitute inputs
        for key, value in inputs.items():
            result = result.replace(f"{{{{ inputs.{key} }}}}", str(value))
        
        # Substitute outputs
        for key, value in outputs.items():
            result = result.replace(f"{{{{ outputs.{key} }}}}", str(value))
        
        return result
    
    async def execute(
        self,
        workflow: ADKWorkflow,
        inputs: Dict[str, Any] = None
    ) -> WorkflowResult:
        """Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            inputs: Input parameters
            
        Returns:
            WorkflowResult with all outputs
        """
        import httpx
        
        inputs = inputs or {}
        outputs: Dict[str, str] = {}
        task_results: Dict[str, ADKResult] = {}
        errors: List[str] = []
        completed: Set[str] = set()
        
        start_time = time.time()
        self.logger.info(f"Starting workflow: {workflow.name}")
        
        # Validate workflow
        validation_errors = workflow.validate()
        if validation_errors:
            return WorkflowResult(
                workflow_name=workflow.name,
                status="error",
                outputs={},
                duration_seconds=0,
                task_results={},
                errors=validation_errors
            )
        
        async with httpx.AsyncClient(timeout=600) as http_client:
            while len(completed) < len(workflow.tasks):
                # Find tasks ready to execute
                ready_tasks = [
                    task for task in workflow.tasks
                    if task.id not in completed
                    and all(dep in completed for dep in task.depends_on)
                ]
                
                if not ready_tasks:
                    errors.append("Workflow stalled - no tasks ready to execute")
                    break
                
                # Execute ready tasks in parallel
                async def execute_task(task: WorkflowTask) -> tuple:
                    agent = self._create_agent(task, http_client)
                    prompt = self._substitute_variables(task.prompt, inputs, outputs)
                    
                    self.logger.info(f"Executing task: {task.id}")
                    result = await agent.execute(prompt, task.context)
                    
                    return task.id, result
                
                results = await asyncio.gather(
                    *[execute_task(t) for t in ready_tasks],
                    return_exceptions=True
                )
                
                for result in results:
                    if isinstance(result, Exception):
                        errors.append(str(result))
                        continue
                    
                    task_id, adk_result = result
                    task_results[task_id] = adk_result
                    
                    if adk_result.is_success:
                        outputs[task_id] = adk_result.output or ""
                        completed.add(task_id)
                        self.logger.info(f"Task completed: {task_id}")
                    else:
                        errors.append(f"Task {task_id} failed: {adk_result.error}")
                        # Continue with other tasks that don't depend on this one
                        completed.add(task_id)
        
        duration = time.time() - start_time
        status = "completed" if not errors else "completed_with_errors" if outputs else "failed"
        
        self.logger.info(f"Workflow {workflow.name} {status} in {duration:.2f}s")
        
        return WorkflowResult(
            workflow_name=workflow.name,
            status=status,
            outputs=outputs,
            duration_seconds=duration,
            task_results=task_results,
            errors=errors
        )
    
    async def execute_from_file(
        self,
        workflow_path: Path,
        inputs: Dict[str, Any] = None
    ) -> WorkflowResult:
        """Execute workflow from YAML file.
        
        Args:
            workflow_path: Path to workflow YAML
            inputs: Input parameters
            
        Returns:
            WorkflowResult
        """
        workflow = ADKWorkflow.from_yaml(workflow_path)
        return await self.execute(workflow, inputs)
