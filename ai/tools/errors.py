"""
ai/tools/errors.py
==================
Canonical exceptions and error translation for AI Tool execution (S27.9).

Invariants:
- Deterministic mapping to AIErrorCode (AI-02).
- Zero credential or internal infrastructure path leakage.
- Client-safe structured representation via canonical AIError.
"""

from __future__ import annotations

import re
from typing import Dict, Optional
from pydantic import JsonValue

from ai.contracts.errors import AIError, AIErrorCode


class ToolError(Exception):
    """Base class for all AI Tool subsystem exceptions."""
    def __init__(self, message: str, details: Optional[Dict[str, JsonValue]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnknownToolError(ToolError):
    """Raised when an un-registered tool is requested."""
    def __init__(self, tool_name: str):
        super().__init__(
            f"Unknown tool '{tool_name}'. Tool is not registered in the canonical registry.",
            details={"tool_name": tool_name}
        )
        self.tool_name = tool_name


class DisabledToolError(ToolError):
    """Raised when an existing tool is currently disabled by policy."""
    def __init__(self, tool_name: str):
        super().__init__(
            f"Tool '{tool_name}' is currently disabled in this environment.",
            details={"tool_name": tool_name}
        )
        self.tool_name = tool_name


class DuplicateToolError(ToolError):
    """Raised when attempting to register a tool with an already existing name/version."""
    def __init__(self, tool_name: str, version: str):
        super().__init__(
            f"Tool '{tool_name}' (version {version}) is already registered.",
            details={"tool_name": tool_name, "version": version}
        )
        self.tool_name = tool_name
        self.version = version


class ToolInputValidationError(ToolError):
    """Raised when model-supplied parameters fail schema validation."""
    def __init__(self, tool_name: str, validation_errors: str):
        super().__init__(
            f"Invalid input parameters for tool '{tool_name}': {validation_errors}",
            details={"tool_name": tool_name, "errors": validation_errors}
        )
        self.tool_name = tool_name


class ToolOutputValidationError(ToolError):
    """Raised when domain adapter result fails output schema validation."""
    def __init__(self, tool_name: str, validation_errors: str):
        super().__init__(
            f"Tool '{tool_name}' produced an invalid output payload: {validation_errors}",
            details={"tool_name": tool_name, "errors": validation_errors}
        )
        self.tool_name = tool_name


class ToolAuthorizationError(ToolError):
    """Base class for tool authorization failures."""
    pass


class ToolTenantAccessDeniedError(ToolAuthorizationError):
    """Raised when caller attempts to access a resource in another tenant workspace."""
    def __init__(self, actor_id: str, workspace_id: str, resource_id: str):
        super().__init__(
            f"Access denied: Actor '{actor_id}' in workspace '{workspace_id}' cannot access resource '{resource_id}'.",
            details={
                "actor_id": actor_id,
                "workspace_id": workspace_id,
                "resource_id": resource_id,
            }
        )
        self.actor_id = actor_id
        self.workspace_id = workspace_id
        self.resource_id = resource_id


class ToolPermissionDeniedError(ToolAuthorizationError):
    """Raised when caller lacks required permission action for the tool."""
    def __init__(self, actor_id: str, tool_name: str, required_permission: str):
        super().__init__(
            f"Permission denied: Actor '{actor_id}' lacks required permission '{required_permission}' for tool '{tool_name}'.",
            details={
                "actor_id": actor_id,
                "tool_name": tool_name,
                "required_permission": required_permission,
            }
        )
        self.actor_id = actor_id
        self.tool_name = tool_name
        self.required_permission = required_permission


# =============================================================================
# S28-M03 Capability Gateway Exceptions
# =============================================================================

class CapabilityError(Exception):
    """Base error for all Capability and Gateway exceptions."""
    def __init__(self, message: str, code: str = "CAPABILITY_ERROR", details: Optional[Dict[str, JsonValue]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class CapabilityNotFoundError(CapabilityError):
    def __init__(self, capability_id: str):
        super().__init__(
            f"Capability '{capability_id}' not found in canonical catalog.",
            code="CAPABILITY_NOT_FOUND",
            details={"capability_id": capability_id},
        )
        self.capability_id = capability_id


class CapabilityForbiddenError(CapabilityError):
    def __init__(self, capability_id: str, reason: str, actor_id: Optional[str] = None):
        super().__init__(
            f"Access denied to capability '{capability_id}': {reason}",
            code="CAPABILITY_FORBIDDEN",
            details={"capability_id": capability_id, "reason": reason, "actor_id": actor_id or "anonymous"},
        )
        self.capability_id = capability_id


class TenantScopeViolationError(CapabilityError):
    def __init__(self, capability_id: str, message: str, details: Optional[Dict[str, JsonValue]] = None):
        super().__init__(message, code="TENANT_SCOPE_VIOLATION", details=details)


class NetworkPolicyViolationError(CapabilityError):
    def __init__(self, message: str, details: Optional[Dict[str, JsonValue]] = None):
        super().__init__(message, code="NETWORK_POLICY_VIOLATION", details=details)


class IdempotencyConflictError(CapabilityError):
    def __init__(self, idempotency_key: str, message: str):
        super().__init__(
            message,
            code="IDEMPOTENCY_CONFLICT",
            details={"idempotency_key": idempotency_key},
        )
        self.idempotency_key = idempotency_key


class CapabilityInputValidationError(CapabilityError):
    def __init__(self, capability_id: str, validation_errors: str):
        super().__init__(
            f"Input contract validation failed for capability '{capability_id}': {validation_errors}",
            code="INVALID_INPUT",
            details={"capability_id": capability_id, "validation_errors": validation_errors},
        )
        self.capability_id = capability_id


class CapabilityOutputValidationError(CapabilityError):
    def __init__(self, capability_id: str, validation_errors: str):
        super().__init__(
            f"Output contract validation failed for capability '{capability_id}': {validation_errors}",
            code="OUTPUT_CONTRACT_VIOLATION",
            details={"capability_id": capability_id, "validation_errors": validation_errors},
        )
        self.capability_id = capability_id


class CapabilityTimeoutError(CapabilityError):
    def __init__(self, capability_id: str, timeout_seconds: float):
        super().__init__(
            f"Capability '{capability_id}' timed out after {timeout_seconds} seconds.",
            code="TIMEOUT",
            details={"capability_id": capability_id, "timeout_seconds": timeout_seconds},
        )
        self.capability_id = capability_id


class CapabilityCancelledError(CapabilityError):
    def __init__(self, capability_id: str):
        super().__init__(
            f"Capability '{capability_id}' execution was cancelled.",
            code="CANCELLED",
            details={"capability_id": capability_id},
        )
        self.capability_id = capability_id


class ToolTimeoutError(ToolError):
    """Raised when tool execution exceeds bounded timeout."""
    def __init__(self, tool_name: str, timeout_seconds: float):
        super().__init__(
            f"Execution of tool '{tool_name}' timed out after {timeout_seconds} seconds.",
            details={"tool_name": tool_name, "timeout_seconds": timeout_seconds}
        )
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds


class ToolDomainExecutionError(ToolError):
    """Raised when the underlying domain service fails during execution."""
    def __init__(self, tool_name: str, error_message: str):
        super().__init__(
            f"Domain execution failed for tool '{tool_name}': {error_message}",
            details={"tool_name": tool_name, "error_message": error_message}
        )
        self.tool_name = tool_name


# Sanitizer pattern for credentials
_FORBIDDEN_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|client[_-]?secret|password)\s*[:=]\s*\S+", re.IGNORECASE),
]


def _sanitize_string(val: str) -> str:
    res = val
    for pat in _FORBIDDEN_PATTERNS:
        res = pat.sub("[REDACTED]", res)
    return res


def to_ai_error(exc: Exception) -> AIError:
    """Translates any exception into a canonical, sanitized client-safe AIError."""
    if isinstance(exc, CapabilityNotFoundError) or exc.__class__.__name__ in ("ImplementationSecurityBlockedError", "ImplementationUnavailableError"):
        return AIError(
            code=AIErrorCode.CAPABILITY_UNAVAILABLE,
            message=_sanitize_string(str(exc)),
            retryable=False,
            details=getattr(exc, "details", None),
        )
    if isinstance(exc, CapabilityForbiddenError):
        return AIError(
            code=AIErrorCode.POLICY_DENIED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, TenantScopeViolationError):
        return AIError(
            code=AIErrorCode.TENANT_ACCESS_DENIED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, CapabilityInputValidationError):
        return AIError(
            code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, CapabilityOutputValidationError):
        return AIError(
            code=AIErrorCode.INVALID_MODEL_OUTPUT,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, CapabilityTimeoutError):
        return AIError(
            code=AIErrorCode.TIMEOUT,
            message=_sanitize_string(exc.message),
            retryable=True,
            details=exc.details,
        )
    if isinstance(exc, CapabilityCancelledError):
        return AIError(
            code=AIErrorCode.CANCELLED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, NetworkPolicyViolationError):
        return AIError(
            code=AIErrorCode.POLICY_DENIED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, IdempotencyConflictError):
        return AIError(
            code=AIErrorCode.POLICY_DENIED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, UnknownToolError):
        return AIError(
            code=AIErrorCode.CAPABILITY_UNAVAILABLE,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, DisabledToolError):
        return AIError(
            code=AIErrorCode.CAPABILITY_UNAVAILABLE,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, ToolTenantAccessDeniedError):
        return AIError(
            code=AIErrorCode.TENANT_ACCESS_DENIED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=exc.details,
        )
    if isinstance(exc, (ToolPermissionDeniedError, ToolAuthorizationError)):
        return AIError(
            code=AIErrorCode.POLICY_DENIED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=getattr(exc, "details", None),
        )
    if isinstance(exc, (ToolInputValidationError, ToolOutputValidationError)):
        return AIError(
            code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=getattr(exc, "details", None),
        )
    if isinstance(exc, ToolTimeoutError):
        return AIError(
            code=AIErrorCode.TIMEOUT,
            message=_sanitize_string(exc.message),
            retryable=True,
            details=getattr(exc, "details", None),
        )
    if isinstance(exc, ToolDomainExecutionError):
        return AIError(
            code=AIErrorCode.DEPENDENCY_FAILED,
            message=_sanitize_string(exc.message),
            retryable=False,
            details=getattr(exc, "details", None),
        )
    
    if hasattr(exc, "to_ai_error") and callable(exc.to_ai_error):
        return exc.to_ai_error()

    # Generic fallback
    sanitized_msg = _sanitize_string(str(exc)) or "An internal error occurred during tool execution."
    return AIError(
        code=AIErrorCode.INTERNAL_ERROR,
        message=sanitized_msg,
        retryable=False,
        details=None,
    )
