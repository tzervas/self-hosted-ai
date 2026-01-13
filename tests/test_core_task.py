"""Tests for Task functionality."""

import pytest
from agents.core.task import Task, TaskConfig, TaskStatus, TaskPriority


class TestTask:
    """Test Task class."""

    def test_task_creation(self):
        """Test task creation."""
        config = TaskConfig(name="test-task", description="Test description")
        task = Task(config, {"data": "test"})
        
        assert task.status == TaskStatus.PENDING
        assert task.config.name == "test-task"
        assert task.payload["data"] == "test"

    def test_can_execute_no_dependencies(self):
        """Test execution check with no dependencies."""
        config = TaskConfig(name="test", description="Test")
        task = Task(config, {})
        
        assert task.can_execute([])

    def test_can_execute_with_satisfied_dependencies(self):
        """Test execution check with satisfied dependencies."""
        config = TaskConfig(
            name="test",
            description="Test",
            dependencies=["task-1", "task-2"]
        )
        task = Task(config, {})
        
        assert task.can_execute(["task-1", "task-2", "task-3"])

    def test_can_execute_with_unsatisfied_dependencies(self):
        """Test execution check with unsatisfied dependencies."""
        config = TaskConfig(
            name="test",
            description="Test",
            dependencies=["task-1", "task-2"]
        )
        task = Task(config, {})
        
        assert not task.can_execute(["task-1"])

    def test_mark_running(self):
        """Test marking task as running."""
        config = TaskConfig(name="test", description="Test")
        task = Task(config, {})
        
        task.mark_running()
        assert task.status == TaskStatus.RUNNING

    def test_mark_completed(self):
        """Test marking task as completed."""
        config = TaskConfig(name="test", description="Test")
        task = Task(config, {})
        
        result = task.mark_completed("output", [])
        assert task.status == TaskStatus.COMPLETED
        assert result.is_success()

    def test_mark_failed(self):
        """Test marking task as failed."""
        config = TaskConfig(name="test", description="Test")
        task = Task(config, {})
        
        result = task.mark_failed("error message")
        assert task.status == TaskStatus.FAILED
        assert result.is_failure()
