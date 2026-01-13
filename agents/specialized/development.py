"""Development agent for code generation and implementation."""

import logging
from typing import Any, Dict, Optional
import httpx

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


logger = logging.getLogger(__name__)


class DevelopmentAgent(Agent):
    """Agent specialized in software development and code generation.

    Capabilities:
    - Generate code from specifications
    - Implement features and bug fixes
    - Refactor and optimize code
    - Write unit tests
    - Provide implementation guidance
    """

    def _get_default_system_prompt(self) -> str:
        return """You are an expert software development agent specializing in Python and Rust.

Your responsibilities:
- Write clean, idiomatic, well-documented code
- Follow best practices and design patterns
- Implement robust error handling
- Write comprehensive tests
- Optimize for performance and maintainability

Coding standards:
- Python: PEP 8, type hints, docstrings
- Rust: Clippy lints, proper error handling, documentation
- DRY principle
- SOLID principles
- Comprehensive error handling

Always:
1. Understand requirements thoroughly
2. Design before implementing
3. Write self-documenting code
4. Include error handling
5. Add tests for critical paths"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        await self.validate_input(task, context)
        context = context or {}
        language = context.get("language", "python")
        
        try:
            code_result = await self._generate_code(task, language, context)
            return self._create_result(
                status=AgentStatus.COMPLETED,
                output=code_result,
                metrics={"language": language, "lines_generated": len(code_result.get("code", "").split("\n"))},
                context=context,
            )
        except Exception as e:
            self.logger.error(f"Development task failed: {e}", exc_info=True)
            return self._create_result(status=AgentStatus.FAILED, error=str(e), context=context)

    async def _generate_code(self, task: str, language: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Task: {task}\nLanguage: {language}\n\nGenerate production-ready code with:
1. Implementation
2. Type hints/types
3. Error handling
4. Documentation
5. Example usage"""
        
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json={"model": self.config.model, "prompt": prompt, "system": self.get_system_prompt(), "stream": False},
            )
            result = response.json()
            return {"code": result.get("response", ""), "language": language}
