"""
ai/mcp/errors.py
================
Structured errors and exception types for MCP subsystem (S27.10).

Invariants:
- Zero credential or internal secret leakage.
- Maps deterministically to client-safe AIError contracts.
- Explicit taxonomy for security violations, timeouts, and authorization denials.
"""

from __future__ import annotations

from typing import Dict, Optional
from pydantic import JsonValue

from ai.contracts.errors import AIError, AIErrorCode


class MCPException(Exception):
    """Base exception for all MCP subsystem errors."""
    def __init__(
        self,
        message: str,
        code: AIErrorCode = AIErrorCode.INTERNAL_ERROR,
        retryable: bool = False,
        details: Optional[Dict[str, JsonValue]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}

    def to_ai_error(self) -> AIError:
        """Converts to canonical client-safe AIError model."""
        return AIError(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            details=self.details if self.details else None,
        )


MCPError = MCPException


class MCPNotFoundError(MCPException):
    """Raised when an MCP server or tool is not found."""
    def __init__(self, target: str, message: Optional[str] = None):
        msg = message or f"MCP entity not found: '{target}'"
        super().__init__(msg, code=AIErrorCode.DEPENDENCY_FAILED, retryable=False, details={"target": target})


class MCPDisabledError(MCPException):
    """Raised when an MCP server or tool is disabled."""
    def __init__(self, target: str):
        super().__init__(
            f"MCP entity '{target}' is disabled in current configuration.",
            code=AIErrorCode.POLICY_DENIED,
            retryable=False,
            details={"target": target},
        )


class MCPOperationNotAllowedError(MCPException):
    """Raised when an operation is forbidden in production runtime."""
    def __init__(self, server_id: str, operation_name: str, reason: str):
        super().__init__(
            f"MCP operation '{server_id}.{operation_name}' is not allowed in production AI runtime: {reason}",
            code=AIErrorCode.POLICY_DENIED,
            retryable=False,
            details={"server_id": server_id, "operation_name": operation_name, "reason": reason},
        )


class MCPTimeoutError(MCPException):
    """Raised when an MCP operation exceeds its bounded execution timeout."""
    def __init__(self, operation_name: str, timeout_seconds: float):
        super().__init__(
            f"MCP operation '{operation_name}' timed out after {timeout_seconds:.1f}s.",
            code=AIErrorCode.TIMEOUT,
            retryable=True,
            details={"operation_name": operation_name, "timeout_seconds": timeout_seconds},
        )


class MCPPathTraversalError(MCPException):
    """Raised when an operation attempts path traversal or accesses unapproved roots."""
    def __init__(self, path: str, reason: str = "Path traversal or unauthorized root access rejected"):
        super().__init__(
            f"Security Violation: {reason} for path '{path}'",
            code=AIErrorCode.POLICY_DENIED,
            retryable=False,
            details={"path": path, "reason": reason},
        )


class MCPShellInjectionError(MCPException):
    """Raised when an argument contains potential shell metacharacters."""
    def __init__(self, argument_name: str, value: str):
        super().__init__(
            f"Security Violation: Potential command injection detected in '{argument_name}'",
            code=AIErrorCode.POLICY_DENIED,
            retryable=False,
            details={"argument_name": argument_name},
        )


class MCPSecurityViolationError(MCPException):
    """Raised on general security or SSRF violations."""
    def __init__(self, violation_type: str, message: str):
        super().__init__(
            f"Security Violation [{violation_type}]: {message}",
            code=AIErrorCode.POLICY_DENIED,
            retryable=False,
            details={"violation_type": violation_type},
        )


class MCPExecutionError(MCPException):
    """Raised when an underlying process or tool returns an execution failure."""
    def __init__(self, operation_name: str, error_detail: str):
        super().__init__(
            f"MCP operation '{operation_name}' execution failed: {error_detail}",
            code=AIErrorCode.DEPENDENCY_FAILED,
            retryable=False,
            details={"operation_name": operation_name, "error_detail": error_detail},
        )
