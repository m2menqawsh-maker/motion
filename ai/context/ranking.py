"""
ai/context/ranking.py
=====================
Deterministic candidate ranking and authority weighting engine (S27.8).

Calculates deterministic composite scores based on:
- Epistemic authority tier (SYSTEM_AUTHORITY > DOMAIN_SOURCE_OF_TRUTH > ...)
- Task and capability relevance
- Source confidence metric
- Recency timestamp
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from pydantic import Field

from ai.contracts.base import AIContractModel, StrictDecimal
from ai.context.types import (
    ContextAuthority,
    ContextExclusion,
    ContextItem,
    ExclusionReason,
)


class ContextRankingPolicy(AIContractModel):
    """
    Versioned ranking policy configuration.
    Strict Decimal arithmetic avoids floating point imprecision in sorting.
    """
    policy_id: str = Field(default="rank_v1", min_length=1)
    version: str = Field(default="1.0.0", min_length=1)
    authority_weight: StrictDecimal = Field(default=Decimal("0.35"))
    relevance_weight: StrictDecimal = Field(default=Decimal("0.40"))
    confidence_weight: StrictDecimal = Field(default=Decimal("0.15"))
    recency_weight: StrictDecimal = Field(default=Decimal("0.10"))
    authority_scores: Dict[str, StrictDecimal] = Field(
        default_factory=lambda: {
            ContextAuthority.SYSTEM_AUTHORITY.value: Decimal("1.00"),
            ContextAuthority.DOMAIN_SOURCE_OF_TRUTH.value: Decimal("0.95"),
            ContextAuthority.HUMAN_CONFIRMED.value: Decimal("0.85"),
            ContextAuthority.EXPLICIT_USER.value: Decimal("0.75"),
            ContextAuthority.DERIVED.value: Decimal("0.50"),
            ContextAuthority.INFERRED.value: Decimal("0.25"),
        }
    )
    minimum_score_threshold: StrictDecimal = Field(default=Decimal("0.15"))


class ContextRanker:
    """
    Computes deterministic ranking scores for candidate items.
    """
    def __init__(self, policy: Optional[ContextRankingPolicy] = None):
        self.policy = policy or ContextRankingPolicy()

    def score_item(
        self,
        item: ContextItem,
        reference_time: Optional[datetime] = None,
    ) -> Decimal:
        """Calculates deterministic composite score in range [0.0, 1.0]."""
        p = self.policy
        auth_score = p.authority_scores.get(item.authority.value, Decimal("0.10"))
        rel_score = Decimal(str(round(item.relevance_score, 4)))
        conf_score = Decimal(str(round(item.confidence, 4)))

        # Recency score calculation
        rec_score = Decimal("1.0")
        if item.recency_timestamp is not None and reference_time is not None:
            ref_dt = reference_time
            if ref_dt.tzinfo is None:
                ref_dt = ref_dt.replace(tzinfo=timezone.utc)
            item_dt = item.recency_timestamp
            if item_dt.tzinfo is None:
                item_dt = item_dt.replace(tzinfo=timezone.utc)

            age_sec = max(0.0, (ref_dt - item_dt).total_seconds())
            age_days = Decimal(str(round(age_sec / 86400.0, 4)))
            # Mild decay curve: 1.0 / (1.0 + 0.05 * days)
            rec_score = Decimal("1.0") / (Decimal("1.0") + age_days * Decimal("0.05"))

        composite = (
            (auth_score * p.authority_weight)
            + (rel_score * p.relevance_weight)
            + (conf_score * p.confidence_weight)
            + (rec_score * p.recency_weight)
        )
        return composite.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    def rank_items(
        self,
        items: List[ContextItem],
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ContextItem], List[ContextExclusion]]:
        """
        Ranks candidate items deterministically.
        Filters out items falling below minimum_score_threshold.
        """
        scored_pairs: List[Tuple[Decimal, Decimal, ContextItem]] = []
        exclusions: List[ContextExclusion] = []

        for item in items:
            score = self.score_item(item, reference_time=reference_time)
            if score < self.policy.minimum_score_threshold:
                exclusions.append(
                    ContextExclusion(
                        candidate_id=item.id,
                        section=item.section,
                        reason=ExclusionReason.LOW_CONFIDENCE,
                        details=f"Rank score {score} fell below minimum policy threshold {self.policy.minimum_score_threshold}.",
                        source_type=item.source_type,
                    )
                )
                continue

            conf_dec = Decimal(str(round(item.confidence, 4)))
            scored_pairs.append((score, conf_dec, item))

        # Deterministic sort order: (-score, -confidence, item.id ASC)
        scored_pairs.sort(key=lambda t: (-t[0], -t[1], t[2].id))

        ranked_items = [p[2] for p in scored_pairs]
        return ranked_items, exclusions
