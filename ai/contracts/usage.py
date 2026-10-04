"""
ai/contracts/usage.py
=====================
Resource metering and monetary cost contracts for AI subsystem operations.

Invariants:
- Monetary amounts use StrictDecimal precision; binary floating-point authority is strictly banned.
- All measured quantities and costs must be non-negative.
- Currency defaults to ISO 4217 standard (USD).
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from typing_extensions import Self
from pydantic import Field, model_validator

from ai.contracts.base import AIContractModel, StrictDecimal


class UsageUnitRecord(AIContractModel):
    """Auxiliary consumption metric for non-token modalities (e.g., characters, search calls)."""
    unit_type: str = Field(min_length=1, description="Resource metric identifier")
    quantity: StrictDecimal = Field(ge=Decimal(0), description="Measured consumption quantity")


class UsageRecord(AIContractModel):
    """
    Canonical, provider-neutral resource consumption record.
    Supports LLMs, speech synthesis, vision processing, and generative media.
    """
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Number of prompt/input tokens")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Number of completion/output tokens")
    total_tokens: Optional[int] = Field(default=None, ge=0, description="Total tokens consumed")
    audio_seconds: Optional[StrictDecimal] = Field(default=None, ge=Decimal(0), description="Duration of processed audio")
    video_seconds: Optional[StrictDecimal] = Field(default=None, ge=Decimal(0), description="Duration of processed video")
    image_count: Optional[int] = Field(default=None, ge=0, description="Count of images generated or analyzed")
    reported_units: Optional[List[UsageUnitRecord]] = Field(
        default=None,
        description="Optional provider-reported auxiliary consumption units",
    )

    @model_validator(mode="after")
    def validate_token_totals(self) -> Self:
        if self.total_tokens is not None and self.input_tokens is not None and self.output_tokens is not None:
            expected = self.input_tokens + self.output_tokens
            if self.total_tokens != expected:
                raise ValueError(
                    f"total_tokens ({self.total_tokens}) does not match input_tokens ({self.input_tokens}) + output_tokens ({self.output_tokens})"
                )
        return self


class CostEstimate(AIContractModel):
    """
    Precision-safe monetary cost representation for budgeting and accounting.
    Enforces exact Decimal calculations to avoid binary floating-point drift.
    """
    estimated_cost: StrictDecimal = Field(ge=Decimal(0), description="Estimated cost prior to execution")
    reserved_cost: Optional[StrictDecimal] = Field(default=None, ge=Decimal(0), description="Budget reserved during execution")
    actual_cost: Optional[StrictDecimal] = Field(default=None, ge=Decimal(0), description="Final settled cost")
    currency: str = Field(
        default="USD",
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 3-letter currency code (e.g. USD, EUR)",
    )
    pricing_version: Optional[str] = Field(
        default=None,
        description="Identifier of the rate card or pricing matrix used",
    )
