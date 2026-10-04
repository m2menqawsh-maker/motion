"""
ai/cost/baseline.py
===================
Canonical Efficiency Baselines for Representative Creative Video Types (S28-08C).

Defines expected reference metrics (calls, tokens, latency, cost, tier)
for comparison against regressions without enforcing inflexible production SLAs.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional
from pydantic import BaseModel, Field

from ai.contracts.creative.cost import ThresholdProvenance

QUANTIZE_PRECISION = Decimal("0.000001")


class FormatBaseline(BaseModel):
    """
    Reference efficiency profile for a video format.
    NOTE: Baselines here represent TEST_REFERENCE and EMPIRICAL_BASELINE assumptions
    for synthetic audits and regression tests. They do NOT constitute inflexible production
    SLAs or budget policies.
    """
    video_type: str = Field(description="Format classification")
    expected_tier: str = Field(description="Canonical expected tier (REUSE, COMPOSE, CREATE)")
    typical_duration_seconds: int = Field(description="Typical runtime seconds")
    max_ai_calls: int = Field(description="Expected upper bound of AI completion calls")
    max_planning_tokens: int = Field(description="Expected upper bound of planning tokens")
    max_retrieval_items: int = Field(description="Expected upper bound of knowledge retrieval items")
    expected_latency_ms: float = Field(description="Expected typical total pipeline latency")
    max_estimated_cost: Decimal = Field(description="Expected baseline cost ceiling in USD")
    provenance: ThresholdProvenance = Field(
        default=ThresholdProvenance.TEST_REFERENCE,
        description="Authority level (TEST_REFERENCE, EMPIRICAL_BASELINE, HEURISTIC, CANONICAL_POLICY)",
    )


CANONICAL_EFFICIENCY_BASELINES: Dict[str, FormatBaseline] = {
    "Product Ad": FormatBaseline(
        video_type="Product Ad",
        expected_tier="REUSE",
        typical_duration_seconds=15,
        max_ai_calls=3,
        max_planning_tokens=3500,
        max_retrieval_items=5,
        expected_latency_ms=2500.0,
        max_estimated_cost=Decimal("0.025000"),
        provenance=ThresholdProvenance.TEST_REFERENCE,
    ),
    "Explainer": FormatBaseline(
        video_type="Explainer",
        expected_tier="COMPOSE",
        typical_duration_seconds=45,
        max_ai_calls=5,
        max_planning_tokens=6000,
        max_retrieval_items=10,
        expected_latency_ms=4500.0,
        max_estimated_cost=Decimal("0.050000"),
        provenance=ThresholdProvenance.TEST_REFERENCE,
    ),
    "Talking Head": FormatBaseline(
        video_type="Talking Head",
        expected_tier="REUSE",
        typical_duration_seconds=30,
        max_ai_calls=3,
        max_planning_tokens=3000,
        max_retrieval_items=4,
        expected_latency_ms=2000.0,
        max_estimated_cost=Decimal("0.020000"),
        provenance=ThresholdProvenance.TEST_REFERENCE,
    ),
    "Music Montage": FormatBaseline(
        video_type="Music Montage",
        expected_tier="REUSE",
        typical_duration_seconds=20,
        max_ai_calls=2,
        max_planning_tokens=2500,
        max_retrieval_items=4,
        expected_latency_ms=1800.0,
        max_estimated_cost=Decimal("0.015000"),
        provenance=ThresholdProvenance.TEST_REFERENCE,
    ),
}


def get_efficiency_baseline(video_type: str) -> Optional[FormatBaseline]:
    """Retrieves canonical efficiency baseline for a video type, or case-insensitive match."""
    if video_type in CANONICAL_EFFICIENCY_BASELINES:
        return CANONICAL_EFFICIENCY_BASELINES[video_type]
    for k, v in CANONICAL_EFFICIENCY_BASELINES.items():
        if k.lower() == video_type.lower():
            return v
    return None
