"""Google ADK Integration Module

Wraps existing specialized agents with Google ADK for:
- Unified agent orchestration
- Multi-agent workflows
- Agent evaluation and testing
- LiteLLM backend integration
"""

from agents.adk.base import ADKAgent, ADKConfig
from agents.adk.agents import (
    DevelopmentADKAgent,
    CodeReviewADKAgent,
    TestingADKAgent,
    DocumentationADKAgent,
    ResearchADKAgent,
)
from agents.adk.workflows import ADKWorkflow, WorkflowExecutor
from agents.adk.evaluator import AgentEvaluator

__all__ = [
    "ADKAgent",
    "ADKConfig",
    "DevelopmentADKAgent",
    "CodeReviewADKAgent",
    "TestingADKAgent",
    "DocumentationADKAgent",
    "ResearchADKAgent",
    "ADKWorkflow",
    "WorkflowExecutor",
    "AgentEvaluator",
]
