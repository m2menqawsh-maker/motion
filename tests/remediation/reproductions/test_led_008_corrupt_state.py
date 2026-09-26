import pytest
from pathlib import Path
from scripts.core.state_store import StateStore

def test_led_008_corrupt_state_treated_as_missing(tmp_path):
    """
    Finding: LED-008
    Expected correct behavior: StateStore.load() must distinguish between a truly missing
    state file and a corrupted/truncated state file. A corrupted state file must NOT return None
    (which causes callers to wipe it to DRAFT); it must raise an exception or provide diagnostic failure.
    Actual behavior on current main: StateStore.load() uses 'except Exception: return None',
    silently treating corrupted/partial state as if the project was just created.
    """
    project_dir = tmp_path / "project_corrupt"
    project_dir.mkdir(parents=True)
    
    state_file = project_dir / ".pipeline_state.json"
    # Write corrupted JSON
    state_file.write_text('{"project_id": "test", "lifecycle_state": "FINAL_QC_PASSED", INVALID_JSON', encoding="utf-8")
    
    assert state_file.exists()
    
    # Attempt to load state
    corrupted_handled_as_error = False
    try:
        loaded = StateStore.load(project_dir)
        if loaded is None:
            # Returned None silently!
            corrupted_handled_as_error = False
        else:
            corrupted_handled_as_error = True
    except Exception:
        corrupted_handled_as_error = True
        
    # Assertion proving the defect:
    # Correct behavior: Must NOT silently return None on a corrupted file.
    # Current behavior on main: returns None silently.
    assert corrupted_handled_as_error, (
        "DEFECT PROVEN (LED-008): StateStore.load() silently returned None for a corrupted state file, "
        "allowing callers to treat it as non-existent and wipe existing project history to DRAFT."
    )
