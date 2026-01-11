"""
Self-Hosted AI Agents Framework.

A flexible multi-agent system for orchestrating AI workflows across
research, development, testing, and deployment tasks.
"""

__version__ = "0.1.0"
__author__ = "tzervas"

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus
from agents.core.workflow import Workflow, WorkflowConfig, WorkflowOrchestrator
from agents.specialized.research import ResearchAgent
from agents.specialized.development import DevelopmentAgent
from agents.specialized.code_review import CodeReviewAgent
from agents.specialized.testing import TestingAgent
from agents.specialized.documentation import DocumentationAgent
from agents.specialized.multimodal import (
    MultiModalAgent,
    EmbeddingAgent,
    FunctionCallingAgent,
)

__all__ = [
    # Core
    "Agent",
    "AgentConfig",
    "AgentResult",
    "AgentStatus",
    "Workflow",
    "WorkflowConfig",
    "WorkflowOrchestrator",
    # Specialized Agents
    "ResearchAgent",
    "DevelopmentAgent",
    "CodeReviewAgent",
    "TestingAgent",
    "DocumentationAgent",
    # Multi-Modal Agents
    "MultiModalAgent",
    "EmbeddingAgent",
    "FunctionCallingAgent",
]
