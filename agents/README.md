# Agent Framework Development

Python-based multi-agent system with Rust performance optimizations.

## Setup

```bash
# Install Python dependencies
cd agents
pip install -e ".[dev]"

# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build Rust components
cd ../rust-agents
cargo build --release
```

## Running Tests

```bash
# Python tests
cd agents
pytest

# Rust tests
cd rust-agents
cargo test
```

## Code Quality

```bash
# Python
black agents tests
isort agents tests
mypy agents
ruff check agents tests
pylint agents

# Rust
cd rust-agents
cargo fmt
cargo clippy
```

## Usage

```python
from agents import ResearchAgent, DevelopmentAgent, Workflow, WorkflowOrchestrator
from agents.core.base import AgentConfig
from agents.core.task import TaskConfig

# Create agents
research_config = AgentConfig(name="researcher", agent_type="research")
research_agent = ResearchAgent(research_config)

dev_config = AgentConfig(name="developer", agent_type="development")
dev_agent = DevelopmentAgent(dev_config)

# Create workflow
workflow_config = WorkflowConfig(name="research-dev", description="Research and develop")
workflow = Workflow(workflow_config)

# Add agents
workflow.add_agent("research", research_agent)
workflow.add_agent("development", dev_agent)

# Add tasks
workflow.add_task(
    TaskConfig(name="research", description="Research topic", required_agents=["research"]),
    {"prompt": "Research Python async patterns"}
)

workflow.add_task(
    TaskConfig(
        name="develop",
        description="Implement feature",
        required_agents=["development"],
        dependencies=["research"]
    ),
    {"prompt": "Implement async handler", "context": {"language": "python"}}
)

# Execute
orchestrator = WorkflowOrchestrator()
result = await orchestrator.execute_workflow(workflow)
```

## Architecture

```
agents/
├── core/               # Base abstractions
│   ├── base.py        # Agent base class
│   ├── task.py        # Task management
│   └── workflow.py    # Workflow orchestration
├── specialized/        # Specialized agents
│   ├── research.py
│   ├── development.py
│   ├── code_review.py
│   ├── testing.py
│   └── documentation.py
└── workflows/          # Workflow configurations

rust-agents/            # Rust performance runtime
└── src/
    └── lib.rs         # Parallel execution engine

tests/                  # Comprehensive test suite
workflows/              # YAML workflow definitions
```
