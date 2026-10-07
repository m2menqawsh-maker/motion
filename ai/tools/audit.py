"""
ai/tools/audit.py
=================
Authoritative operational and security audit logger for AI Tool executions (S27.9).

Invariants:
- Absolute secret isolation: NEVER logs API keys, bearer tokens, passwords, signed URLs,
  raw media payloads, or full model prompts.
- Structured records with deterministic timestamps.
- Thread-safe recording with in-memory retention and optional subsystem logging.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Deque, List, Optional
from pydantic import Field, field_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime
from ai.contracts.tools import ToolCallStatus, ToolCallStatusEnum
from ai.tools.types import (
    AuthorizationDecision,
    AuthorizationDecisionEnum,
    SideEffectClass,
    SideEffectClassEnum,
)

logger = logging.getLogger("ai.tools.audit")

_SENSITIVE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{16,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|client[_-]?secret|password)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"https?://[^\s]+\?[^\s]*(?:sig|token|key|secret)=[^\s]+", re.IGNORECASE),
]


def _assert_no_sensitive_leak(val: Optional[str]) -> Optional[str]:
    if not val:
        return val
    for pat in _SENSITIVE_PATTERNS:
        if pat.search(val):
            raise ValueError(f"Security invariant violated: Audit field contains potential secret or credential: '{pat.pattern}'")
    return val


class ToolAuditRecord(AIContractModel):
    """
    Structured, tamper-resistant audit entry documenting a tool invocation attempt.
    """
    tool_name: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$", description="Canonical tool identifier")
    tool_version: str = Field(pattern=r"^\d+\.\d+\.\d+$", description="Tool definition version")
    actor_id: str = Field(min_length=1, description="Authenticated actor identifier")
    workspace_id: str = Field(min_length=1, description="Authoritative workspace identifier")
    target_resource: Optional[str] = Field(default=None, description="Resource identifier operated on")
    decision: AuthorizationDecisionEnum = Field(description="Server-side authorization decision")
    side_effect_class: SideEffectClassEnum = Field(description="Declared side effect taxonomy")
    timestamp: TzAwareDatetime = Field(description="Timezone-aware occurrence timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Request/execution trace identifier")
    status: ToolCallStatusEnum = Field(description="Outcome status of invocation")
    duration_ms: int = Field(ge=0, description="Total execution duration in milliseconds")
    error_code: Optional[str] = Field(default=None, description="Mapped error classification if failed")

    @field_validator("actor_id", "workspace_id", "target_resource", "error_code")
    @classmethod
    def validate_safety(cls, v: Optional[str]) -> Optional[str]:
        return _assert_no_sensitive_leak(v)


class ToolAuditRecorder:
    """Thread-safe recorder and queryable buffer for ToolAuditRecords."""

    def __init__(self, max_records: int = 1000):
        self._buffer: Deque[ToolAuditRecord] = deque(maxlen=max_records)
        self._lock = threading.Lock()

    def record(self, record: ToolAuditRecord) -> None:
        """Stores a structured audit entry and logs a sanitized event."""
        with self._lock:
            self._buffer.append(record)

        log_level = logging.INFO if record.status == ToolCallStatus.SUCCESS else logging.WARNING
        logger.log(
            log_level,
            "TOOL_AUDIT: tool=%s actor=%s ws=%s decision=%s status=%s ms=%d err=%s",
            record.tool_name,
            record.actor_id,
            record.workspace_id,
            record.decision.value if hasattr(record.decision, "value") else record.decision,
            record.status.value if hasattr(record.status, "value") else record.status,
            record.duration_ms,
            record.error_code,
        )

    def get_records(
        self,
        tool_name: Optional[str] = None,
        workspace_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> List[ToolAuditRecord]:
        """Returns snapshot of recorded entries filtered by query criteria."""
        with self._lock:
            items = list(self._buffer)

        if tool_name:
            items = [r for r in items if r.tool_name == tool_name]
        if workspace_id:
            items = [r for r in items if r.workspace_id == workspace_id]
        if actor_id:
            items = [r for r in items if r.actor_id == actor_id]
        return items

    def clear(self) -> None:
        """Clears all audit entries (primarily for test resets)."""
        with self._lock:
            self._buffer.clear()


# Default global recorder instance
default_audit_recorder = ToolAuditRecorder()
