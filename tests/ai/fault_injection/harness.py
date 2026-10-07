"""
tests/ai/fault_injection/harness.py
====================================
Fault Injection Test Harness & Interception Seams (S28-08D).

Guarantees:
- Test-only abstraction: NEVER mutates production registry or enters runtime authority.
- Hermetic: cleans up all monkeypatches, temp files, and snapshots.
- Observable: Captures structured trace evidence without raw sensitive data.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.plan import CreativePlan, CreativeTier
from ai.contracts.creative.skills_knowledge import RetrievalMode
from ai.knowledge.contracts import KnowledgeChunk, KnowledgeRetrievalQuery, KnowledgeRetrievalResult
from ai.knowledge.retriever import KnowledgeRetriever
from ai.knowledge.semantic import BaseSemanticScorer
from ai.planning.errors import TemplateRegistryUnavailableError
from ai.planning.tier_policy import CreativeTierPolicy
from ai.recipes.contracts import NoEligibleRecipeError, RecipeNotFoundError
from tests.ai.fault_injection.contracts import (
    ExpectedBehavior,
    FaultScenario,
    FaultScenarioResult,
    FaultSubsystem,
    FaultType,
)

logger = logging.getLogger(__name__)


class FaultInjectionHarness:
    """
    Test harness orchestrating fault scenarios against creative intelligence subsystems.
    """

    def __init__(self) -> None:
        self.results: List[FaultScenarioResult] = []

    def record_result(self, result: FaultScenarioResult) -> None:
        self.results.append(result)

    def summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        contained = sum(1 for r in self.results if r.contained)
        recovered = sum(1 for r in self.results if r.recovered)
        return {
            "total_fault_scenarios": total,
            "passed": passed,
            "failed": total - passed,
            "contained": contained,
            "recovered": recovered,
            "scenarios": [
                {
                    "scenario_id": r.scenario_id,
                    "subsystem": r.subsystem.value,
                    "fault_type": r.fault_type.value,
                    "passed": r.passed,
                    "contained": r.contained,
                    "recovered": r.recovered,
                    "observed_behavior": r.observed_behavior,
                    "errors": r.errors,
                }
                for r in self.results
            ],
        }


# =============================================================================
# Subsystem Fault Simulators (Test-Only)
# =============================================================================

class FailingSemanticScorer(BaseSemanticScorer):
    """Simulates embedding service outage or timeout."""

    def __init__(self, failure_mode: str = "timeout", error_message: str = "Semantic backend connection timeout after 5000ms"):
        self.failure_mode = failure_mode
        self.error_message = error_message

    def is_available(self) -> bool:
        if self.failure_mode == "unavailable":
            return False
        return True

    def score_chunks(self, query: str, chunks: Sequence[KnowledgeChunk]) -> List[float]:
        if self.failure_mode == "timeout":
            raise TimeoutError(self.error_message)
        elif self.failure_mode == "500":
            raise RuntimeError(f"Embedding service 500 Internal Error: {self.error_message}")
        raise RuntimeError(self.error_message)


class TransientFailureHelper:
    """Simulates recoverable transient failures with bounded retry counters."""

    def __init__(self, fail_count: int = 1, error_factory: Optional[Callable[[], Exception]] = None):
        self.fail_count = fail_count
        self.current_attempt = 0
        self.error_factory = error_factory or (lambda: TimeoutError("Transient connection timeout"))

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        self.current_attempt += 1
        if self.current_attempt <= self.fail_count:
            raise self.error_factory()
        return func(*args, **kwargs)
