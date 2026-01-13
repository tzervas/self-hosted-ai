"""Documentation agent for generating technical documentation."""

import logging
from typing import Any, Dict, Optional
import httpx

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


logger = logging.getLogger(__name__)


class DocumentationAgent(Agent):
    """Agent for generating technical documentation."""

    def _get_default_system_prompt(self) -> str:
        return """You are a technical documentation specialist.

Create:
- API documentation
- User guides
- Architecture docs
- README files
- Inline code documentation

Principles:
- Clear and concise
- Examples and use cases
- Proper formatting (Markdown)
- Audience-appropriate
- Comprehensive but not verbose"""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        await self.validate_input(task, context)
        context = context or {}
        
        try:
            docs = await self._generate_documentation(task, context)
            return self._create_result(status=AgentStatus.COMPLETED, output=docs, context=context)
        except Exception as e:
            return self._create_result(status=AgentStatus.FAILED, error=str(e), context=context)

    async def _generate_documentation(self, content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = context.get("doc_type", "api")
        prompt = f"""Generate {doc_type} documentation for:\n\n{content}\n\nInclude:
1. Overview
2. Usage examples
3. Parameters/Arguments
4. Return values
5. Error handling"""
        
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json={"model": self.config.model, "prompt": prompt, "system": self.get_system_prompt(), "stream": False},
            )
            result = response.json()
            return {"documentation": result.get("response", ""), "format": "markdown"}
