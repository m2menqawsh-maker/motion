"""
ai/contracts/errors.py
======================
Canonical error taxonomy and structured error contract for the AI subsystem.

Invariants:
- Never leaks internal credentials (API keys, bearer tokens) or raw stack traces.
- Client-safe structured representation with deterministic serialization.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, Optional
from pydantic import Field, JsonValue, field_validator

from ai.contracts.base import AIContractModel, strict_enum


class AIErrorCode(str, Enum):
    """Authoritative error classification for AI subsystem failures."""
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    INVALID_MODEL_OUTPUT = "INVALID_MODEL_OUTPUT"
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    POLICY_DENIED = "POLICY_DENIED"
    TENANT_ACCESS_DENIED = "TENANT_ACCESS_DENIED"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    DEPENDENCY_FAILED = "DEPENDENCY_FAILED"
    CANCELLED = "CANCELLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


AIErrorCodeEnum = strict_enum(AIErrorCode)

# Patterns forbidden from appearing in public error messages to prevent credential leakage
_FORBIDDEN_LEAK_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|client[_-]?secret|password)\s*[:=]\s*\S+", re.IGNORECASE),
]


class AIError(AIContractModel):
    """
    Structured, client-safe error object emitted by the AI subsystem.
    Excludes sensitive infrastructure secrets and un-sanitized exception traces.
    """
    code: AIErrorCodeEnum = Field(description="Canonical machine-readable error code")
    message: str = Field(min_length=1, description="Sanitized client-safe error message")
    retryable: bool = Field(description="Whether the operation may succeed if retried")
    details: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Structured context details safe for client inspection",
    )
    dependency_reference: Optional[str] = Field(
        default=None,
        description="Optional upstream dependency identifier associated with the failure",
    )

    @field_validator("message")
    @classmethod
    def validate_message_safety(cls, val: str) -> str:
        for pat in _FORBIDDEN_LEAK_PATTERNS:
            if pat.search(val):
                raise ValueError("Error message contains potentially sensitive credential or secret pattern")
        return val

    @field_validator("details")
    @classmethod
    def validate_details_safety(cls, val: Optional[Dict[str, JsonValue]]) -> Optional[Dict[str, JsonValue]]:
        if val is None:
            return None
        text_repr = str(val)
        for pat in _FORBIDDEN_LEAK_PATTERNS:
            if pat.search(text_repr):
                raise ValueError("Error details contain potentially sensitive credential or secret pattern")
        return val

    @classmethod
    def create(
        cls,
        code: AIErrorCode | str,
        message: str,
        retryable: Optional[bool] = None,
        details: Optional[Dict[str, JsonValue]] = None,
        dependency_reference: Optional[str] = None,
    ) -> AIError:
        code_enum = AIErrorCode(code) if isinstance(code, str) else code
        if retryable is None:
            retryable = code_enum in {
                AIErrorCode.RATE_LIMITED,
                AIErrorCode.TIMEOUT,
                AIErrorCode.PROVIDER_UNAVAILABLE,
                AIErrorCode.INTERNAL_ERROR,
            }
        return cls(
            code=code_enum,
            message=message,
            retryable=retryable,
            details=details,
            dependency_reference=dependency_reference,
        )

    @classmethod
    def cancelled(cls, message: str = "Operation was cancelled.", details: Optional[Dict[str, JsonValue]] = None) -> AIError:
        return cls.create(AIErrorCode.CANCELLED, message, retryable=False, details=details)

    @classmethod
    def dependency_failed(cls, message: str = "Prerequisite dependency failed.", details: Optional[Dict[str, JsonValue]] = None, dependency_reference: Optional[str] = None) -> AIError:
        return cls.create(AIErrorCode.DEPENDENCY_FAILED, message, retryable=False, details=details, dependency_reference=dependency_reference)

    @classmethod
    def rate_limited(cls, message: str = "Rate limit exceeded.", details: Optional[Dict[str, JsonValue]] = None) -> AIError:
        return cls.create(AIErrorCode.RATE_LIMITED, message, retryable=True, details=details)

    @classmethod
    def policy_denied(cls, message: str = "Policy denied operation.", details: Optional[Dict[str, JsonValue]] = None) -> AIError:
        return cls.create(AIErrorCode.POLICY_DENIED, message, retryable=False, details=details)

    @classmethod
    def timeout(cls, message: str = "Operation timed out.", details: Optional[Dict[str, JsonValue]] = None) -> AIError:
        return cls.create(AIErrorCode.TIMEOUT, message, retryable=True, details=details)

    @classmethod
    def internal_error(cls, message: str = "Internal AI error.", details: Optional[Dict[str, JsonValue]] = None) -> AIError:
        return cls.create(AIErrorCode.INTERNAL_ERROR, message, retryable=True, details=details)


class UnknownProviderError(Exception):
    """Raised when an unknown or unregistered provider identifier is queried or referenced."""
    def __init__(self, provider_id: str):
        super().__init__(f"Unknown provider '{provider_id}'. Must be registered in ProviderRegistry.")
        self.provider_id = provider_id

