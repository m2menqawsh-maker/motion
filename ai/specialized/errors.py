"""
ai/specialized/errors.py
========================
Exception classes for Specialized Media AI (S27.17 / AI-13).

Invariants:
- Derives from Exception so it can be raised and caught in Python.
- Maps deterministically to canonical client-safe AIError contracts.
"""

from __future__ import annotations

from typing import Dict, Optional
from pydantic import JsonValue

from ai.contracts.errors import AIError, AIErrorCode


class SpecializedMediaError(Exception):
    """Base exception for specialized media AI failures."""

    def __init__(
        self,
        code: AIErrorCode,
        message: str,
        retryable: bool = False,
        details: Optional[Dict[str, JsonValue]] = None,
        dependency_reference: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details
        self.dependency_reference = dependency_reference
        super().__init__(f"[{code.value}] {message}")

    def to_ai_error(self) -> AIError:
        return AIError(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            details=self.details,
            dependency_reference=self.dependency_reference,
        )
