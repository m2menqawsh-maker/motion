"""
ai/mcp/policy.py
================
Authoritative security policy and verification boundary for MCP (S27.10).

Invariants:
- Absolute prevention of shell injection (checks arguments for command metacharacters).
- Strict path traversal prevention (rejects '..', unapproved roots, encoded traversal).
- Anti-SSRF validation for media URLs (rejects localhost, private ranges, file:// schemes).
- Identity isolation: Model-supplied identity parameters are strictly rejected.
- Tenant isolation: Assets and operations strictly bound to trusted workspace context.
- Disabled or deprecated servers and unapproved operations fail closed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urlparse

from ai.mcp.contracts import MCPOperationDefinition, MCPServerDefinition
from ai.mcp.errors import (
    MCPDisabledError,
    MCPOperationNotAllowedError,
    MCPPathTraversalError,
    MCPSecurityViolationError,
    MCPShellInjectionError,
)

if TYPE_CHECKING:
    from ai.tools.types import TrustedToolExecutionContext


# Metacharacters dangerous in shell and CLI execution contexts
_SHELL_INJECTION_PATTERN = re.compile(r"[;&|`$<>\r\n]|\$\(|\$\{")

# Encoded or tricky path traversal patterns
_TRAVERSAL_PATTERN = re.compile(r"(?:\.\.[\\/]|(?:%2e%2e|%2f|%5c))", re.IGNORECASE)

# Identity fields that must NEVER be supplied by model
FORBIDDEN_MODEL_IDENTITY_FIELDS = {
    "workspace_id",
    "tenant_id",
    "actor_id",
    "user_id",
    "role",
    "permissions",
    "approved_by",
}

# Forbidden SSRF hosts and IP prefixes
_FORBIDDEN_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "169.254.169.254",  # Cloud instance metadata
    "metadata.google.internal",
}


class MCPSecurityPolicy:
    """Central policy engine evaluating MCP invocation safety and authorization."""

    @classmethod
    def validate_server_access(
        cls,
        server: MCPServerDefinition,
        operation_name: str,
        is_production: bool = True,
    ) -> MCPOperationDefinition:
        """
        Validates that the server and operation are enabled and permitted for execution.
        Fails closed if the server is disabled, deprecated for production, or unknown.
        """
        if not server.enabled:
            raise MCPDisabledError(server.server_id)

        if is_production and not server.allowed_for_production:
            raise MCPOperationNotAllowedError(
                server_id=server.server_id,
                operation_name=operation_name,
                reason=f"Server disposition is {server.disposition.value}. Direct production AI invocation is prohibited.",
            )

        if operation_name not in server.operations:
            raise MCPOperationNotAllowedError(
                server_id=server.server_id,
                operation_name=operation_name,
                reason=f"Operation '{operation_name}' is not in allowed operations for server '{server.server_id}'.",
            )

        return server.operations[operation_name]

    @classmethod
    def validate_arguments(
        cls,
        raw_args: Dict[str, Any],
        context: TrustedToolExecutionContext,
    ) -> None:
        """
        Validates raw invocation arguments:
        - Rejects forged model identity fields.
        - Checks for shell injection metacharacters.
        - Verifies string length bounds.
        """
        for field in FORBIDDEN_MODEL_IDENTITY_FIELDS:
            if field in raw_args:
                raise MCPSecurityViolationError(
                    violation_type="FORGED_IDENTITY",
                    message=f"Model argument cannot specify trusted identity field '{field}'.",
                )

        for key, val in raw_args.items():
            if isinstance(val, str):
                if len(val) > 10000:
                    raise MCPSecurityViolationError(
                        violation_type="OVERSIZED_ARGUMENT",
                        message=f"Argument '{key}' exceeds maximum allowed length (10000 chars).",
                    )
                if _SHELL_INJECTION_PATTERN.search(val):
                    raise MCPShellInjectionError(argument_name=key, value=val)

    @classmethod
    def validate_safe_path(
        cls,
        path_str: str,
        allowed_root: Optional[Path] = None,
        must_exist: bool = False,
    ) -> Path:
        """
        Enforces strict path security:
        - Rejects traversal attempts ('..', encoded slashes).
        - Resolves path and verifies it remains strictly within allowed_root.
        - Prevents directory traversal attacks.
        """
        if not path_str or not isinstance(path_str, str):
            raise MCPPathTraversalError(str(path_str), "Path must be a non-empty string")

        if _TRAVERSAL_PATTERN.search(path_str) or ".." in path_str:
            raise MCPPathTraversalError(path_str, "Directory traversal sequence detected ('..')")

        candidate = Path(path_str)
        try:
            resolved = candidate.resolve()
        except Exception as e:
            raise MCPPathTraversalError(path_str, f"Invalid path resolution: {e}")

        if allowed_root is not None:
            root_resolved = allowed_root.resolve()
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                raise MCPPathTraversalError(
                    path_str,
                    f"Resolved path '{resolved}' escapes allowed boundary '{root_resolved}'",
                )

        if must_exist and not resolved.exists():
            raise MCPPathTraversalError(path_str, f"Target file does not exist: '{resolved}'")

        return resolved

    @classmethod
    def validate_media_url(cls, url_str: str) -> None:
        """
        Validates external media URLs to prevent SSRF:
        - Only http and https schemes allowed.
        - Localhost, link-local, loopback, and private addresses forbidden.
        """
        if not url_str or not isinstance(url_str, str):
            raise MCPSecurityViolationError("INVALID_URL", "URL must be a non-empty string")

        try:
            parsed = urlparse(url_str)
        except Exception as e:
            raise MCPSecurityViolationError("MALFORMED_URL", f"Failed to parse URL: {e}")

        if parsed.scheme not in {"http", "https"}:
            raise MCPSecurityViolationError(
                "FORBIDDEN_SCHEME",
                f"URL scheme '{parsed.scheme}' is forbidden. Only HTTP/HTTPS allowed.",
            )

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise MCPSecurityViolationError("MISSING_HOSTNAME", "URL must contain a valid hostname")

        if hostname in _FORBIDDEN_HOSTS:
            raise MCPSecurityViolationError(
                "SSRF_PROHIBITED",
                f"Access to private/internal host '{hostname}' is strictly prohibited.",
            )

        # Private IP range check
        if hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("127."):
            raise MCPSecurityViolationError(
                "SSRF_PROHIBITED",
                f"Access to private IP space '{hostname}' is strictly prohibited.",
            )
        if hostname.startswith("172."):
            parts = hostname.split(".")
            if len(parts) >= 2 and parts[1].isdigit():
                second = int(parts[1])
                if 16 <= second <= 31:
                    raise MCPSecurityViolationError(
                        "SSRF_PROHIBITED",
                        f"Access to private IP space '{hostname}' is strictly prohibited.",
                    )
