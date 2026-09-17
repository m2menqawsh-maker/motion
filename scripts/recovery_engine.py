import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from scripts.state_model import CheckpointStage, ValidationLevel, ProjectState
from scripts.state_store import StateStore

@dataclass
class ResumeDecision:
    can_resume: bool
    next_stage: Optional[CheckpointStage]
    reason: str
    recommended_action: Optional[str] = None
    
class RecoveryEngine:
    @staticmethod
    def evaluate(project_dir: Path) -> ResumeDecision:
        state = StateStore.load(project_dir)
        
        if not state:
            return ResumeDecision(can_resume=False, next_stage=CheckpointStage.INITIALIZED, reason="No state found")
            
        # Validate Artifacts
        for artifact in state.artifact_references:
            full_path = project_dir / artifact.path
            
            if not full_path.exists():
                return ResumeDecision(
                    can_resume=False,
                    next_stage=None,
                    reason=f"Artifact missing: {artifact.path}",
                    recommended_action=f"restart_from_stage_creating_{artifact.path}"
                )
                
            if artifact.validation in (ValidationLevel.SIZE, ValidationLevel.SHA256):
                current_size = full_path.stat().st_size
                if current_size != artifact.size_bytes:
                    return ResumeDecision(
                        can_resume=False,
                        next_stage=None,
                        reason=f"Artifact size mismatch for {artifact.path}",
                        recommended_action=f"restart_from_stage_creating_{artifact.path}"
                    )
                    
            if artifact.validation == ValidationLevel.SHA256:
                current_hash = StateStore._compute_sha256(full_path)
                if current_hash != artifact.sha256:
                    return ResumeDecision(
                        can_resume=False,
                        next_stage=None,
                        reason=f"Artifact hash mismatch for {artifact.path}",
                        recommended_action=f"restart_from_stage_creating_{artifact.path}"
                    )
                    
        # Determine next stage based on current checkpoint
        next_stage = state.checkpoint
        
        return ResumeDecision(
            can_resume=True,
            next_stage=next_stage,
            reason=f"Resuming from {state.checkpoint}"
        )
