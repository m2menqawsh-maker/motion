"""
ai/cost/accounting.py
=====================
Token accounting and precision cost calculation for Creative Intelligence (S28-08C).

Invariants:
- Token accounting priority:
    1. Provider usage metadata (authoritative) -> CostProvenance.ACTUAL
    2. Canonical tokenizer / character estimate -> CostProvenance.ESTIMATED
    3. Missing / un-monetized -> CostProvenance.UNKNOWN
- Never present ESTIMATED numbers as settled invoices.
- Monetary calculations strictly use Decimal precision (QUANTIZE_PRECISION = Decimal("0.000001")).
- Versioned pricing looked up from canonical ModelRegistry (no hardcoded prices).
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from ai.contracts.creative.cost import CostProvenance
from ai.contracts.usage import UsageRecord
from ai.models.registry import get_model_registry, UnknownModelError
from ai.models.types import ModelPricing
from ai.routing.cost import calculate_estimated_cost
from ai.routing.types import WorkloadEstimate

QUANTIZE_PRECISION = Decimal("0.000001")


class TokenAccounting:
    """
    Authority on token accounting, estimation, and provenance classification.
    """

    @classmethod
    def estimate_tokens(cls, text: Optional[str]) -> int:
        """
        Deterministic token count estimation from raw string content.
        Uses ~4 chars/token for Latin scripts and ~1.5 chars/token for Arabic / non-ASCII scripts.
        """
        if not text:
            return 0

        # Strip whitespace for fair count
        clean = text.strip()
        if not clean:
            return 0

        # Separate Arabic / non-ASCII characters from ASCII characters
        non_ascii_chars = len(re.findall(r"[^\x00-\x7F]", clean))
        ascii_chars = len(clean) - non_ascii_chars

        # Heuristic: 1 token ~ 4 ASCII characters; 1 token ~ 1.5 non-ASCII characters
        token_estimate = int((ascii_chars / 4.0) + (non_ascii_chars / 1.5))
        return max(1, token_estimate)

    @classmethod
    def resolve_tokens_and_provenance(
        cls,
        usage_record: Optional[UsageRecord] = None,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        explicit_input_tokens: Optional[int] = None,
        explicit_output_tokens: Optional[int] = None,
    ) -> Tuple[Optional[int], Optional[int], CostProvenance]:
        """
        Applies authoritative priority hierarchy:
        1. Explicit UsageRecord with tokens -> ACTUAL
        2. Explicit token integers passed by caller -> ACTUAL
        3. Text content estimated via TokenAccounting -> ESTIMATED
        4. Neither available -> UNKNOWN
        """
        # 1. Authoritative provider usage record
        if usage_record is not None and (
            usage_record.input_tokens is not None or usage_record.output_tokens is not None
        ):
            return usage_record.input_tokens, usage_record.output_tokens, CostProvenance.ACTUAL

        # 2. Explicitly supplied measured tokens
        if explicit_input_tokens is not None or explicit_output_tokens is not None:
            return explicit_input_tokens, explicit_output_tokens, CostProvenance.ACTUAL

        # 3. Estimated from raw text inputs/outputs
        if input_text is not None or output_text is not None:
            in_tok = cls.estimate_tokens(input_text) if input_text is not None else None
            out_tok = cls.estimate_tokens(output_text) if output_text is not None else None
            return in_tok, out_tok, CostProvenance.ESTIMATED

        # 4. Unknown
        return None, None, CostProvenance.UNKNOWN


class CreativeCostEstimator:
    """
    Computes monetary costs using canonical versioned ModelPricing schedules.
    """

    @classmethod
    def compute_cost(
        cls,
        model_id: Optional[str],
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        request_count: int = 1,
        generation_count: int = 0,
        actual_cost_override: Optional[Decimal] = None,
    ) -> Tuple[Optional[Decimal], Optional[str], CostProvenance]:
        """
        Calculates monetary cost for an operation.
        Returns: (cost_amount, pricing_version, cost_provenance)
        """
        # If an authoritative invoice / actual provider cost was already reported
        if actual_cost_override is not None:
            return actual_cost_override.quantize(QUANTIZE_PRECISION, rounding=ROUND_HALF_UP), None, CostProvenance.ACTUAL

        if not model_id:
            return None, None, CostProvenance.UNKNOWN

        registry = get_model_registry()
        try:
            model_def = registry.get(model_id)
        except UnknownModelError:
            # Model not found in canonical registry, cannot determine cost
            return None, None, CostProvenance.UNKNOWN

        pricing: Optional[ModelPricing] = model_def.pricing
        if pricing is None:
            return None, None, CostProvenance.UNKNOWN

        workload = WorkloadEstimate(
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            request_count=request_count,
            image_count=generation_count if generation_count > 0 else None,
        )

        cost = calculate_estimated_cost(pricing=pricing, workload=workload)
        if cost is None:
            return None, pricing.pricing_version, CostProvenance.UNKNOWN

        return cost.quantize(QUANTIZE_PRECISION, rounding=ROUND_HALF_UP), pricing.pricing_version, CostProvenance.ESTIMATED
