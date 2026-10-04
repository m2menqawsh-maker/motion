"""
ai/mcp/audit.py
===============
Safe, bounded audit recording for MCP invocations (S27.10).

Invariants:
- Redacts sensitive credentials, tokens, and keys.
- Records structured invocation metrics: server, operation, duration, actor, status.
- Thread-safe in-memory recording with bounded ring buffer.
"""

from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel


# Credential masking patterns
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|client[_-]?secret|password|token)\s*[:=]\s*(\S+)", re.IGNORECASE),
]


def sanitize_audit_text(text: str) -> str:
    """Masks potential secrets and authentication tokens from audit logs."""
    sanitized = text
    for pat in _SECRET_PATTERNS:
        sanitized = pat.sub("[REDACTED]", sanitized)
    return sanitized


class MCPAuditRecord(AIContractModel):
    """Structured audit log record for an individual MCP execution."""
    server_id: str = Field(description="Target MCP server ID")
    operation_name: str = Field(description="Name of invoked operation")
    actor_id: str = Field(description="Trusted actor ID from server context")
    workspace_id: str = Field(description="Trusted workspace ID from server context")
    target_resource: Optional[str] = Field(default=None, description="Sanitized resource reference")
    status: str = Field(description="Execution outcome: SUCCESS, ERROR, TIMEOUT, DENIED")
    duration_ms: int = Field(ge=0, description="Execution duration in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code if failed")


class MCPAuditRecorder:
    """Thread-safe bounded audit logger for MCP executions."""
    def __init__(self, capacity: int = 1000):
        self._capacity = capacity
        self._records: List[MCPAuditRecord] = []
        self._lock = threading.Lock()

    def record(self, record: MCPAuditRecord) -> None:
        """Appends an audit record, maintaining fixed buffer capacity."""
        with self._lock:
            if len(self._records) >= self._capacity:
                self._records.pop(0)
            self._records.append(record)

    def get_records(
        self,
        server_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MCPAuditRecord]:
        """Queries recorded audit logs with optional filtering."""
        with self._lock:
            filtered = list(self._records)

        if server_id:
            filtered = [r for r in filtered if r.server_id == server_id]
        if workspace_id:
            filtered = [r for r in filtered if r.workspace_id == workspace_id]

        return filtered[-limit:]

    def clear(self) -> None:
        """Clears audit records (for test isolation)."""
        with self._lock:
            self._records.clear()


default_mcp_audit_recorder = MCPAuditRecorder()
