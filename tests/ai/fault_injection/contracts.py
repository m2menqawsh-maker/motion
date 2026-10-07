"""
tests/ai/fault_injection/contracts.py
======================================
Test-only Fault Injection Contracts and Taxonomy (S28-08D).

Strict Invariants:
- Test / evaluation ONLY: Never enters production authority or runtime dependencies.
- Models every subsystem failure, expected behavior, and forbidden side-effects.
- Fails closed on authority breaches, data corruption, or cross-tenant leakage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class FaultSubsystem(str, Enum):
    """Subsystems targeted for fault injection verification."""
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    EMBEDDING_SERVICE = "EMBEDDING_SERVICE"
    SKILL_LOADING = "SKILL_LOADING"
    RECIPE_REGISTRY = "RECIPE_REGISTRY"
    TASTE_ENGINE = "TASTE_ENGINE"
    TEMPLATE_REGISTRY = "TEMPLATE_REGISTRY"
    CANDIDATE_RENDER = "CANDIDATE_RENDER"
    PROMOTION = "PROMOTION"
    MEMORY_SERVICE = "MEMORY_SERVICE"
    AI_PROVIDER = "AI_PROVIDER"
    WORKER_EXECUTION = "WORKER_EXECUTION"


class FaultType(str, Enum):
    """Specific failure injection modes."""
    TIMEOUT = "TIMEOUT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    EMPTY_DATA = "EMPTY_DATA"
    CRASH_EXCEPTION = "CRASH_EXCEPTION"
    RATE_LIMIT = "RATE_LIMIT"
    CORRUPT_STATE = "CORRUPT_STATE"
    INTERRUPT = "INTERRUPT"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    CROSS_TENANT_ATTEMPT = "CROSS_TENANT_ATTEMPT"


class ExpectedBehavior(str, Enum):
    """Expected outcome behavior under failure."""
    SAFE_FALLBACK = "SAFE_FALLBACK"
    EXPLICIT_RECOVERABLE_FAILURE = "EXPLICIT_RECOVERABLE_FAILURE"
    CONTROLLED_RETRY = "CONTROLLED_RETRY"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass(frozen=True)
class FaultScenario:
    """Specification of an individual fault injection scenario."""
    scenario_id: str
    target_subsystem: FaultSubsystem
    fault_type: FaultType
    injection_point: str
    expected_behavior: ExpectedBehavior
    expected_state: str
    forbidden_side_effects: List[str] = field(default_factory=list)
    recovery_expected: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FaultScenarioResult:
    """Outcome report for an executed fault injection scenario."""
    scenario_id: str
    subsystem: FaultSubsystem
    fault_type: FaultType
    passed: bool
    observed_behavior: str
    contained: bool
    recovered: bool
    errors: List[str] = field(default_factory=list)
    trace_evidence: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
