"""
ai/acquisition/filtering.py
===========================
Deterministic hard constraint filtering engine for stock media candidates (S28-M05).

Invariants:
- Hard constraints execute strictly BEFORE ranking.
- Incompatible media types, mismatched aspect orientations, and violated duration limits
  are disqualified immediately.
- Rejections are tracked deterministically for observability and audit reporting.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from ai.acquisition.contracts import (
    CommercialUseStatus,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)


class StockFilterEngine:
    """Enforces hard compatibility constraints on raw provider search results."""

    @classmethod
    def filter_candidates(
        cls,
        candidates: List[StockCandidate],
        query: StockSearchQuery,
    ) -> Tuple[List[StockCandidate], Dict[str, int]]:
        """
        Filters candidates against query constraints.
        Returns (eligible_candidates, rejection_reasons_counter).
        """
        eligible: List[StockCandidate] = []
        rejection_stats: Dict[str, int] = {
            "media_type_mismatch": 0,
            "orientation_mismatch": 0,
            "min_dimensions_violated": 0,
            "duration_out_of_bounds": 0,
            "commercial_use_prohibited": 0,
            "attribution_unacceptable": 0,
            "provider_not_allowed": 0,
        }

        for c in candidates:
            # 1. Media Type constraint
            # Allow SOUND_EFFECT when AUDIO is requested if it fits
            if query.media_type == StockMediaType.AUDIO:
                if c.media_type not in (StockMediaType.AUDIO, StockMediaType.SOUND_EFFECT):
                    rejection_stats["media_type_mismatch"] += 1
                    continue
            elif query.media_type == StockMediaType.SOUND_EFFECT:
                if c.media_type not in (StockMediaType.SOUND_EFFECT, StockMediaType.AUDIO):
                    rejection_stats["media_type_mismatch"] += 1
                    continue
            else:
                if c.media_type != query.media_type:
                    rejection_stats["media_type_mismatch"] += 1
                    continue

            # 2. Allowed Providers constraint
            if query.allowed_providers and c.source.lower() not in [p.lower() for p in query.allowed_providers]:
                rejection_stats["provider_not_allowed"] += 1
                continue

            # 3. Orientation constraint (for visual media: VIDEO, IMAGE)
            if query.orientation and c.media_type in (StockMediaType.VIDEO, StockMediaType.IMAGE):
                desired = query.orientation.lower()
                c_orient = (c.orientation or "").lower()
                
                # Derive orientation if not explicitly tagged by provider
                if not c_orient and c.width and c.height:
                    ratio = c.width / c.height
                    if ratio > 1.15:
                        c_orient = "landscape"
                    elif ratio < 0.85:
                        c_orient = "portrait"
                    else:
                        c_orient = "square"

                if c_orient and c_orient != desired:
                    rejection_stats["orientation_mismatch"] += 1
                    continue

            # 4. Dimension constraints
            if query.min_width and c.width and c.width < query.min_width:
                rejection_stats["min_dimensions_violated"] += 1
                continue
            if query.min_height and c.height and c.height < query.min_height:
                rejection_stats["min_dimensions_violated"] += 1
                continue

            # 5. Duration constraints (for time-based media: VIDEO, AUDIO, SOUND_EFFECT)
            if c.duration_seconds is not None:
                if query.min_duration is not None and c.duration_seconds < query.min_duration:
                    rejection_stats["duration_out_of_bounds"] += 1
                    continue
                if query.max_duration is not None and c.duration_seconds > query.max_duration:
                    rejection_stats["duration_out_of_bounds"] += 1
                    continue

            # 6. Commercial Use requirement
            if query.commercial_use_required:
                if c.commercial_use == CommercialUseStatus.PROHIBITED:
                    rejection_stats["commercial_use_prohibited"] += 1
                    continue

            # 7. Attribution requirement
            if query.require_no_attribution:
                if c.attribution_required:
                    rejection_stats["attribution_unacceptable"] += 1
                    continue

            eligible.append(c)

        return eligible, rejection_stats
