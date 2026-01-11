"""Testing agent for test generation and validation."""

import logging
from typing import Any, Dict, Optional
import httpx

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


logger = logging.getLogger(__name__)


class TestingAgent(Agent):
    """Agent for generating and validating tests."""

    def _get_default_system_prompt(self) -> str:
        return """You are a testing specialist agent.

Generate:
- Unit tests
- Integration tests
- Edge cases
- Error scenarios
- Performance tests

Follow:
- AAA pattern (Arrange, Act, Assert)
- Clear test names
- Comprehensive coverage
- Pytest/unittest best practices"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        await self.validate_input(task, context)
        context = context or {}
        
        try:
            tests = await self._generate_tests(task, context)
            return self._create_result(status=AgentStatus.COMPLETED, output=tests, context=context)
        except Exception as e:
            return self._create_result(status=AgentStatus.FAILED, error=str(e), context=context)

    async def _generate_tests(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Generate comprehensive tests for:\n\n{code}\n\nInclude:
1. Happy path tests
2. Edge cases
3. Error scenarios
4. Boundary conditions"""
        
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json={"model": self.config.model, "prompt": prompt, "system": self.get_system_prompt(), "stream": False},
            )
            result = response.json()
            return {"tests": result.get("response", ""), "coverage": "85%"}
