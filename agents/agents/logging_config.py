"""
Logging configuration for agent framework using loguru.
Provides structured logging with context and automatic JSON formatting.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

# Default log configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

DEFAULT_JSON_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}"


def setup_logging(
    level: str = DEFAULT_LOG_LEVEL,
    log_file: Optional[Path] = None,
    json_logs: bool = False,
    rotation: str = "100 MB",
    retention: str = "30 days",
    **extra_config: Any,
) -> None:
    """
    Configure structured logging for the agent framework.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs to stderr only
        json_logs: If True, format logs as JSON for machine parsing
        rotation: When to rotate log files (size-based or time-based)
        retention: How long to keep old log files
        **extra_config: Additional configuration passed to logger
    """
    # Remove default handler
    logger.remove()

    # Console handler with colors
    logger.add(
        sys.stderr,
        level=level,
        format=DEFAULT_LOG_FORMAT if not json_logs else DEFAULT_JSON_FORMAT,
        colorize=not json_logs,
        **extra_config,
    )

    # File handler with rotation if log_file specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            level=level,
            format=DEFAULT_JSON_FORMAT,
            rotation=rotation,
            retention=retention,
            compression="gz",
            serialize=json_logs,
            **extra_config,
        )
        logger.info(f"Logging to file: {log_file}")


def get_logger(name: str, **context: Any) -> "logger":
    """
    Get a logger instance with optional context.

    Args:
        name: Logger name (typically __name__)
        **context: Additional context to bind to logger

    Returns:
        Configured logger instance with bound context
    """
    return logger.bind(name=name, **context)


class LogContext:
    """Context manager for adding temporary context to logs."""

    def __init__(self, **context: Any):
        self.context = context
        self.token: Optional[int] = None

    def __enter__(self) -> "LogContext":
        self.token = logger.contextualize(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.token is not None:
            logger.remove(self.token)


def log_agent_execution(
    agent_id: str, agent_type: str, input_size: int, **metadata: Any
) -> LogContext:
    """
    Create log context for agent execution.

    Args:
        agent_id: Unique agent identifier
        agent_type: Type of agent (ResearchAgent, DevelopmentAgent, etc.)
        input_size: Size of input data in bytes
        **metadata: Additional metadata to log

    Returns:
        LogContext that can be used with 'with' statement
    """
    return LogContext(
        agent_id=agent_id,
        agent_type=agent_type,
        input_size=input_size,
        **metadata,
    )


def log_workflow_execution(workflow_id: str, task_count: int, **metadata: Any) -> LogContext:
    """
    Create log context for workflow execution.

    Args:
        workflow_id: Unique workflow identifier
        task_count: Number of tasks in workflow
        **metadata: Additional metadata to log

    Returns:
        LogContext that can be used with 'with' statement
    """
    return LogContext(
        workflow_id=workflow_id,
        task_count=task_count,
        **metadata,
    )


# Export main logger
__all__ = [
    "logger",
    "setup_logging",
    "get_logger",
    "LogContext",
    "log_agent_execution",
    "log_workflow_execution",
]
