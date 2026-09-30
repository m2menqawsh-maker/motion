import pytest
from pathlib import Path
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, LifecycleState
from scripts.core.recovery_engine import RecoveryEngine

def test_rec_001_recovery_trusts_empty_evidence(tmp_path):
    """
    Finding: REC-001
    Owner Package: S06 (Recovery Engine & Evidence Verification)
    Expected correct behavior: RecoveryEngine.evaluate() must enforce a required evidence
    matrix per lifecycle state. For instance, COMPLETE state MUST require 'out.mp4' on disk.
    If evidence is missing, it must return can_resume=False.
    Actual behavior on current main: RecoveryEngine loops over state.artifact_records.
    When artifact_records is empty ([]), it performs 0 checks and returns can_resume=True,
    blindly trusting a bogus COMPLETE state without any media or video on disk!
    """
    project_dir = tmp_path / "project_rec_001"
    project_dir.mkdir(parents=True)
    
    # State claims project is COMPLETE, but artifact_records is empty []
    state = ProjectState(
        project_id="test_rec_001",
        lifecycle_state=LifecycleState.COMPLETE,
        artifact_records=[]
    )
    StateStore.save(project_dir, state)
    
    # Crucially, NO out.mp4 or other artifacts exist on disk
    assert not (project_dir / "out.mp4").exists()
    
    decision = RecoveryEngine.evaluate(project_dir)
    
    # Assertion proving the defect:
    # Correct behavior: can_resume MUST be False because required video artifact is missing!
    # Current behavior on main: decision.can_resume is True!
    assert not decision.can_resume, (
        f"DEFECT PROVEN (REC-001): RecoveryEngine evaluated can_resume=True for "
        f"COMPLETE state even though artifact_records is empty and out.mp4 is missing! "
        f"Reason given: {decision.reason}"
    )
