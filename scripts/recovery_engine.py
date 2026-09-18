import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from scripts.state_model import LifecycleState, ValidationLevel, ProjectState
from scripts.state_store import StateStore

@dataclass
class ResumeDecision:
    can_resume: bool
    next_state: Optional[LifecycleState]
    reason: str
    recommended_action: Optional[str] = None
    
class RecoveryEngine:
    @staticmethod
    def evaluate(project_dir: Path) -> ResumeDecision:
        state = StateStore.load(project_dir)
        
        if not state:
            return ResumeDecision(can_resume=False, next_state=LifecycleState.DRAFT, reason="No state found")
            
        # Validate Artifacts
        for artifact in state.artifact_records:
            full_path = project_dir / artifact.path
            
            if not full_path.exists():
                return ResumeDecision(
                    can_resume=False,
                    next_state=None,
                    reason=f"Artifact missing: {artifact.path}",
                    recommended_action=f"restart_from_stage_creating_{artifact.path}"
                )
                
            if artifact.validation in (ValidationLevel.SIZE, ValidationLevel.SHA256):
                current_size = full_path.stat().st_size
                if current_size != artifact.size_bytes:
                    return ResumeDecision(
                        can_resume=False,
                        next_state=None,
                        reason=f"Artifact size mismatch for {artifact.path}",
                        recommended_action=f"restart_from_stage_creating_{artifact.path}"
                    )
                    
            if artifact.validation == ValidationLevel.SHA256:
                current_hash = StateStore._compute_sha256(full_path)
                if current_hash != artifact.sha256:
                    return ResumeDecision(
                        can_resume=False,
                        next_state=None,
                        reason=f"Artifact hash mismatch for {artifact.path}",
                        recommended_action=f"restart_from_stage_creating_{artifact.path}"
                    )
                    
        # Determine next state based on current
        next_state = state.lifecycle_state
        
        return ResumeDecision(
            can_resume=True,
            next_state=next_state,
            reason=f"Resuming from {state.lifecycle_state}"
        )
