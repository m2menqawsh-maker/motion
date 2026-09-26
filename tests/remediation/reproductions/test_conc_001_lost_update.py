import pytest
from pathlib import Path
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, LifecycleState

def test_conc_001_lost_update_and_stale_write(tmp_path):
    """
    Finding: CONC-001
    Expected correct behavior: StateStore must support Compare-And-Swap (CAS) or optimistic locking.
    If Writer A and Writer B both read revision 1, Writer A writes revision 2,
    then Writer B attempting to write based on stale revision 1 MUST be rejected with a StateConflict error.
    Actual behavior on current main: Writer B unconditionally overwrites the state file,
    erasing Writer A's changes completely.
    """
    project_dir = tmp_path / "project_conc"
    project_dir.mkdir(parents=True)
    
    # 1. Initial State: Revision 1, Assets ready
    initial_state = ProjectState(
        project_id="test_conc",
        revision=1,
        lifecycle_state=LifecycleState.ASSETS_READY
    )
    StateStore.save(project_dir, initial_state)
    
    # 2. Writer A and Writer B read the same initial state (Revision 1)
    writer_a_state = StateStore.load(project_dir)
    writer_b_state = StateStore.load(project_dir)
    assert writer_a_state.revision == 1
    assert writer_b_state.revision == 1
    
    # 3. Writer A advances state to PLAN_READY and increments revision to 2
    writer_a_state.lifecycle_state = LifecycleState.PLAN_READY
    writer_a_state.revision = 2
    writer_a_state.run_metadata["writer"] = "Writer_A"
    StateStore.save(project_dir, writer_a_state)
    
    # 4. Writer B (holding stale state with revision 1) now updates something else and saves
    writer_b_state.revision = 2  # increments its stale copy from 1 to 2
    writer_b_state.run_metadata["writer"] = "Writer_B_Stale"
    
    # In a correct CAS implementation, this save would raise an exception (e.g. StateConflictError).
    # On main, it silently overwrites!
    conflict_detected = False
    try:
        StateStore.save(project_dir, writer_b_state)
    except Exception:
        conflict_detected = True
        
    current_state = StateStore.load(project_dir)
    
    # Assertion proving the defect:
    # Correct behavior: conflict_detected must be True, and Writer A's state must not be lost.
    # Current behavior on main: conflict_detected is False, Writer A's state was completely overwritten!
    assert conflict_detected, (
        f"DEFECT PROVEN (CONC-001): StateStore allowed stale write without conflict! "
        f"Writer A was overwritten by Writer B: run_metadata={current_state.run_metadata}, "
        f"lifecycle={current_state.lifecycle_state}"
    )
