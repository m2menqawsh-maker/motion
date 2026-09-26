import json
import os
import sys
import datetime
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from scripts.core.failure_model import FailureInfo, FailureCode

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
            attempt=1, # Reset attempt for the child operation
            recovery_from_run_id=self.recovery_from_run_id
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
            recovery_from_run_id=self.recovery_from_run_id
        )

class RuntimeLogger:
    def __init__(self, context: RunContext):
        self.context = context
        
        workspace_root = Path.cwd().resolve()
        self.global_log_dir = workspace_root / "logs"
        self.global_log_file = self.global_log_dir / "runtime.jsonl"
        
        self.project_log_file = None
        if self.context.project_id:
            self.project_log_file = workspace_root / "projects" / self.context.project_id / "run.jsonl"

        # Attempt to ensure the global directory exists, silently fail if impossible
        try:
            self.global_log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[RuntimeLogger Warning] Failed to create global log directory: {e}", file=sys.stderr)

    def event(
        self,
        event: str,
        status: str,
        stage: str = None,
        component: str = None,
        level: str = "INFO",
        duration_ms: int = None,
        failure_info: FailureInfo = None
    ):
        """
        Log a structured event safely to global and project-local jsonl files.
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
            # Override level with severity if present
            payload["level"] = failure_info.metadata.severity.value

        log_line = json.dumps(payload, ensure_ascii=False) + "\n"

        # Write to Global Log
        try:
            with open(self.global_log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()
        except IOError as e:
            print(f"[RuntimeLogger Warning] Failed to write to global log: {e}", file=sys.stderr)
            
        # Write to Project Log (if applicable)
        if self.project_log_file:
            try:
                # Ensure project directory exists
                self.project_log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.project_log_file, "a", encoding="utf-8") as f:
                    f.write(log_line)
                    f.flush()
            except IOError as e:
                print(f"[RuntimeLogger Warning] Failed to write to project log: {e}", file=sys.stderr)
