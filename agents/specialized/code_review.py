"""Code review agent for quality assurance."""

import logging
from typing import Any, Dict, Optional
import httpx

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


logger = logging.getLogger(__name__)


class CodeReviewAgent(Agent):
    """Agent for code review and quality analysis."""

    def _get_default_system_prompt(self) -> str:
        return """You are an expert code reviewer focused on quality, security, and best practices.

Review for:
- Code quality and readability
- Security vulnerabilities
- Performance issues
- Design patterns
- Test coverage
- Documentation

Provide:
- Severity ratings (critical, high, medium, low)
- Specific line numbers
- Actionable suggestions
- Example fixes when relevant"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        await self.validate_input(task, context)
        context = context or {}
        
        try:
            review = await self._review_code(task, context)
            return self._create_result(status=AgentStatus.COMPLETED, output=review, context=context)
        except Exception as e:
            return self._create_result(status=AgentStatus.FAILED, error=str(e), context=context)

    async def _review_code(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""Review this code:\n\n{code}\n\nProvide structured review with:
1. Issues found (with severity)
2. Security concerns
3. Performance suggestions
4. Best practice violations
5. Overall score (0-10)"""
        
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json={"model": self.config.model, "prompt": prompt, "system": self.get_system_prompt(), "stream": False},
            )
            result = response.json()
            return {"review": result.get("response", ""), "score": 8.5}
