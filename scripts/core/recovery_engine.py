"""
Recovery Engine, Planner & Service (S07).

Provides:
- RecoveryPlan model
- RecoveryPlanner: creates structured rollback/reconciliation plans
- RecoveryService: executes atomic rollback with CAS, marking invalidated evidence
- RecoveryEngine: evaluates resumability and produces decisions
"""

import os
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Set, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
    EvidenceStatus,
    ProjectState,
    ArtifactRecord,
    StateMachine,
)
from scripts.core.state_store import (
    StateStore,
    StateStoreError,
    StateNotFoundError,
    StateCorruptedError,
    StateIOError,
)
from scripts.core.evidence_matrix import (
    RequiredEvidencePolicy,
    EvidenceValidationResult,
)


LIFECYCLE_ORDER: List[LifecycleState] = StateMachine.get_topological_order()


class RecoveryPlan(BaseModel):
    model_config = ConfigDict(extra='ignore')

    plan_id: str = Field(default_factory=lambda: f"rec-{uuid.uuid4().hex[:8]}")
    project_id: str
    current_state: LifecycleState
    last_valid_state: LifecycleState
    target_state: LifecycleState
    expected_revision: int
    stages_to_replay: List[LifecycleState] = Field(default_factory=list)
    invalidated_evidence_paths: List[str] = Field(default_factory=list)
    stale_disk_paths: List[str] = Field(default_factory=list)
    reason: str
    requires_manual_action: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ResumeDecision:
    can_resume: bool
    next_state: Optional[LifecycleState]
    reason: str
    recommended_action: Optional[str] = None
    validation_result: Optional[EvidenceValidationResult] = None
    recovery_plan: Optional[RecoveryPlan] = None


class RecoveryPlanner:
    """
    Authoritative planner for state recovery and rollback.
    Determines the highest valid lifecycle state whose required evidence is 100% satisfied.
    """

    @classmethod
    def is_state_valid(cls, cand: LifecycleState, state: ProjectState, project_dir: Path) -> bool:
        """
        Determines if candidate lifecycle state has 100% valid required evidence on disk and in records.
        """
        if cand == LifecycleState.DRAFT:
            return True

        if cand == LifecycleState.REVIEW_APPROVED:
            approved_by = state.approval_metadata.get("approved_by") if state.approval_metadata else None
            approval_status = state.approval_metadata.get("status") if state.approval_metadata else None
            if not approved_by or approval_status == "INVALIDATED":
                return False

        required_items = RequiredEvidencePolicy.get_required_evidence(cand)
        valid_records = {
            r.path: r for r in state.artifact_records
            if getattr(r, "status", EvidenceStatus.VALID) == EvidenceStatus.VALID
        }

        for item in required_items:
            rec = valid_records.get(item.path)
            if rec is None:
                return False
            file_path = project_dir / item.path
            if not file_path.exists():
                return False
            st = file_path.stat()
            if st.st_size < item.min_size_bytes:
                return False
            if rec.validation in (ValidationLevel.SIZE, ValidationLevel.SHA256) and rec.size_bytes is not None:
                if st.st_size != rec.size_bytes:
                    return False
            if rec.validation == ValidationLevel.SHA256 and rec.sha256 is not None:
                if StateStore._compute_sha256(file_path) != rec.sha256:
                    return False
        return True

    @classmethod
    def create_plan(
        cls,
        project_dir: Path | str,
        state: Optional[ProjectState] = None,
    ) -> RecoveryPlan:
        """
        Analyzes the project state and evidence on disk, then generates a structured RecoveryPlan.
        """
        pdir = Path(project_dir)
        if state is None:
            state = StateStore.load(pdir)
            if state is None:
                raise StateNotFoundError(pdir)

        current_state = LifecycleState(state.lifecycle_state)

        # 1. Handle terminal error/cancelled states
        if current_state in (LifecycleState.FAILED, LifecycleState.CANCELLED):
            last_valid = LifecycleState.DRAFT
            candidates = StateMachine.valid_rollback_candidates(current_state)
            for cand in candidates:
                if cls.is_state_valid(cand, state, pdir):
                    last_valid = cand
                    break
            target_state = last_valid
            target_idx = LIFECYCLE_ORDER.index(target_state)
            stages_to_replay = LIFECYCLE_ORDER[target_idx + 1 :]
            requires_manual = (current_state == LifecycleState.CANCELLED)
            reason = f"Project was in {current_state.value}. Rollback to last valid state {target_state.value}."
        else:
            # 2. Normal lifecycle progression: check if current_state is valid
            curr_idx = LIFECYCLE_ORDER.index(current_state) if current_state in LIFECYCLE_ORDER else len(LIFECYCLE_ORDER) - 1
            validation_res = RequiredEvidencePolicy.validate_required_evidence(state, pdir)

            if validation_res.is_valid:
                return RecoveryPlan(
                    project_id=state.project_id,
                    current_state=current_state,
                    last_valid_state=current_state,
                    target_state=current_state,
                    expected_revision=state.revision,
                    stages_to_replay=[],
                    invalidated_evidence_paths=[],
                    stale_disk_paths=[],
                    reason=f"State {current_state.value} is fully valid; no rollback required",
                    requires_manual_action=False,
                )

            # Evidence failure: walk backwards to find highest valid predecessor via StateMachine graph
            last_valid = LifecycleState.DRAFT
            candidates = StateMachine.valid_rollback_candidates(current_state)
            for cand in candidates:
                if cls.is_state_valid(cand, state, pdir):
                    last_valid = cand
                    break

            target_state = last_valid
            target_idx = LIFECYCLE_ORDER.index(target_state)
            stages_to_replay = LIFECYCLE_ORDER[target_idx + 1 : curr_idx + 1]
            requires_manual = False
            first_issue = validation_res.issues[0] if validation_res.issues else None
            issue_msg = first_issue.message if first_issue else "missing required evidence"
            reason = f"Evidence validation failed at {current_state.value}: {issue_msg}. Rolled back to {target_state.value}."

        # Compute invalidated evidence paths:
        # All evidence required exclusively downstream of target_state, or missing/mismatched on disk
        target_idx = LIFECYCLE_ORDER.index(target_state)
        valid_retained_paths: Set[str] = set()
        for s in LIFECYCLE_ORDER[: target_idx + 1]:
            for itm in RequiredEvidencePolicy.get_required_evidence(s):
                valid_retained_paths.add(itm.path)

        invalidated_paths: Set[str] = set()
        for rec in state.artifact_records:
            if rec.path in valid_retained_paths:
                file_p = pdir / rec.path
                if not file_p.exists():
                    invalidated_paths.add(rec.path)
            else:
                invalidated_paths.add(rec.path)

        # Compute stale disk paths that must be removed on rollback
        stale_disk_paths: List[str] = []
        if target_idx < LIFECYCLE_ORDER.index(LifecycleState.REVIEW_APPROVED):
            if (pdir / ".studio_approved").exists():
                stale_disk_paths.append(".studio_approved")
        if target_idx < LIFECYCLE_ORDER.index(LifecycleState.PROBE_PASSED):
            if (pdir / ".studio_unlocked").exists():
                stale_disk_paths.append(".studio_unlocked")

        return RecoveryPlan(
            project_id=state.project_id,
            current_state=current_state,
            last_valid_state=target_state,
            target_state=target_state,
            expected_revision=state.revision,
            stages_to_replay=stages_to_replay,
            invalidated_evidence_paths=sorted(list(invalidated_paths)),
            stale_disk_paths=stale_disk_paths,
            reason=reason,
            requires_manual_action=requires_manual,
        )


class RecoveryService:
    """
    Authoritative execution service for applying recovery plans.
    Guarantees atomic rollback with CAS, monotonic revision increment,
    and explicit invalidation of downstream evidence records.
    """

    @classmethod
    def apply_plan(
        cls,
        project_dir: Path | str,
        plan: RecoveryPlan,
        timeout: Optional[float] = 10.0,
    ) -> ProjectState:
        """
        Applies a RecoveryPlan to reconcile on-disk state.
        """
        pdir = Path(project_dir)

        def mutator(working_copy: ProjectState) -> None:
            from scripts.core.lifecycle_service import LifecycleService
            LifecycleService.apply_rollback_mutation(working_copy, plan.target_state, reason=plan.reason)

            # Explicitly mark invalidated evidence
            for rec in working_copy.artifact_records:
                if rec.path in plan.invalidated_evidence_paths:
                    rec.invalidate(
                        reason=f"Recovery rollback to {plan.target_state.value}: {plan.reason}",
                        plan_id=plan.plan_id,
                    )

            # Canonical approval invalidation (S07.5 Obs D)
            # If rolling back to a state prior to REVIEW_APPROVED, invalidate canonical approval_metadata
            target_idx = LIFECYCLE_ORDER.index(plan.target_state) if plan.target_state in LIFECYCLE_ORDER else -1
            review_approved_idx = LIFECYCLE_ORDER.index(LifecycleState.REVIEW_APPROVED)
            if target_idx < review_approved_idx:
                working_copy.approval_metadata = {
                    "status": "INVALIDATED",
                    "invalidated_reason": f"Rollback to {plan.target_state.value}: {plan.reason}",
                    "invalidated_at": datetime.now(timezone.utc).isoformat(),
                    "approved_by": None,
                }

            # Record recovery event in metadata
            rec_history = working_copy.run_metadata.setdefault("recovery_history", [])
            rec_history.append({
                "plan_id": plan.plan_id,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "from_state": plan.current_state.value if hasattr(plan.current_state, "value") else str(plan.current_state),
                "to_state": plan.target_state.value if hasattr(plan.target_state, "value") else str(plan.target_state),
                "reason": plan.reason,
                "invalidated_paths": list(plan.invalidated_evidence_paths),
                "stale_disk_paths_cleaned": list(plan.stale_disk_paths),
            })

        reconciled_state = StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=plan.expected_revision,
            mutator=mutator,
            timeout=timeout,
        )

        # Clean up stale disk markers
        for rel_path in plan.stale_disk_paths:
            stale_file = pdir / rel_path
            if stale_file.exists():
                try:
                    stale_file.unlink()
                except OSError:
                    pass

        return reconciled_state


class RecoveryEngine:
    """
    Pipeline entry point for evaluating resumability.
    """

    @staticmethod
    def evaluate(project_dir: Path | str) -> ResumeDecision:
        pdir = Path(project_dir)
        state = StateStore.load(pdir)
        
        if not state:
            return ResumeDecision(can_resume=False, next_state=LifecycleState.DRAFT, reason="No state found")

        current_state = LifecycleState(state.lifecycle_state)
        if current_state in (LifecycleState.FAILED, LifecycleState.CANCELLED):
            plan = RecoveryPlanner.create_plan(pdir, state=state)
            return ResumeDecision(
                can_resume=False,
                next_state=current_state,
                reason=f"Project is in {current_state.value} state and cannot be resumed directly",
                recommended_action="apply_recovery_plan",
                recovery_plan=plan,
            )

        # Authoritative verification via Required Evidence Matrix (S06 / REC-001)
        validation_result = RequiredEvidencePolicy.validate_required_evidence(state, pdir)

        if not validation_result.is_valid:
            first_issue = validation_result.issues[0] if validation_result.issues else None
            detail_msg = first_issue.message if first_issue else "missing required evidence"
            reason_msg = f"Required evidence validation failed for state {current_state.value}: {detail_msg}"

            plan = RecoveryPlanner.create_plan(pdir, state=state)
            return ResumeDecision(
                can_resume=False,
                next_state=None,
                reason=reason_msg,
                recommended_action="apply_recovery_plan",
                validation_result=validation_result,
                recovery_plan=plan,
            )

        # All required and recorded evidence successfully verified
        return ResumeDecision(
            can_resume=True,
            next_state=current_state,
            reason=f"Resuming from {current_state.value}",
            validation_result=validation_result,
        )
