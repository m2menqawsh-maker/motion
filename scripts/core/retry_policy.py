from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timezone
import time
from pydantic import BaseModel, Field

from scripts.core.failure_model import FailureInfo, FailureCode, RetryDisposition
from scripts.core.state_model import (
    LifecycleState,
    EvidenceStatus,
    ProjectState,
)
from scripts.core.state_store import StateStore


class IdempotencyClass(str, Enum):
    SAFE_TO_RETRY = "SAFE_TO_RETRY"
    CONDITIONALLY_RETRYABLE = "CONDITIONALLY_RETRYABLE"
    NOT_RETRYABLE = "NOT_RETRYABLE"


@dataclass
class RetryDecision:
    should_retry: bool
    reason: str
    next_attempt: int
    delay_seconds: int
    max_attempts: int


class RetryContext(BaseModel):
    project_id: str
    stage: str
    operation: str
    attempt: int = 1
    expected_revision: int
    input_fingerprints: Dict[str, str] = Field(default_factory=dict)
    evidence_paths: List[str] = Field(default_factory=list)
    idempotency: IdempotencyClass = IdempotencyClass.CONDITIONALLY_RETRYABLE
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RetryPolicyEngine:
    """
    Authoritative engine for safe retry evaluation, precondition validation,
    and structured failure attempt persistence (S08).
    """

    @staticmethod
    def evaluate(
        failure: FailureInfo,
        idempotency: IdempotencyClass,
        current_attempt: int,
        is_state_valid: bool = True,
    ) -> RetryDecision:
        meta = failure.metadata
        max_attempts = RetryPolicyEngine._get_max_attempts(failure.code)

        # 1. Is failure retryable by its canonical disposition?
        if meta.retry_disposition == RetryDisposition.NEVER or not meta.retryable:
            return RetryDecision(
                should_retry=False,
                reason=f"Failure {failure.code.name} is not retryable (disposition: NEVER)",
                next_attempt=current_attempt,
                delay_seconds=0,
                max_attempts=max_attempts,
            )

        # 2. Is operation idempotency class allowed?
        if idempotency == IdempotencyClass.NOT_RETRYABLE:
            return RetryDecision(
                should_retry=False,
                reason="Operation is NOT_RETRYABLE",
                next_attempt=current_attempt,
                delay_seconds=0,
                max_attempts=max_attempts,
            )

        # 3. Have max attempts been exhausted?
        if current_attempt >= max_attempts:
            return RetryDecision(
                should_retry=False,
                reason=f"Max attempts exhausted ({max_attempts})",
                next_attempt=current_attempt,
                delay_seconds=0,
                max_attempts=max_attempts,
            )

        # 4. Is current state / runtime valid for retry?
        if not is_state_valid:
            return RetryDecision(
                should_retry=False,
                reason="State is invalid for retry",
                next_attempt=current_attempt,
                delay_seconds=0,
                max_attempts=max_attempts,
            )

        # 5. All checks passed -> schedule retry
        next_attempt = current_attempt + 1
        delay_seconds = RetryPolicyEngine._get_backoff(current_attempt)

        return RetryDecision(
            should_retry=True,
            reason=f"Retrying after {failure.code.name}",
            next_attempt=next_attempt,
            delay_seconds=delay_seconds,
            max_attempts=max_attempts,
        )

    @classmethod
    def verify_preconditions(
        cls,
        arg1: Any,
        arg2: Any,
    ) -> Tuple[bool, str]:
        if isinstance(arg1, RetryContext):
            return cls.validate_retry_preconditions(arg1, arg2)
        else:
            return cls.validate_retry_preconditions(arg2, arg1)

    @classmethod
    def validate_retry_preconditions(
        cls,
        context: RetryContext,
        project_dir: Path | str,
    ) -> Tuple[bool, str]:
        """
        Validates all runtime preconditions before permitting a conditional retry:
        1. Canonical state file exists and can be loaded.
        2. Expected state revision matches persisted revision on disk (no divergence).
        3. Input file fingerprints (sha256) match initial attempt values (no input tampering).
        4. Evidence relied upon has not been marked INVALIDATED or SUPERSEDED.
        5. For render operations, verifies canonical approval_metadata (approved_by), rejecting .studio_approved alone.
        """
        pdir = Path(project_dir)
        try:
            state = StateStore.load(pdir)
        except Exception as e:
            return False, f"Failed to load project state: {e}"

        if not state:
            return False, "Project state does not exist on disk"

        # Precondition A: State revision must match expected revision
        if state.revision != context.expected_revision:
            return (
                False,
                f"Stale revision: state revision is {state.revision}, context expected {context.expected_revision}",
            )

        # Precondition B: Input fingerprints must match
        for rel_path, expected_hash in context.input_fingerprints.items():
            input_file = pdir / rel_path
            if not input_file.exists():
                return False, f"Input file '{rel_path}' is missing on disk for retry"
            actual_hash = StateStore._compute_sha256(input_file)
            if actual_hash != expected_hash:
                return (
                    False,
                    f"Input fingerprint mismatch for '{rel_path}': content has changed on disk",
                )

        # Precondition C: Evidence must not be INVALIDATED or SUPERSEDED
        for ev_path in context.evidence_paths:
            rec = state.get_artifact_record(ev_path)
            if rec is not None:
                status = getattr(rec, "status", EvidenceStatus.VALID)
                if isinstance(status, str):
                    try:
                        status = EvidenceStatus(status)
                    except ValueError:
                        status = EvidenceStatus.VALID
                if status == EvidenceStatus.INVALIDATED:
                    return (
                        False,
                        f"Required evidence '{ev_path}' was INVALIDATED (reason: {rec.invalidated_reason})",
                    )
                if status == EvidenceStatus.SUPERSEDED:
                    return (
                        False,
                        f"Required evidence '{ev_path}' was SUPERSEDED by newer revision",
                    )

        # Precondition D: Render authorization requires canonical structured approval (S07.5 Obs A, S09 ReviewService)
        if context.stage == "render" or "render" in context.operation.lower():
            from scripts.core.review_service import ReviewService
            is_auth, auth_msg = ReviewService.is_render_authorized(project_dir)
            if not is_auth:
                return (
                    False,
                    f"Render operation requires canonical review authorization: {auth_msg}",
                )

        return True, "Preconditions valid for retry"

    @classmethod
    def record_failure_attempt(
        cls,
        project_dir: Path | str,
        failure: FailureInfo,
        attempt: int,
        will_retry: bool,
        operation_id: Optional[str] = None,
        timeout: Optional[float] = 10.0,
    ) -> Optional[ProjectState]:
        """
        Authoritatively persists structured error and retry history into ProjectState.
        Uses StateStore.atomic_update to maintain CAS and monotonic revision guarantees.
        """
        pdir = Path(project_dir)
        state_file = pdir / StateStore.STATE_FILE
        if not state_file.exists():
            return None

        current = StateStore.load(pdir)
        if not current:
            return None

        def mutator(working_copy: ProjectState) -> None:
            now_iso = datetime.now(timezone.utc).isoformat()

            # 1. Append to structured_errors
            err_entry = {
                "code": failure.code.value,
                "category": failure.metadata.category.value,
                "severity": failure.metadata.severity.value,
                "message": failure.message,
                "cause_type": failure.cause_type,
                "stage": failure.stage,
                "component": failure.component,
                "attempt": attempt,
                "will_retry": will_retry,
                "timestamp": now_iso,
                "operation_id": operation_id,
            }
            working_copy.structured_errors.append(err_entry)

            # 2. Append to run_metadata["retry_history"]
            event_type = "RETRY_SCHEDULED" if will_retry else "ATTEMPT_FAILED"
            history_entry = {
                "event": event_type,
                "attempt": attempt,
                "code": failure.code.value,
                "will_retry": will_retry,
                "stage": failure.stage,
                "component": failure.component,
                "timestamp": now_iso,
            }
            retry_history = working_copy.run_metadata.setdefault("retry_history", [])
            retry_history.append(history_entry)

        return StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=current.revision,
            mutator=mutator,
            timeout=timeout,
        )

    @staticmethod
    def _get_max_attempts(code: FailureCode) -> int:
        meta = failure_metadata = FailureInfo(code=code, message="").metadata
        return meta.max_attempts

    @staticmethod
    def _get_backoff(current_attempt: int) -> int:
        """
        Exponential / staged backoff.
        current_attempt 1 -> 1s
        current_attempt 2 -> 2s
        current_attempt 3+ -> 4s
        """
        if current_attempt == 1:
            return 1
        elif current_attempt == 2:
            return 2
        else:
            return 4

    @staticmethod
    def delay_for(decision: RetryDecision) -> None:
        """Abstraction for delaying. Can be mocked in tests."""
        if decision.should_retry and decision.delay_seconds > 0:
            time.sleep(decision.delay_seconds)


# Alias for backward and cross-module compatibility
RetryPolicy = RetryPolicyEngine
