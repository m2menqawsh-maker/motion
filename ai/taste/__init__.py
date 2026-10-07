"""
ai/taste/__init__.py
====================
Taste Engine package for S28-04.
"""

from ai.taste.contracts import (
    DuplicateTasteRuleError,
    InvalidTasteRuleError,
    TasteEngineError,
    TasteEvaluationResult,
    TasteRuleNotFoundError,
)
from ai.contracts.creative.taste import TasteDecision
from ai.taste.context import TasteContextBuilder
from ai.taste.evaluator import TasteEvaluator
from ai.taste.registry import TasteRuleRegistry
from ai.taste.engine import TasteEngine

__all__ = [
    "DuplicateTasteRuleError",
    "InvalidTasteRuleError",
    "TasteContextBuilder",
    "TasteDecision",
    "TasteEngine",
    "TasteEngineError",
    "TasteEvaluationResult",
    "TasteEvaluator",
    "TasteRuleNotFoundError",
    "TasteRuleRegistry",
]
