"""
Prometheus metrics for agent framework.
Tracks agent execution times, success rates, and workflow performance.
"""

import logging
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, Info, Summary, start_http_server

# Configure logger
logger = logging.getLogger(__name__)

# Configuration flag for Prometheus export
prometheus_enabled = False

# Agent execution metrics
AGENT_EXECUTIONS = Counter(
    "agent_executions_total",
    "Total number of agent executions",
    ["agent_type", "status"],
)

AGENT_EXECUTION_TIME = Histogram(
    "agent_execution_seconds",
    "Time spent executing agents",
    ["agent_type", "status"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

AGENT_INPUT_SIZE = Histogram(
    "agent_input_size_bytes",
    "Size of agent input data",
    ["agent_type"],
    buckets=[100, 1000, 10000, 100000, 1000000],
)

AGENT_OUTPUT_SIZE = Histogram(
    "agent_output_size_bytes",
    "Size of agent output in bytes",
    ["agent_type"],
)

AGENT_EXECUTION_TIME = Histogram(
    "agent_execution_seconds",
    "Agent execution time in seconds",
    ["agent_type", "status"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf")),
)

AGENT_EXECUTION_COUNT = Counter(
    "agent_executions_total",
    "Total number of agent executions",
    ["agent_type", "status"],
)

WORKFLOW_EXECUTION_COUNT = Counter(
    "workflow_executions_total",
    "Total number of workflow executions",
    ["workflow_id", "status"],
)

WORKFLOW_TASK_COUNT = Histogram(
    "workflow_task_count",
    "Number of tasks per workflow",
    buckets=[1, 2, 5, 10, 20, 50, 100],
)

WORKFLOW_DURATION = Histogram(
    "workflow_execution_seconds",
    "Workflow execution time in seconds",
    ["workflow_id", "status"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800],
)


class MetricsCollector:
    """Collect and export metrics for agent execution."""

    def __init__(self) -> None:
        """Initialize metrics collectors."""
        self.agent_execution_counter = Counter(
            "agent_executions_total",
            "Total number of agent executions",
            ["agent_type", "status"],
        )

        self.agent_execution_time = Histogram(
            "agent_execution_seconds",
            "Agent execution time in seconds",
            ["agent_type", "agent_id"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
        )

        self.workflow_execution_time = Histogram(
            "workflow_execution_seconds",
            "Time spent executing workflows",
            ["workflow_id", "status"],
        )

        self.task_execution_time = Histogram(
            "task_execution_seconds",
            "Task execution time",
            ["task_id", "agent_type", "status"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
        )

        self.agent_execution_counter = Counter(
            "agent_executions_total",
            "Total number of agent executions",
            ["agent_type", "status"],
        )

        self.workflow_execution_counter = Counter(
            "workflow_executions_total",
            "Total workflow executions",
            ["workflow_id", "status"],
        )

        self.task_duration = Histogram(
            "agent_task_duration_seconds",
            "Time spent executing agent tasks",
            ["agent_type", "status"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )

        self.task_counter = Counter(
            "agent_tasks_total",
            "Total number of agent tasks executed",
            ["agent_type", "status"],
        )

        self.workflow_counter = Counter(
            "workflow_executions_total", "Total workflow executions", ["workflow_id", "status"]
        )

        self.workflow_duration = Histogram(
            "workflow_execution_seconds",
            "Workflow execution time in seconds",
            ["workflow_id"],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600],
        )

    def record_agent_execution(
        self, agent_id: str, agent_type: str, duration: float, status: str, **labels: Any
    ) -> None:
        """Record metrics for an agent execution."""
        self.agent_executions.labels(
            agent_id=agent_id, agent_type=agent_type, status=status
        ).inc()
        self.execution_duration.labels(agent_type=agent_type, status=status).observe(duration)
        
        # Update counters
        if status == "completed":
            self.successful_executions.labels(agent_type=agent_type).inc()
        else:
            self.failed_executions.labels(agent_type=agent_type, error=status).inc()

    def record_workflow_execution(
        self, workflow_id: str, task_count: int, duration: float, success: bool
    ) -> None:
        """Record workflow execution metrics."""
        self.workflow_executions.inc()
        self.workflow_duration.observe(duration)

        if not success:
            self.workflow_failures.labels(workflow_id=workflow_id).inc()

        logger.info(
            "Workflow execution completed",
            workflow_id=workflow_id,
            task_count=task_count,
            success=success,
            duration=duration,
        )


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def setup_metrics(
    enable_prometheus: bool = True,
    prometheus_port: int = 9090,
    export_interval: int = 60,
) -> None:
    """
    Configure metrics collection for the agent framework.

    Args:
        enable_prometheus: Enable Prometheus metrics export
        prometheus_port: Port for Prometheus metrics server
        export_interval: Interval for exporting metrics (seconds)
    """
    if prometheus_enabled:
        # Start HTTP server for Prometheus scraping
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")


# Export main functions
__all__ = [
    "MetricsCollector",
    "get_metrics_collector",
    "setup_metrics",
    "AGENT_EXECUTIONS",
    "AGENT_EXECUTION_TIME",
    "WORKFLOW_EXECUTION_COUNT",
    "WORKFLOW_DURATION",
]
