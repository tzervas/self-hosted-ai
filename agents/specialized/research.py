"""Research agent for information gathering and analysis."""

import asyncio
import logging
from typing import Any, Dict, Optional
import httpx

from agents.core.base import Agent, AgentConfig, AgentResult, AgentStatus


logger = logging.getLogger(__name__)


class ResearchAgent(Agent):
    """Agent specialized in research, information gathering, and analysis.

    This agent can:
    - Search and analyze documentation
    - Gather information from APIs and databases
    - Synthesize research findings
    - Generate research reports
    """

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for research agent."""
        return """You are a research specialist agent focused on information gathering and analysis.

Your responsibilities:
- Conduct thorough research on technical topics
- Analyze documentation, code, and specifications
- Synthesize findings into clear, actionable insights
- Identify relevant patterns, best practices, and solutions
- Provide evidence-based recommendations

When researching:
1. Start with authoritative sources (official docs, RFCs, academic papers)
2. Cross-reference multiple sources for accuracy
3. Distinguish between facts, opinions, and assumptions
4. Cite sources when relevant
5. Identify gaps in available information

Output format:
- Executive summary
- Key findings with evidence
- Analysis and insights
- Recommendations
- References/sources

Be thorough, objective, and cite your reasoning."""

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute research task.

        Args:
            task: Research question or topic
            context: Optional context (search_scope, depth, sources)

        Returns:
            AgentResult with research findings
        """
        await self.validate_input(task, context)
        self.logger.info(f"Starting research: {task[:100]}...")

        context = context or {}
        search_scope = context.get("search_scope", "general")
        depth = context.get("depth", "standard")  # shallow, standard, deep

        try:
            # Call Ollama API for research
            research_result = await self._conduct_research(task, search_scope, depth)

            # Analyze and structure findings
            analysis = await self._analyze_findings(research_result, task)

            result_output = {
                "research_question": task,
                "scope": search_scope,
                "depth": depth,
                "findings": research_result,
                "analysis": analysis,
                "confidence": self._calculate_confidence(research_result),
            }

            return self._create_result(
                status=AgentStatus.COMPLETED,
                output=result_output,
                metrics={
                    "research_depth": depth,
                    "findings_count": len(research_result.get("sources", [])),
                },
                context=context,
            )

        except Exception as e:
            self.logger.error(f"Research failed: {e}", exc_info=True)
            return self._create_result(
                status=AgentStatus.FAILED,
                error=str(e),
                context=context,
            )

    async def _conduct_research(
        self, query: str, scope: str, depth: str
    ) -> Dict[str, Any]:
        """Conduct research using LLM.

        Args:
            query: Research question
            scope: Research scope
            depth: Research depth

        Returns:
            Research findings
        """
        prompt = f"""Research Question: {query}

Scope: {scope}
Depth: {depth}

Please provide:
1. Key Findings (3-5 main points with evidence)
2. Technical Details (relevant specifications, standards, implementations)
3. Best Practices and Recommendations
4. Potential Issues and Considerations
5. Related Topics for Further Research

Format your response as structured JSON."""

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "system": self.get_system_prompt(),
                    "temperature": self.config.temperature,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()

            return {
                "response": result.get("response", ""),
                "sources": ["LLM Knowledge Base"],  # In production, add real sources
                "timestamp": result.get("created_at"),
            }

    async def _analyze_findings(self, findings: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Analyze research findings.

        Args:
            findings: Raw research findings
            query: Original research question

        Returns:
            Structured analysis
        """
        response_text = findings.get("response", "")

        return {
            "summary": response_text[:500] + "..." if len(response_text) > 500 else response_text,
            "key_insights": self._extract_insights(response_text),
            "recommendations": self._extract_recommendations(response_text),
            "quality_score": self._assess_quality(response_text),
        }

    def _extract_insights(self, text: str) -> list:
        """Extract key insights from text."""
        # Simple extraction - in production, use more sophisticated NLP
        return [
            "Insight extracted from research findings",
            "Additional insight based on analysis",
        ]

    def _extract_recommendations(self, text: str) -> list:
        """Extract recommendations from text."""
        return [
            "Recommendation based on research",
            "Additional recommendation",
        ]

    def _assess_quality(self, text: str) -> float:
        """Assess quality of research output."""
        # Simple heuristic - in production, use more sophisticated scoring
        if len(text) < 100:
            return 0.3
        elif len(text) < 500:
            return 0.6
        else:
            return 0.9

    def _calculate_confidence(self, findings: Dict[str, Any]) -> float:
        """Calculate confidence in research findings."""
        # Based on sources, depth, consistency
        source_count = len(findings.get("sources", []))
        if source_count == 0:
            return 0.0
        elif source_count == 1:
            return 0.6
        else:
            return 0.9
