"""
ai/routing/cost.py
==================
Precision-safe, deterministic cost estimation using versioned ModelPricing (S27.4).

Invariants:
- Strictly Decimal-backed arithmetic (no binary float precision loss).
- Calculations explicitly bound to rate schedules without hardcoded constants.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from ai.models.types import ModelPricing
from ai.routing.types import WorkloadEstimate

QUANTIZE_PRECISION = Decimal("0.000001")


def calculate_estimated_cost(
    pricing: Optional[ModelPricing],
    workload: Optional[WorkloadEstimate] = None,
) -> Optional[Decimal]:
    """
    Computes expected invocation cost from a model's active pricing schedule and estimated workload.
    Returns None if pricing schedule is not configured.
    """
    if pricing is None:
        return None

    cost = Decimal("0")

    # 1. Base request fee
    if pricing.request_price is not None:
        multiplier = Decimal(str(workload.request_count)) if workload else Decimal("1")
        cost += pricing.request_price * multiplier

    if workload is None:
        return cost.quantize(QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)

    # 2. Token consumption
    if pricing.input_token_price is not None and workload.input_tokens is not None:
        cost += pricing.input_token_price * Decimal(str(workload.input_tokens))

    if pricing.output_token_price is not None and workload.output_tokens is not None:
        cost += pricing.output_token_price * Decimal(str(workload.output_tokens))

    # 3. Audio duration (priced per minute)
    if pricing.audio_minute_price is not None and workload.audio_seconds is not None:
        minutes = workload.audio_seconds / Decimal("60")
        cost += pricing.audio_minute_price * minutes

    # 4. Video duration (priced per minute)
    if pricing.video_minute_price is not None and workload.video_seconds is not None:
        minutes = workload.video_seconds / Decimal("60")
        cost += pricing.video_minute_price * minutes

    # 5. Image count
    if pricing.image_price is not None and workload.image_count is not None:
        cost += pricing.image_price * Decimal(str(workload.image_count))

    # 6. Character count (e.g. TTS)
    if pricing.character_price is not None and workload.character_count is not None:
        cost += pricing.character_price * Decimal(str(workload.character_count))

    return cost.quantize(QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)
