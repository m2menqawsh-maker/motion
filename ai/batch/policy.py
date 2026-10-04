"""
ai/batch/policy.py
==================
Execution Class Policies & Constraints for Batch / Background AI (S27.21).

Invariants:
- INTERACTIVE: low-latency, immediate, bounded execution.
- BACKGROUND: speculative or media analysis, tolerant to queue delays, uses cheaper routes.
- BATCH: bulk/nightly workloads, strictly executes via durable infra, forbidden to hit expensive interactive endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ai.contracts.common import ExecutionClass, QualityTarget
from ai.models.types import CostTier, LatencyTier


@dataclass(frozen=True)
class ExecutionClassPolicy:
    """Configuration and constraint policy for an execution latency tier."""
    execution_class: ExecutionClass
    default_timeout_seconds: float
    max_timeout_seconds: float
    allowed_latency_tiers: List[LatencyTier]
    disallowed_cost_tiers: List[CostTier]
    allow_durable_workers: bool
    requires_budget_reservation: bool
    description: str


INTERACTIVE_POLICY = ExecutionClassPolicy(
    execution_class=ExecutionClass.INTERACTIVE,
    default_timeout_seconds=5.0,
    max_timeout_seconds=15.0,
    allowed_latency_tiers=[LatencyTier.REALTIME, LatencyTier.FAST, LatencyTier.MODERATE],
    disallowed_cost_tiers=[],
    allow_durable_workers=False,
    requires_budget_reservation=True,
    description="Immediate user-facing execution with tight latency bounds.",
)

BACKGROUND_POLICY = ExecutionClassPolicy(
    execution_class=ExecutionClass.BACKGROUND,
    default_timeout_seconds=120.0,
    max_timeout_seconds=600.0,
    allowed_latency_tiers=[LatencyTier.REALTIME, LatencyTier.FAST, LatencyTier.MODERATE, LatencyTier.SLOW],
    disallowed_cost_tiers=[],
    allow_durable_workers=True,
    requires_budget_reservation=True,
    description="Asynchronous media analysis or background worker processing.",
)

BATCH_POLICY = ExecutionClassPolicy(
    execution_class=ExecutionClass.BATCH,
    default_timeout_seconds=1800.0,
    max_timeout_seconds=7200.0,
    allowed_latency_tiers=[LatencyTier.MODERATE, LatencyTier.SLOW, LatencyTier.FAST],
    # Disallow expensive interactive-only models in batch workloads
    disallowed_cost_tiers=[CostTier.VERY_HIGH],
    allow_durable_workers=True,
    requires_budget_reservation=True,
    description="Bulk offline analysis or nightly benchmark runs via durable workers.",
)

EXECUTION_POLICIES: Dict[ExecutionClass, ExecutionClassPolicy] = {
    ExecutionClass.INTERACTIVE: INTERACTIVE_POLICY,
    ExecutionClass.BACKGROUND: BACKGROUND_POLICY,
    ExecutionClass.BATCH: BATCH_POLICY,
}


def get_execution_policy(execution_class: ExecutionClass) -> ExecutionClassPolicy:
    """Resolves authoritative policy for execution class."""
    return EXECUTION_POLICIES.get(execution_class, INTERACTIVE_POLICY)


class ForbiddenBatchRouteError(ValueError):
    """Raised when a batch workload is directed to a forbidden expensive interactive route."""
    pass
