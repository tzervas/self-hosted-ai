"""Agent Evaluator

Evaluation framework for testing and validating agent performance.
Based on Google ADK evaluation patterns.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from agents.adk.base import ADKAgent, ADKConfig, ADKResult


@dataclass
class EvaluationCase:
    """A single evaluation test case."""
    id: str
    input_task: str
    expected_output: Optional[str] = None
    expected_contains: Optional[List[str]] = None
    expected_not_contains: Optional[List[str]] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300
    custom_validator: Optional[Callable[[str], bool]] = None


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""
    case_id: str
    passed: bool
    score: float  # 0.0 to 1.0
    actual_output: Optional[str]
    duration_seconds: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class EvaluationReport:
    """Summary report of all evaluations."""
    agent_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    total_duration_seconds: float
    results: List[EvaluationResult]
    
    @property
    def pass_rate(self) -> float:
        return self.passed_cases / self.total_cases if self.total_cases > 0 else 0.0


class AgentEvaluator:
    """Evaluator for testing ADK agents."""
    
    def __init__(self, agent: ADKAgent):
        """Initialize evaluator.
        
        Args:
            agent: Agent to evaluate
        """
        self.agent = agent
        self.logger = logger.bind(evaluator=agent.config.name)
    
    def _evaluate_output(
        self,
        case: EvaluationCase,
        actual: str
    ) -> tuple[bool, float, Dict[str, Any]]:
        """Evaluate output against expected criteria.
        
        Args:
            case: Test case
            actual: Actual output
            
        Returns:
            Tuple of (passed, score, details)
        """
        details = {}
        score = 0.0
        checks_passed = 0
        total_checks = 0
        
        # Check exact match if expected_output provided
        if case.expected_output is not None:
            total_checks += 1
            if case.expected_output.strip() == actual.strip():
                checks_passed += 1
                details["exact_match"] = True
            else:
                details["exact_match"] = False
        
        # Check contains
        if case.expected_contains:
            for expected in case.expected_contains:
                total_checks += 1
                if expected.lower() in actual.lower():
                    checks_passed += 1
                    details[f"contains_{expected[:20]}"] = True
                else:
                    details[f"contains_{expected[:20]}"] = False
        
        # Check not contains
        if case.expected_not_contains:
            for not_expected in case.expected_not_contains:
                total_checks += 1
                if not_expected.lower() not in actual.lower():
                    checks_passed += 1
                    details[f"not_contains_{not_expected[:20]}"] = True
                else:
                    details[f"not_contains_{not_expected[:20]}"] = False
        
        # Custom validator
        if case.custom_validator:
            total_checks += 1
            try:
                if case.custom_validator(actual):
                    checks_passed += 1
                    details["custom_validator"] = True
                else:
                    details["custom_validator"] = False
            except Exception as e:
                details["custom_validator"] = f"error: {e}"
        
        # Calculate score
        if total_checks > 0:
            score = checks_passed / total_checks
        else:
            # No specific checks - just verify we got output
            score = 1.0 if actual.strip() else 0.0
        
        passed = score >= 0.5  # Pass threshold
        
        return passed, score, details
    
    async def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """Evaluate a single test case.
        
        Args:
            case: Test case to evaluate
            
        Returns:
            EvaluationResult
        """
        start_time = time.time()
        
        try:
            # Execute agent
            result = await self.agent.execute(case.input_task, case.context)
            duration = time.time() - start_time
            
            if not result.is_success:
                return EvaluationResult(
                    case_id=case.id,
                    passed=False,
                    score=0.0,
                    actual_output=None,
                    duration_seconds=duration,
                    error=result.error
                )
            
            # Evaluate output
            passed, score, details = self._evaluate_output(case, result.output or "")
            
            return EvaluationResult(
                case_id=case.id,
                passed=passed,
                score=score,
                actual_output=result.output,
                duration_seconds=duration,
                details=details
            )
            
        except asyncio.TimeoutError:
            return EvaluationResult(
                case_id=case.id,
                passed=False,
                score=0.0,
                actual_output=None,
                duration_seconds=case.timeout,
                error="Timeout"
            )
        except Exception as e:
            return EvaluationResult(
                case_id=case.id,
                passed=False,
                score=0.0,
                actual_output=None,
                duration_seconds=time.time() - start_time,
                error=str(e)
            )
    
    async def evaluate_all(
        self,
        cases: List[EvaluationCase],
        parallel: bool = False,
        max_parallel: int = 5
    ) -> EvaluationReport:
        """Evaluate all test cases.
        
        Args:
            cases: List of test cases
            parallel: Run in parallel
            max_parallel: Max parallel evaluations
            
        Returns:
            EvaluationReport
        """
        start_time = time.time()
        results: List[EvaluationResult] = []
        
        self.logger.info(f"Starting evaluation of {len(cases)} cases")
        
        if parallel:
            semaphore = asyncio.Semaphore(max_parallel)
            
            async def limited_evaluate(case):
                async with semaphore:
                    return await self.evaluate_case(case)
            
            results = await asyncio.gather(*[limited_evaluate(c) for c in cases])
        else:
            for case in cases:
                self.logger.info(f"Evaluating case: {case.id}")
                result = await self.evaluate_case(case)
                results.append(result)
        
        # Calculate summary
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        
        report = EvaluationReport(
            agent_name=self.agent.config.name,
            total_cases=len(cases),
            passed_cases=passed,
            failed_cases=failed,
            average_score=avg_score,
            total_duration_seconds=time.time() - start_time,
            results=results
        )
        
        self.logger.info(
            f"Evaluation complete: {passed}/{len(cases)} passed, "
            f"avg score: {avg_score:.2f}"
        )
        
        return report
    
    @classmethod
    def load_cases_from_json(cls, path: Path) -> List[EvaluationCase]:
        """Load test cases from JSON file.
        
        Args:
            path: Path to JSON file
            
        Returns:
            List of EvaluationCase
        """
        with open(path) as f:
            data = json.load(f)
        
        cases = []
        for item in data.get("cases", []):
            cases.append(EvaluationCase(
                id=item["id"],
                input_task=item["input_task"],
                expected_output=item.get("expected_output"),
                expected_contains=item.get("expected_contains"),
                expected_not_contains=item.get("expected_not_contains"),
                context=item.get("context", {}),
                timeout=item.get("timeout", 300)
            ))
        
        return cases
    
    def save_report(self, report: EvaluationReport, path: Path):
        """Save evaluation report to JSON.
        
        Args:
            report: Report to save
            path: Output path
        """
        data = {
            "agent_name": report.agent_name,
            "summary": {
                "total_cases": report.total_cases,
                "passed_cases": report.passed_cases,
                "failed_cases": report.failed_cases,
                "pass_rate": report.pass_rate,
                "average_score": report.average_score,
                "total_duration_seconds": report.total_duration_seconds
            },
            "results": [
                {
                    "case_id": r.case_id,
                    "passed": r.passed,
                    "score": r.score,
                    "duration_seconds": r.duration_seconds,
                    "details": r.details,
                    "error": r.error
                }
                for r in report.results
            ]
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
