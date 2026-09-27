from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr
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

class EvidenceStatus(str, Enum):
    VALID = "VALID"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"

class ValidationLevel(str, Enum):
    EXISTS = "EXISTS"       # Level 1 — Exists only (temporary/derived files)
    SIZE = "SIZE"           # Level 2 — Exists + size (large files like out.mp4)
    SHA256 = "SHA256"       # Level 3 — SHA256 (logic files like master_plan.md)

class ArtifactRecord(BaseModel):
    model_config = ConfigDict(extra='ignore', use_enum_values=True)

    path: str
    validation: ValidationLevel
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None

    # S06 additions (backward-compatible with defaults)
    logical_name: Optional[str] = None
    stage: Optional[str] = None
    produced_at_revision: Optional[int] = None
    generation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # S07 additions (invalidation & rollback auditability)
    status: EvidenceStatus = EvidenceStatus.VALID
    invalidated_at: Optional[str] = None
    invalidated_reason: Optional[str] = None
    invalidated_by_recovery_plan: Optional[str] = None

    def invalidate(self, reason: str, plan_id: Optional[str] = None) -> None:
        """Explicitly invalidates this evidence record while preserving it in history."""
        self.status = EvidenceStatus.INVALIDATED
        self.invalidated_at = datetime.now(timezone.utc).isoformat()
        self.invalidated_reason = reason
        self.invalidated_by_recovery_plan = plan_id

class ProjectState(BaseModel):
    model_config = ConfigDict(extra='ignore', use_enum_values=True)
    _loaded_revision: Optional[int] = PrivateAttr(default=None)
    
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

    def record_evidence(self, record: ArtifactRecord) -> None:
        """
        Deterministically records an artifact evidence record.
        If a record with the same logical path already exists, it is updated in-place.
        Otherwise, it is appended to artifact_records.
        """
        for i, existing in enumerate(self.artifact_records):
            if existing.path == record.path:
                self.artifact_records[i] = record
                return
        self.artifact_records.append(record)

    def record_multiple_evidences(self, records: List[ArtifactRecord]) -> None:
        """Deterministically records multiple artifact evidence records."""
        for rec in records:
            self.record_evidence(rec)

    def get_artifact_record(self, path: str) -> Optional[ArtifactRecord]:
        """Retrieves the artifact record for the given path if present."""
        for rec in self.artifact_records:
            if rec.path == path:
                return rec
        return None

    def has_artifact(self, path: str) -> bool:
        """Returns True if an artifact record exists for the given path."""
        return self.get_artifact_record(path) is not None

    def get_valid_artifact_records(self) -> List[ArtifactRecord]:
        """Returns only records with status VALID."""
        return [r for r in self.artifact_records if getattr(r, "status", EvidenceStatus.VALID) == EvidenceStatus.VALID]

    def get_invalidated_artifact_records(self) -> List[ArtifactRecord]:
        """Returns only records with status INVALIDATED."""
        return [r for r in self.artifact_records if getattr(r, "status", EvidenceStatus.VALID) == EvidenceStatus.INVALIDATED]

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
        """Deprecated: Use LifecycleService.transition() instead. Delegates to LifecycleService."""
        from scripts.core.lifecycle_service import LifecycleService
        LifecycleService.apply_transition_mutation(state, target_state)

    @classmethod
    def get_topological_order(cls) -> List[LifecycleState]:
        """Returns the canonical topological progression of happy-path lifecycle states."""
        return [
            LifecycleState.DRAFT,
            LifecycleState.ASSETS_READY,
            LifecycleState.PLAN_READY,
            LifecycleState.BLUEPRINT_READY,
            LifecycleState.MATERIALIZED,
            LifecycleState.PROBE_PASSED,
            LifecycleState.AWAITING_REVIEW,
            LifecycleState.REVIEW_APPROVED,
            LifecycleState.RENDERED,
            LifecycleState.FINAL_QC_PASSED,
            LifecycleState.COMPLETE,
        ]

    @classmethod
    def get_predecessors(cls, state: LifecycleState) -> List[LifecycleState]:
        """Returns the immediate valid predecessor states for the given state in forward progression."""
        state_enum = LifecycleState(state)
        return [prev for prev, nxt in cls.VALID_FORWARD_TRANSITIONS.items() if nxt == state_enum]

    @classmethod
    def get_ancestors(cls, state: LifecycleState) -> List[LifecycleState]:
        """
        Returns all topological ancestors of the given state, ordered from closest predecessor
        down to DRAFT.
        """
        state_enum = LifecycleState(state)
        ancestors: List[LifecycleState] = []
        curr = state_enum
        while True:
            preds = cls.get_predecessors(curr)
            if not preds:
                break
            prev = preds[0]
            ancestors.append(prev)
            curr = prev
        return ancestors

    @classmethod
    def valid_rollback_candidates(cls, state: LifecycleState) -> List[LifecycleState]:
        """
        Returns ordered candidate states for rollback/recovery, starting from closest predecessor down to DRAFT.
        If state is FAILED or CANCELLED, returns all topological states in reverse order.
        """
        state_enum = LifecycleState(state)
        if state_enum in (LifecycleState.FAILED, LifecycleState.CANCELLED):
            return list(reversed(cls.get_topological_order()))
        return cls.get_ancestors(state_enum)

    @classmethod
    def path_between(cls, start_state: LifecycleState, end_state: LifecycleState) -> List[LifecycleState]:
        """
        Returns the linear forward path between start_state (exclusive) and end_state (inclusive).
        """
        start_enum = LifecycleState(start_state)
        end_enum = LifecycleState(end_state)
        topo = cls.get_topological_order()
        if start_enum not in topo or end_enum not in topo:
            return []
        start_idx = topo.index(start_enum)
        end_idx = topo.index(end_enum)
        if start_idx >= end_idx:
            return []
        return topo[start_idx + 1 : end_idx + 1]

