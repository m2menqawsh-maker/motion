"""
Lifecycle Service — The Canonical Authority for Project Lifecycle Transitions.

Architecture Rule (S03):
LifecycleService.transition(...) is the SOLE permitted mechanism for advancing
or modifying the lifecycle_state of a project in production.
Direct mutation of state.lifecycle_state is strictly forbidden across all routers,
services, and pipeline scripts.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Optional, List, Tuple, Dict, Any

from scripts.core.state_model import (
    LifecycleState,
    ProjectState,
    StateMachine,
    StateTransitionError,
    ArtifactRecord,
    ValidationLevel,
)
from scripts.core.state_store import StateStore


class LifecycleError(Exception):
    """Base exception for all lifecycle domain errors."""
    pass


class InvalidLifecycleTransitionError(LifecycleError):
    """Raised when an illegal lifecycle transition is attempted (violates StateMachine)."""
    def __init__(self, current_state: Any, target_state: Any, reason: Optional[str] = None):
        self.current_state = current_state
        self.target_state = target_state
        self.reason = reason
        msg = f"Invalid lifecycle transition from {current_state} to {target_state}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class LifecyclePreconditionFailedError(LifecycleError):
    """Raised when a lifecycle transition lacks verified gate proof or evidence."""
    def __init__(self, target_state: Any, reason: str):
        self.target_state = target_state
        self.reason = reason
        super().__init__(f"Cannot transition to {target_state}: {reason}")


class LifecycleService:
    """
    Single Authority for Project Lifecycle Transitions.
    All transitions MUST pass through LifecycleService.transition().
    """

    @classmethod
    def apply_transition_mutation(cls, state: ProjectState, target_state: LifecycleState) -> None:
        """
        Low-level model state mutation.
        Strictly encapsulated within LifecycleService.
        """
        current_state = LifecycleState(state.lifecycle_state)
        target_state_enum = LifecycleState(target_state)

        if not StateMachine.validate_transition(current_state, target_state_enum):
            raise InvalidLifecycleTransitionError(
                current_state=current_state,
                target_state=target_state_enum,
                reason=f"Transition from {current_state.value} to {target_state_enum.value} is not permitted by StateMachine"
            )

        # Sole authorized production mutation of lifecycle_state
        state.lifecycle_state = target_state_enum

    @classmethod
    def apply_rollback_mutation(cls, state: ProjectState, target_state: LifecycleState, reason: Optional[str] = None) -> None:
        """
        Authorized rollback mutation for recovery and reconciliation (S07).
        Strictly encapsulated within LifecycleService.
        """
        target_state_enum = LifecycleState(target_state)
        state.lifecycle_state = target_state_enum

    @classmethod
    def _verify_preconditions(
        cls,
        project_dir: Path,
        current_state: LifecycleState,
        target_state: LifecycleState,
        artifacts: Optional[List[Tuple[str, ValidationLevel]]],
        evidence: Optional[Any],
    ) -> None:
        """
        Enforce S03 Rule: No proof -> no lifecycle advancement.
        Verifies that prerequisites, gate outputs, or artifacts exist before allowing state advancement.
        """
        # Transitions to FAILED or CANCELLED require no artifact evidence
        if target_state in (LifecycleState.FAILED, LifecycleState.CANCELLED):
            return

        # Idempotent no-op
        if current_state == target_state:
            return

        # State-specific prerequisite gates
        if target_state == LifecycleState.ASSETS_READY:
            manifest_file = project_dir / "02_asset_manifest.json"
            if not manifest_file.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Asset manifest (02_asset_manifest.json) is missing on disk."
                )

        elif target_state == LifecycleState.PLAN_READY:
            plan_file = project_dir / "master_plan.md"
            if not plan_file.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Master plan (master_plan.md) is missing on disk."
                )

        elif target_state == LifecycleState.BLUEPRINT_READY:
            bp_file = project_dir / "05_blueprint.json"
            if not bp_file.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Blueprint file (05_blueprint.json) is missing on disk."
                )
            try:
                content = json.loads(bp_file.read_text(encoding="utf-8"))
                if not isinstance(content, dict) or not content:
                    raise LifecyclePreconditionFailedError(
                        target_state.value,
                        "Blueprint file (05_blueprint.json) is empty or invalid JSON."
                    )
            except Exception as e:
                if isinstance(e, LifecyclePreconditionFailedError):
                    raise
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    f"Blueprint file (05_blueprint.json) could not be parsed: {e}"
                )

        elif target_state == LifecycleState.MATERIALIZED:
            media_map = project_dir / "media_map.json"
            if not media_map.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Media map (media_map.json) is missing on disk."
                )

        elif target_state == LifecycleState.PROBE_PASSED:
            probe_report = project_dir / "probe_qc_report.json"
            if not probe_report.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Probe QC report (probe_qc_report.json) is missing on disk."
                )

        elif target_state == LifecycleState.AWAITING_REVIEW:
            if current_state != LifecycleState.PROBE_PASSED:
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    f"Awaiting review requires prior PROBE_PASSED, current is {current_state.value}."
                )

        elif target_state == LifecycleState.REVIEW_APPROVED:
            studio_approved = project_dir / ".studio_approved"
            if not studio_approved.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Human review marker (.studio_approved) is missing on disk."
                )

        elif target_state == LifecycleState.RENDERED:
            video_file = project_dir / "out.mp4"
            if not video_file.exists():
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Rendered video artifact (out.mp4) is missing on disk."
                )

        elif target_state == LifecycleState.FINAL_QC_PASSED:
            if current_state != LifecycleState.RENDERED:
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    f"Final QC requires prior RENDERED state, current is {current_state.value}."
                )

        elif target_state == LifecycleState.COMPLETE:
            if current_state != LifecycleState.FINAL_QC_PASSED:
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    f"Project completion requires prior FINAL_QC_PASSED, current is {current_state.value}."
                )
            out_file = project_dir / "out.mp4"
            if not out_file.exists() or out_file.stat().st_size == 0:
                raise LifecyclePreconditionFailedError(
                    target_state.value,
                    "Project completion requires non-empty rendered video output (out.mp4) on disk."
                )

        # Check declared artifact existence
        if artifacts:
            for rel_path, _ in artifacts:
                artifact_file = project_dir / rel_path
                if not artifact_file.exists():
                    raise LifecyclePreconditionFailedError(
                        target_state.value,
                        f"Declared artifact '{rel_path}' is missing on disk."
                    )

    @classmethod
    def transition(
        cls,
        project_dir: Path | str,
        target_state: LifecycleState | str,
        artifacts: Optional[List[Tuple[str, ValidationLevel]]] = None,
        evidence: Optional[Any] = None,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        expected_revision: Optional[int] = None,
        timeout: Optional[float] = 10.0,
    ) -> ProjectState:
        """
        The single canonical entry point to transition a project lifecycle state.

        1. Handles initial state creation for DRAFT if missing.
        2. Binds expected revision (explicit or snapshot).
        3. Executes transactional atomic update via StateStore.atomic_update.
        4. Mutator enforces StateMachine legality, precondition checks, artifact records,
           metadata updates, and lifecycle mutation.
        5. Storage authority commits atomically with CAS check, revision+1, updated_at.
        6. Returns updated ProjectState.
        """
        proj_dir = Path(project_dir)
        target_state_enum = LifecycleState(target_state)
        state_file = proj_dir / StateStore.STATE_FILE

        if not state_file.exists():
            if target_state_enum == LifecycleState.DRAFT:
                project_id = proj_dir.name
                return StateStore.create(proj_dir, project_id, timeout=timeout)
            else:
                raise LifecycleError(
                    f"Cannot transition project at '{proj_dir}': No state file exists."
                )

        if expected_revision is None:
            current_snap = StateStore.load(proj_dir)
            if not current_snap:
                raise LifecycleError(f"Cannot transition project at '{proj_dir}': State file cannot be read.")
            expected_revision = current_snap.revision

        def mutator(working_copy: ProjectState) -> None:
            current_state = LifecycleState(working_copy.lifecycle_state)

            # 1. State machine legality check
            if not StateMachine.validate_transition(current_state, target_state_enum):
                raise InvalidLifecycleTransitionError(
                    current_state=current_state,
                    target_state=target_state_enum,
                    reason=f"Transition from {current_state.value} to {target_state_enum.value} is not permitted by StateMachine"
                )

            # 2. Gate evidence & precondition verification
            cls._verify_preconditions(proj_dir, current_state, target_state_enum, artifacts, evidence)

            # 3. Cumulative artifact records recording (S06: no destructive overwrite)
            if artifacts:
                new_records = []
                for item in artifacts:
                    if isinstance(item, tuple):
                        path, val_level = item
                        new_records.append(StateStore.create_artifact_record(
                            proj_dir,
                            path,
                            val_level,
                            stage=target_state_enum.value,
                            produced_at_revision=expected_revision + 1,
                        ))
                    elif isinstance(item, ArtifactRecord):
                        new_records.append(item)
                working_copy.record_multiple_evidences(new_records)
            elif artifacts is None:
                # Auto-record required evidence files produced for this stage that exist on disk
                from scripts.core.evidence_matrix import RequiredEvidencePolicy
                auto_records = RequiredEvidencePolicy.auto_record_stage_evidence(
                    working_copy,
                    proj_dir,
                    target_state_enum,
                    revision=expected_revision + 1,
                )
                if auto_records:
                    working_copy.record_multiple_evidences(auto_records)

            # 4. Record metadata (actor / reason / failure context)
            if actor:
                working_copy.run_metadata["last_actor"] = actor
            if reason:
                working_copy.run_metadata["transition_reason"] = reason
                if target_state_enum == LifecycleState.FAILED:
                    working_copy.structured_errors.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": reason,
                        "previous_state": current_state.value,
                    })

            # 5. Mutate lifecycle state (S03 Sole Authority)
            cls.apply_transition_mutation(working_copy, target_state_enum)

        return StateStore.atomic_update(
            project_dir=proj_dir,
            expected_revision=expected_revision,
            mutator=mutator,
            timeout=timeout,
        )
