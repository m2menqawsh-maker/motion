"""
ai/taste/contracts.py
=====================
Contracts and domain exceptions for Taste Engine (S28-04).
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel
from ai.contracts.creative.taste import (
    TasteContext,
    TasteDecision,
    TasteRule,
    TasteRuleSeverity,
)


class TasteEngineError(Exception):
    """Base exception for Taste Engine subsystem."""
    pass


class TasteRuleNotFoundError(TasteEngineError):
    """Raised when a referenced taste rule does not exist in registry."""
    pass


class DuplicateTasteRuleError(TasteEngineError):
    """Raised when attempting to register a duplicate rule without override flag."""
    pass


class InvalidTasteRuleError(TasteEngineError):
    """Raised when a TasteRule violates structural or provenance invariants."""
    pass


class TasteEvaluationResult(AIContractModel):
    """Detailed evaluation result of a taste rule against a specific context."""
    rule_id: str = Field(description="Evaluated TasteRule identifier")
    is_applicable: bool = Field(description="Whether rule criteria are satisfied")
    confidence: float = Field(ge=0.0, le=1.0, description="Evaluation confidence score")
    evidence: List[str] = Field(default_factory=list, description="Concrete evidence lines justifying applicability")
    waived_by_exception: Optional[str] = Field(default=None, description="Exception reason if rule was waived")
