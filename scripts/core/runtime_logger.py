"""
scripts/core/runtime_logger.py — Structured Runtime Logger with Secret Redaction and Rotation (S23 - LED-087).

Guarantees:
- Structured JSONL event logging across global and project contexts.
- Secret redaction: Sanitizes Authorization headers, bearer tokens, API keys, passwords, and sensitive keys.
- Configurable log destination via MOTION_LOG_DIR (does not assume writable repository checkout).
- Bounded file rotation and retention policy (max_bytes and backup_count).
- Optional stdout/stderr sink for containerized production environments (MOTION_LOG_STDOUT=1).
- Non-tracked: Never writes into tracked Git artifacts.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Union
import uuid

from scripts.core.failure_model import FailureInfo, FailureCode

# Sensitive key names subject to masking
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(?i)(authorization|api[_-]?key|token|secret|password|access[_-]?token|refresh[_-]?token|cookie|credential|private[_-]?key)"
)

# Regex to detect bearer tokens or sensitive headers inside strings
BEARER_TOKEN_REGEX = re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{8,}")
API_KEY_REGEX = re.compile(r"(?i)(?:api[_-]?key|secret|token)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{12,})['\"]?")


def redact_sensitive_value(val: Any) -> Any:
    """Recursively redacts secrets and sensitive keys from log payloads."""
    if isinstance(val, dict):
        redacted = {}
        for k, v in val.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_value(v)
        return redacted
    elif isinstance(val, list):
        return [redact_sensitive_value(item) for item in val]
    elif isinstance(val, str):
        masked = BEARER_TOKEN_REGEX.sub("Bearer [REDACTED]", val)
        masked = API_KEY_REGEX.sub(r'\1: "[REDACTED]"', masked)
        return masked
    return val


@dataclass
class RunContext:
    run_id: str
    project_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    attempt: int = 1
    recovery_from_run_id: Optional[str] = None

    def derive(self, component_name: str) -> "RunContext":
        """Creates a child context with a new span_id linked to the current span."""
        short_id = uuid.uuid4().hex[:6]
        new_span = f"{component_name}-a{self.attempt}-{short_id}"
        return RunContext(
            run_id=self.run_id,
            project_id=self.project_id,
            span_id=new_span,
            parent_span_id=self.span_id,
            attempt=1,  # Reset attempt for the child operation
            recovery_from_run_id=self.recovery_from_run_id,
        )

    def derive_retry(self, component_name: str = "retry") -> "RunContext":
        """Creates a new span for the next attempt, linked to the CURRENT span."""
        short_id = uuid.uuid4().hex[:6]
        new_attempt = self.attempt + 1
        new_span = f"{component_name}-a{new_attempt}-{short_id}"
        return RunContext(
            run_id=self.run_id,
            project_id=self.project_id,
            span_id=new_span,
            parent_span_id=self.span_id,
            attempt=new_attempt,
            recovery_from_run_id=self.recovery_from_run_id,
        )


class RuntimeLogger:
    """Structured JSONL Logger with bounded rotation, configurable sink, and redaction."""

    def __init__(
        self,
        context: RunContext,
        log_dir: Optional[Union[str, Path]] = None,
        max_bytes: int = 10_485_760,  # 10MB
        backup_count: int = 5,
    ):
        self.context = context
        self.max_bytes = int(os.environ.get("MOTION_LOG_MAX_BYTES", str(max_bytes)))
        self.backup_count = int(os.environ.get("MOTION_LOG_BACKUP_COUNT", str(backup_count)))

        workspace_root = Path.cwd().resolve()

        # Destination resolution
        env_log_dir = os.environ.get("MOTION_LOG_DIR")
        if log_dir is not None:
            self.global_log_dir = Path(log_dir).resolve()
        elif env_log_dir:
            self.global_log_dir = Path(env_log_dir).resolve()
        else:
            self.global_log_dir = workspace_root / "logs"

        self.global_log_file = self.global_log_dir / "runtime.jsonl"

        self.project_log_file = None
        if self.context.project_id:
            self.project_log_file = workspace_root / "projects" / self.context.project_id / "run.jsonl"

        # Stdout emission flag for container/cloud logging
        self.stdout_sink = os.environ.get("MOTION_LOG_STDOUT", "0").lower() in ("1", "true", "yes")

        # Attempt to ensure the global directory exists, silently fail if impossible
        try:
            self.global_log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[RuntimeLogger Warning] Failed to create global log directory: {e}", file=sys.stderr)

    def redact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from the payload."""
        return redact_sensitive_value(payload)

    def _rotate_file_if_needed(self, file_path: Path):
        """Standard bounded file rotation to prevent unbounded disk growth."""
        if self.backup_count <= 0 or self.max_bytes <= 0:
            return

        try:
            if not file_path.exists() or file_path.stat().st_size < self.max_bytes:
                return

            # Shift older backups
            for i in range(self.backup_count - 1, 0, -1):
                src = file_path.with_name(f"{file_path.name}.{i}")
                dst = file_path.with_name(f"{file_path.name}.{i + 1}")
                if src.exists():
                    if dst.exists():
                        dst.unlink()
                    src.rename(dst)

            # Move current log to .1
            dst_first = file_path.with_name(f"{file_path.name}.1")
            if dst_first.exists():
                dst_first.unlink()
            file_path.rename(dst_first)
        except Exception as e:
            print(f"[RuntimeLogger Warning] File rotation failed: {e}", file=sys.stderr)

    def event(
        self,
        event: str,
        status: str,
        stage: str = None,
        component: str = None,
        level: str = "INFO",
        duration_ms: int = None,
        failure_info: FailureInfo = None,
        payload_extra: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Log a structured event safely to global and project-local jsonl files with secret redaction.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        payload = {
            "timestamp": now,
            "level": level,
            "run_id": self.context.run_id,
            "project_id": self.context.project_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "attempt": self.context.attempt,
            "stage": stage,
            "component": component,
            "event": event,
            "status": status,
            "duration_ms": duration_ms,
        }

        if self.context.recovery_from_run_id:
            payload["recovery_from_run_id"] = self.context.recovery_from_run_id

        if failure_info:
            payload.update(failure_info.to_dict())
            if hasattr(failure_info, "metadata") and hasattr(failure_info.metadata, "severity"):
                payload["level"] = failure_info.metadata.severity.value

        if payload_extra:
            payload.update(payload_extra)
        if kwargs:
            payload.update(kwargs)

        # Redact secrets from entire payload
        sanitized_payload = self.redact(payload)
        log_line = json.dumps(sanitized_payload, ensure_ascii=False) + "\n"

        # Stdout sink
        if self.stdout_sink:
            sys.stdout.write(log_line)
            sys.stdout.flush()

        # Write to Global Log with rotation
        try:
            self._rotate_file_if_needed(self.global_log_file)
            with open(self.global_log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()
        except IOError as e:
            print(f"[RuntimeLogger Warning] Failed to write to global log: {e}", file=sys.stderr)

        # Write to Project Log (if applicable)
        if self.project_log_file:
            try:
                self.project_log_file.parent.mkdir(parents=True, exist_ok=True)
                self._rotate_file_if_needed(self.project_log_file)
                with open(self.project_log_file, "a", encoding="utf-8") as f:
                    f.write(log_line)
                    f.flush()
            except IOError as e:
                print(f"[RuntimeLogger Warning] Failed to write to project log: {e}", file=sys.stderr)
