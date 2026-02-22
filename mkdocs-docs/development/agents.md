---
title: Agent Framework
description: Python and Rust agent development
---

# Agent Framework

## Two Types of Agents

| Type | Language | Use Case |
|------|----------|----------|
| **Python Agents** (`agents/`) | Python | Runtime task execution, API orchestration |
| **Claude Sub-Agents** (`.claude/agents/`) | AI-powered | Development, testing, deployment workflows |

## Python Agent Framework

### Structure

```
agents/
├── core/
│   ├── base.py         # Agent, AgentConfig, AgentResult
│   ├── task.py          # Task management
│   └── workflow.py      # Workflow orchestration
├── specialized/
│   ├── researcher.py
│   ├── developer.py
│   ├── code_reviewer.py
│   ├── testing.py
│   └── documentation.py
├── logging_config.py    # Structured logging
└── metrics.py           # Prometheus metrics
```

### Creating a New Agent

```python
from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus

class MyCustomAgent(Agent):
    """Custom agent for specific task."""

    @property
    def system_prompt(self) -> str:
        return "You are a specialized AI assistant that..."

    async def execute(self, input_data: str) -> AgentResult:
        prompt = f"{self.system_prompt}\n\nTask: {input_data}"
        response = await self._call_llm(prompt)

        return AgentResult(
            status=AgentStatus.COMPLETED,
            output=response,
        )
```

### Running Tests

```bash
cd agents
pytest tests/ -v
pytest tests/ --cov=agents --cov-report=html
```

## Rust Agent Runtime

```
rust-agents/
├── src/
│   ├── agent_runtime.rs    # Core runtime
│   ├── python_bindings.rs  # PyO3 FFI
│   └── lib.rs
├── Cargo.toml
└── rustfmt.toml
```

```bash
cd rust-agents
cargo build --release
cargo test
cargo clippy -- -D warnings
```

## Claude Sub-Agents

Sub-agents in `.claude/agents/` are AI-powered workflows:

| Agent | Model | Purpose |
|-------|-------|---------|
| k8s-validator | Haiku | Fast manifest validation |
| python-test-runner | Haiku | Run pytest, report failures |
| argocd-sync-monitor | Sonnet | Monitor ArgoCD deployments |
