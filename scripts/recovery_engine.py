import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from scripts.checkpoint_model import CheckpointRecord, CheckpointStage, ValidationLevel
from scripts.checkpoint_store import CheckpointStore

@dataclass
class ResumeDecision:
    can_resume: bool
    next_stage: Optional[CheckpointStage]
    reason: str
    recommended_action: Optional[str] = None
    
class RecoveryEngine:
    CURRENT_SCHEMA_VERSION = "1.0"
    CURRENT_PIPELINE_VERSION = "1.0"
    
    @staticmethod
    def evaluate(project_dir: Path) -> ResumeDecision:
        record = CheckpointStore.load(project_dir)
        
        if not record:
            return ResumeDecision(can_resume=False, next_stage=CheckpointStage.INITIALIZED, reason="No checkpoint found")
            
        if record.checkpoint_schema_version != RecoveryEngine.CURRENT_SCHEMA_VERSION:
            return ResumeDecision(
                can_resume=False,
                next_stage=CheckpointStage.INITIALIZED,
                reason=f"Unsupported schema version: {record.checkpoint_schema_version}",
                recommended_action="restart_from_scratch"
            )
            
        if record.pipeline_version != RecoveryEngine.CURRENT_PIPELINE_VERSION:
            return ResumeDecision(
                can_resume=False,
                next_stage=CheckpointStage.INITIALIZED,
                reason=f"Unsupported pipeline version: {record.pipeline_version}",
                recommended_action="restart_from_scratch"
            )
            
        # Validate Artifacts
        for artifact in record.artifact_references:
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
                current_hash = CheckpointStore._compute_sha256(full_path)
                if current_hash != artifact.sha256:
                    return ResumeDecision(
                        can_resume=False,
                        next_stage=None,
                        reason=f"Artifact hash mismatch for {artifact.path}",
                        recommended_action=f"restart_from_stage_creating_{artifact.path}"
                    )
                    
        # Determine next stage based on current checkpoint
        # The pipeline expects next_stage to match the PRE-CONDITION of the phase it should run.
        # Since the checkpoint records the last successful phase, it IS the pre-condition for the next phase.
        next_stage = record.checkpoint
        
        return ResumeDecision(
            can_resume=True,
            next_stage=next_stage,
            reason=f"Resuming from {record.checkpoint.value}"
        )
