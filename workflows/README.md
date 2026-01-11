# Multi-Agent Workflow Configurations

This directory contains YAML-based workflow configurations for common multi-agent scenarios.

## Available Workflows

- `research_and_develop.yaml` - Research a topic, then implement code
- `code_review_pipeline.yaml` - Develop → Review → Test → Document
- `full_development_cycle.yaml` - Complete SDLC with all agents
- `documentation_generator.yaml` - Analyze code and generate docs
- `test_generation.yaml` - Generate comprehensive test suites

## Workflow Format

```yaml
name: workflow-name
description: Workflow description
config:
  max_parallel_tasks: 5
  fail_fast: false
  timeout_seconds: 3600

agents:
  - type: research
    config:
      model: qwen2.5-coder:14b
      temperature: 0.7
  - type: development
    config:
      model: qwen2.5-coder:14b

tasks:
  - name: task-name
    description: Task description
    agent_types:
      - research
    priority: high
    dependencies: []
    payload:
      prompt: "Task prompt"
      context:
        key: value
```

## Usage

```python
from agents.workflows.loader import load_workflow

# Load workflow
workflow = load_workflow("workflows/research_and_develop.yaml")

# Execute
orchestrator = WorkflowOrchestrator()
result = await orchestrator.execute_workflow(workflow)
```
