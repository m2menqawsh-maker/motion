from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

class LifecycleState(str, Enum):
    DRAFT = "DRAFT"
    ASSETS_READY = "ASSETS_READY"
    PLAN_READY = "PLAN_READY"
    BLUEPRINT_READY = "BLUEPRINT_READY"
    MATERIALIZED = "MATERIALIZED"
    PROBE_PASSED = "PROBE_PASSED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    RENDERED = "RENDERED"
    FINAL_QC_PASSED = "FINAL_QC_PASSED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ValidationLevel(str, Enum):
    EXISTS = "EXISTS"       # Level 1 — Exists only (temporary/derived files)
    SIZE = "SIZE"           # Level 2 — Exists + size (large files like out.mp4)
    SHA256 = "SHA256"       # Level 3 — SHA256 (logic files like master_plan.md)

class ArtifactRecord(BaseModel):
    path: str
    validation: ValidationLevel
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None

class ProjectState(BaseModel):
    model_config = ConfigDict(extra='forbid', use_enum_values=True)
    
    project_id: str
    schema_version: int = 1
    revision: int = 1
    lifecycle_state: LifecycleState = LifecycleState.DRAFT
    
    run_metadata: Dict[str, Any] = Field(default_factory=dict)
    approval_metadata: Dict[str, Any] = Field(default_factory=dict)
    structured_errors: List[Dict[str, Any]] = Field(default_factory=list)
    artifact_records: List[ArtifactRecord] = Field(default_factory=list)
    
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

class StateMachine:
    # Forward happy path transitions
    VALID_FORWARD_TRANSITIONS = {
        LifecycleState.DRAFT: LifecycleState.ASSETS_READY,
        LifecycleState.ASSETS_READY: LifecycleState.PLAN_READY,
        LifecycleState.PLAN_READY: LifecycleState.BLUEPRINT_READY,
        LifecycleState.BLUEPRINT_READY: LifecycleState.MATERIALIZED,
        LifecycleState.MATERIALIZED: LifecycleState.PROBE_PASSED,
        LifecycleState.PROBE_PASSED: LifecycleState.AWAITING_REVIEW,
        LifecycleState.AWAITING_REVIEW: LifecycleState.REVIEW_APPROVED,
        LifecycleState.REVIEW_APPROVED: LifecycleState.RENDERED,
        LifecycleState.RENDERED: LifecycleState.FINAL_QC_PASSED,
        LifecycleState.FINAL_QC_PASSED: LifecycleState.COMPLETE,
    }

    @staticmethod
    def validate_transition(current_state: LifecycleState, target_state: LifecycleState) -> bool:
        """Validates if a transition is legal."""
        if current_state == target_state:
            return True  # Idempotent
            
        # Any state can transition to FAILED or CANCELLED (except terminal states)
        if target_state in (LifecycleState.FAILED, LifecycleState.CANCELLED):
            if current_state in (LifecycleState.COMPLETE, LifecycleState.CANCELLED):
                return False
            return True
            
        # Recovering from FAILED
        if current_state == LifecycleState.FAILED:
            # Can jump back to any previous state to retry
            return True
            
        # Normal forward progression
        return StateMachine.VALID_FORWARD_TRANSITIONS.get(current_state) == target_state

    @staticmethod
    def transition(state: ProjectState, target_state: LifecycleState) -> None:
        """Mutates the state to the target if valid, otherwise raises StateTransitionError."""
        current_state = LifecycleState(state.lifecycle_state)
        target_state_enum = LifecycleState(target_state)
        
        if not StateMachine.validate_transition(current_state, target_state_enum):
            raise StateTransitionError(f"Invalid transition from {current_state.value} to {target_state_enum.value}")
            
        state.lifecycle_state = target_state_enum
        state.revision += 1
        state.updated_at = datetime.now(timezone.utc).isoformat()

