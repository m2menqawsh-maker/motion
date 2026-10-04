"""
ai/evals/promotion.py
=====================
Model Promotion & Utility Evaluation Engine (S27.20).

Invariants:
- Strict promotion lifecycle: CANDIDATE -> OFFLINE_EVAL -> COST_BENCHMARK -> LATENCY_BENCHMARK -> SHADOW_VALIDATION -> APPROVED.
- Fake cheap model test: High cost savings with poor quality (< 0.80) is REJECTED.
- Bad utility test: Tiny quality gain (+0.01) with massive cost inflation (e.g. 10x) is REJECTED.
- Promotion is mediated through Registry authority, not direct mutation of defaults.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ai.contracts.evals import ModelPromotionState


class PromotionDecision:
    def __init__(
        self,
        approved: bool,
        final_state: ModelPromotionState,
        reasons: List[str],
        utility_score: float,
    ):
        self.approved = approved
        self.final_state = final_state
        self.reasons = reasons
        self.utility_score = utility_score


class ModelPromotionEngine:
    """
    Evaluates candidate models across quality floor, latency benchmark, and economic utility.
    """

    QUALITY_FLOOR = 0.80
    MAX_ACCEPTABLE_LATENCY_MS = 5000.0

    @classmethod
    def evaluate_candidate(
        cls,
        candidate_id: str,
        quality_score: float,
        cost_per_call: float,
        latency_ms: float,
        baseline_quality: float = 0.85,
        baseline_cost: float = 0.01,
        baseline_latency: float = 800.0,
    ) -> PromotionDecision:
        reasons: List[str] = []

        # 1. Hard Quality Floor Gate
        if quality_score < cls.QUALITY_FLOOR:
            reasons.append(
                f"Candidate '{candidate_id}' failed quality floor ({quality_score:.2f} < {cls.QUALITY_FLOOR:.2f}). "
                "Models below the quality floor cannot be approved regardless of cheap cost."
            )
            return PromotionDecision(
                approved=False,
                final_state=ModelPromotionState.REJECTED,
                reasons=reasons,
                utility_score=0.0,
            )

        # 2. Latency Ceiling Gate
        if latency_ms > cls.MAX_ACCEPTABLE_LATENCY_MS:
            reasons.append(
                f"Candidate '{candidate_id}' latency ({latency_ms:.1f}ms) exceeds ceiling ({cls.MAX_ACCEPTABLE_LATENCY_MS:.1f}ms)."
            )
            return PromotionDecision(
                approved=False,
                final_state=ModelPromotionState.REJECTED,
                reasons=reasons,
                utility_score=0.0,
            )

        # 3. Economic Utility Policy
        delta_quality = quality_score - baseline_quality
        cost_ratio = (cost_per_call / baseline_cost) if baseline_cost > 0 else 1.0

        # If quality gain is trivial (< 0.02) but cost inflation is excessive (>= 3.0x, e.g. 10x)
        if delta_quality < 0.02 and cost_ratio >= 3.0:
            reasons.append(
                f"Candidate '{candidate_id}' rejected under economic utility policy: "
                f"Trivial quality delta ({delta_quality:+.3f}) does not justify {cost_ratio:.1f}x cost inflation "
                f"(${cost_per_call:.4f} vs baseline ${baseline_cost:.4f})."
            )
            return PromotionDecision(
                approved=False,
                final_state=ModelPromotionState.REJECTED,
                reasons=reasons,
                utility_score=round(delta_quality - (cost_ratio * 0.1), 4),
            )

        # 4. Standard Utility Scoring
        # Positive utility requires sufficient quality improvement or cost savings
        utility = delta_quality * 10.0 - (cost_ratio - 1.0) * 0.5
        if utility < -1.0:
            reasons.append(f"Candidate net utility {utility:.3f} is below acceptance threshold.")
            return PromotionDecision(
                approved=False,
                final_state=ModelPromotionState.REJECTED,
                reasons=reasons,
                utility_score=round(utility, 4),
            )

        reasons.append(
            f"Candidate '{candidate_id}' passed quality floor ({quality_score:.2f}), "
            f"latency benchmark ({latency_ms:.1f}ms), and utility policy (+{utility:.2f})."
        )
        return PromotionDecision(
            approved=True,
            final_state=ModelPromotionState.APPROVED,
            reasons=reasons,
            utility_score=round(utility, 4),
        )
