"""
tests/ai/routing/test_fallback.py
=================================
Verification suite for Fallback Chain and Failure-Aware Fallback Resolution (S27.4).

Invariants:
- Primary candidate is NEVER in the fallback chain.
- Fallback chain has ZERO duplicates.
- Fallbacks maintain provider diversity when configured.
- Failure codes drive intelligent next-candidate selection.
- Retries and fallbacks are strictly bounded.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType, QualityTarget
from ai.contracts.errors import AIErrorCode
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.routing.fallback import build_fallback_chain, resolve_next_fallback
from ai.routing.policy import STANDARD_POLICY, RoutingPolicy


def make_candidate(mid: str, pid: str, structured: bool = False) -> ModelDefinition:
    return ModelDefinition(
        model_id=mid,
        provider_id=pid,
        display_name=mid,
        capabilities=[CapabilityType.TEXT_GENERATION],
        quality_profile=QualityTarget.STANDARD,
        cost_profile=CostTier.LOW,
        latency_profile=LatencyTier.FAST,
        reliability=0.99,
        supports_structured_output=structured,
        enabled=True,
    )


class TestFallbackChain:

    def test_fallback_chain_invariants(self):
        """Validates that fallback chain excludes primary and contains no duplicates."""
        c1 = make_candidate("m1", "p1")
        c2 = make_candidate("m2", "p2")
        c3 = make_candidate("m3", "p1")
        c4 = make_candidate("m4", "p3")

        ranked = [
            (c1, Decimal("1.0"), Decimal("0.01")),
            (c2, Decimal("0.9"), Decimal("0.01")),
            (c3, Decimal("0.8"), Decimal("0.01")),
            (c4, Decimal("0.7"), Decimal("0.01")),
        ]

        fallbacks = build_fallback_chain(ranked, STANDARD_POLICY)

        assert "m1" not in fallbacks
        assert len(fallbacks) == len(set(fallbacks))
        assert len(fallbacks) <= STANDARD_POLICY.max_fallbacks

    def test_cross_provider_diversity_interleaving(self):
        """Cross-provider diversity prefers alternating provider origins."""
        c1 = make_candidate("m1", "p1")  # Primary
        c2 = make_candidate("m2", "p1")  # Same provider
        c3 = make_candidate("m3", "p2")  # Different provider
        c4 = make_candidate("m4", "p3")  # Different provider

        ranked = [
            (c1, Decimal("1.0"), Decimal("0.01")),
            (c2, Decimal("0.9"), Decimal("0.01")),
            (c3, Decimal("0.8"), Decimal("0.01")),
            (c4, Decimal("0.7"), Decimal("0.01")),
        ]

        # Policy with diversity enabled
        policy = RoutingPolicy(policy_id="test", prefer_cross_provider_diversity=True, max_fallbacks=3)
        fallbacks = build_fallback_chain(ranked, policy)

        # Because c1 is from p1, diverse candidates (m3, m4) are prioritized over m2 (p1)
        assert fallbacks[0] == "m3"  # From p2
        assert "m1" not in fallbacks


class TestFailureAwareFallback:

    def test_terminal_failures_return_none(self):
        """Cancelled or content-rejected operations must terminate immediately with no fallback."""
        c1 = make_candidate("m1", "p1")
        c2 = make_candidate("m2", "p2")
        ranked = [(c1, Decimal("1.0"), None), (c2, Decimal("0.9"), None)]

        assert resolve_next_fallback("m1", AIErrorCode.CANCELLED, ["m1"], ranked, STANDARD_POLICY) is None
        assert resolve_next_fallback("m1", AIErrorCode.CONTENT_REJECTED, ["m1"], ranked, STANDARD_POLICY) is None
        assert resolve_next_fallback("m1", AIErrorCode.BUDGET_EXCEEDED, ["m1"], ranked, STANDARD_POLICY) is None

    def test_rate_limit_switches_provider(self):
        """429 / RATE_LIMITED prioritizes an alternative provider."""
        c1 = make_candidate("m1", "prov-a")
        c2 = make_candidate("m2", "prov-a")
        c3 = make_candidate("m3", "prov-b")
        ranked = [
            (c1, Decimal("1.0"), None),
            (c2, Decimal("0.9"), None),
            (c3, Decimal("0.8"), None),
        ]

        next_candidate = resolve_next_fallback(
            current_candidate="m1",
            failure_code=AIErrorCode.RATE_LIMITED,
            attempted_candidates=["m1"],
            ranked_candidates=ranked,
            policy=STANDARD_POLICY,
        )
        assert next_candidate == "m3", "Expected candidate from prov-b to be prioritized after 429 on prov-a"

    def test_schema_failure_prefers_structured_output_model(self):
        """SCHEMA_VALIDATION_FAILED prefers candidates supporting structured output."""
        c1 = make_candidate("m1", "prov-a", structured=False)
        c2 = make_candidate("m2", "prov-a", structured=False)
        c3 = make_candidate("m3", "prov-b", structured=True)
        ranked = [
            (c1, Decimal("1.0"), None),
            (c2, Decimal("0.9"), None),
            (c3, Decimal("0.8"), None),
        ]

        next_candidate = resolve_next_fallback(
            current_candidate="m1",
            failure_code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
            attempted_candidates=["m1"],
            ranked_candidates=ranked,
            policy=STANDARD_POLICY,
        )
        assert next_candidate == "m3", "Expected structured-output capable model to be chosen"

    def test_invalid_output_allows_single_retry_then_falls_back(self):
        """INVALID_MODEL_OUTPUT allows 1 retry on the same model, then switches."""
        c1 = make_candidate("m1", "prov-a")
        c2 = make_candidate("m2", "prov-b")
        ranked = [(c1, Decimal("1.0"), None), (c2, Decimal("0.9"), None)]

        # First failure on m1 -> allows retry
        next_attempt1 = resolve_next_fallback(
            current_candidate="m1",
            failure_code=AIErrorCode.INVALID_MODEL_OUTPUT,
            attempted_candidates=["m1"],
            ranked_candidates=ranked,
            policy=STANDARD_POLICY,
        )
        assert next_attempt1 == "m1"

        # Second failure on m1 -> must fall back to m2
        next_attempt2 = resolve_next_fallback(
            current_candidate="m1",
            failure_code=AIErrorCode.INVALID_MODEL_OUTPUT,
            attempted_candidates=["m1", "m1"],
            ranked_candidates=ranked,
            policy=STANDARD_POLICY,
        )
        assert next_attempt2 == "m2"

    def test_max_total_attempts_bounded(self):
        """Exceeding max_total_attempts stops resolution."""
        c1 = make_candidate("m1", "p1")
        c2 = make_candidate("m2", "p2")
        ranked = [(c1, Decimal("1.0"), None), (c2, Decimal("0.9"), None)]

        policy = RoutingPolicy(policy_id="test", max_total_attempts=2)
        # Already attempted twice
        assert resolve_next_fallback("m1", AIErrorCode.TIMEOUT, ["m1", "m2"], ranked, policy) is None
