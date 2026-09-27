import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from scripts.core.state_model import LifecycleState, ValidationLevel, ProjectState
from scripts.core.state_store import StateStore
from scripts.core.evidence_matrix import RequiredEvidencePolicy, EvidenceValidationResult

@dataclass
class ResumeDecision:
    can_resume: bool
    next_state: Optional[LifecycleState]
    reason: str
    recommended_action: Optional[str] = None
    validation_result: Optional[EvidenceValidationResult] = None

class RecoveryEngine:
    @staticmethod
    def evaluate(project_dir: Path) -> ResumeDecision:
        pdir = Path(project_dir)
        state = StateStore.load(pdir)
        
        if not state:
            return ResumeDecision(can_resume=False, next_state=LifecycleState.DRAFT, reason="No state found")

        # Terminal error or cancelled states cannot resume automatically
        current_state = LifecycleState(state.lifecycle_state)
        if current_state in (LifecycleState.FAILED, LifecycleState.CANCELLED):
            return ResumeDecision(
                can_resume=False,
                next_state=current_state,
                reason=f"Project is in {current_state.value} state and cannot be resumed directly",
                recommended_action="manual_intervention_or_rollback",
            )

        # Authoritative verification via Required Evidence Matrix (S06 / REC-001)
        validation_result = RequiredEvidencePolicy.validate_required_evidence(state, pdir)

        if not validation_result.is_valid:
            first_issue = validation_result.issues[0] if validation_result.issues else None
            detail_msg = first_issue.message if first_issue else "missing required evidence"
            reason_msg = f"Required evidence validation failed for state {current_state.value}: {detail_msg}"

            return ResumeDecision(
                can_resume=False,
                next_state=None,
                reason=reason_msg,
                recommended_action=validation_result.recommended_action,
                validation_result=validation_result,
            )

        # All required and recorded evidence successfully verified
        return ResumeDecision(
            can_resume=True,
            next_state=current_state,
            reason=f"Resuming from {current_state.value}",
            validation_result=validation_result,
        )
