"""
ai/acquisition/ranking.py
=========================
Deterministic multi-factor ranking engine for stock media candidates (S28-M05).

Invariants:
- Deterministic calculation: identical inputs yield identical rankings.
- Fully auditable: emits granular feature score breakdown per candidate.
- Does not rely on ungrounded or non-deterministic LLM evaluation.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from ai.acquisition.contracts import (
    CommercialUseStatus,
    LicenseClassification,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)


def _tokenize(text: str) -> Set[str]:
    """Extracts normalized alphanumeric search tokens."""
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return {w for w in cleaned.split() if len(w) > 2}


class StockRankingEngine:
    """Computes deterministic relevance and quality scores for eligible candidates."""

    WEIGHT_RELEVANCE = 0.40
    WEIGHT_DIMENSIONS = 0.20
    WEIGHT_DURATION = 0.20
    WEIGHT_LICENSE = 0.15
    WEIGHT_PROVIDER = 0.05

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[StockCandidate],
        query: StockSearchQuery,
    ) -> List[StockCandidate]:
        """
        Ranks a list of pre-filtered eligible candidates.
        Mutates candidate.ranking_score and candidate.ranking_features in-place.
        Returns candidates sorted in descending order of ranking_score.
        """
        query_tokens = _tokenize(query.query)

        target_duration: float | None = None
        if query.min_duration is not None and query.max_duration is not None:
            target_duration = (query.min_duration + query.max_duration) / 2.0
        elif query.min_duration is not None:
            target_duration = query.min_duration
        elif query.max_duration is not None:
            target_duration = query.max_duration

        scored_candidates: List[StockCandidate] = []
        for c in candidates:
            # 1. Query relevance (Jaccard overlap across title, tags, description)
            candidate_tokens: Set[str] = set()
            if c.title:
                candidate_tokens.update(_tokenize(c.title))
            if c.description:
                candidate_tokens.update(_tokenize(c.description))
            for tag in c.tags:
                candidate_tokens.update(_tokenize(tag))

            if query_tokens and candidate_tokens:
                intersection = query_tokens.intersection(candidate_tokens)
                relevance_score = len(intersection) / len(query_tokens)
                relevance_score = min(1.0, relevance_score)
            elif not query_tokens:
                relevance_score = 0.5
            else:
                relevance_score = 0.1

            # 2. Dimensions score (HD=0.8, 1080p=0.9, 4K=1.0)
            dim_score = 0.5
            if c.width and c.height:
                max_dim = max(c.width, c.height)
                if max_dim >= 3840:
                    dim_score = 1.0
                elif max_dim >= 1920:
                    dim_score = 0.95
                elif max_dim >= 1280:
                    dim_score = 0.80
                elif max_dim >= 720:
                    dim_score = 0.60
                else:
                    dim_score = 0.40
            elif c.media_type == StockMediaType.ICON:
                # Vector SVGs are resolution independent
                dim_score = 1.0

            # 3. Duration fit score
            dur_score = 0.5
            if target_duration and c.duration_seconds is not None:
                diff = abs(c.duration_seconds - target_duration)
                # Exponential decay penalty
                dur_score = max(0.0, 1.0 - (diff / max(target_duration, 5.0)))
            elif c.duration_seconds is not None:
                # Modest default duration fit
                dur_score = 0.8
            else:
                dur_score = 0.5

            # 4. License score
            license_score = 0.5
            if c.license in (LicenseClassification.CC0, LicenseClassification.PUBLIC_DOMAIN):
                license_score = 1.0
            elif c.license in (LicenseClassification.PEXELS_LICENSE, LicenseClassification.PIXABAY_LICENSE, LicenseClassification.OPEN_SOURCE_ICON):
                license_score = 0.95
            elif c.license == LicenseClassification.CC_BY:
                license_score = 0.80
            elif c.commercial_use == CommercialUseStatus.ALLOWED:
                license_score = 0.75
            else:
                license_score = 0.30

            # 5. Provider score
            prov_score = 0.5
            if c.provider_score is not None:
                # Normalize arbitrary positive score to 0..1
                prov_score = min(1.0, c.provider_score / 1000.0) if c.provider_score > 0 else 0.5

            total_score = (
                relevance_score * cls.WEIGHT_RELEVANCE
                + dim_score * cls.WEIGHT_DIMENSIONS
                + dur_score * cls.WEIGHT_DURATION
                + license_score * cls.WEIGHT_LICENSE
                + prov_score * cls.WEIGHT_PROVIDER
            )
            total_score = round(min(1.0, max(0.0, total_score)), 4)

            scored_candidates.append(
                c.model_copy(
                    update={
                        "ranking_score": total_score,
                        "ranking_features": {
                            "relevance": round(relevance_score, 4),
                            "dimensions": round(dim_score, 4),
                            "duration": round(dur_score, 4),
                            "license": round(license_score, 4),
                            "provider": round(prov_score, 4),
                        },
                    }
                )
            )

        # Deterministic sort: descending score, ascending candidate_id
        ranked = sorted(scored_candidates, key=lambda x: (-(x.ranking_score or 0.0), x.candidate_id))
        return ranked
