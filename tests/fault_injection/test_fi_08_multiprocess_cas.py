"""
tests/fault_injection/test_fi_08_multiprocess_cas.py — Fault Injection Scenario FI-08.

Multi-Process Concurrent Writers & CAS Verification:
Spawns two distinct, concurrent OS Python processes via subprocess
attempting to perform atomic CAS updates on the exact same project record
starting from the exact same revision (revision = 1).

Expected Invariants:
1. Exactly ONE process succeeds (revision advances from 1 to 2, exit code 0).
2. The other process receives a deterministic StateConflictError (exit code 49 / CONFLICT).
3. Zero lost updates (no silent last-write-wins).
4. Monotonic revision sequence in the database (revision == 2).
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest

from scripts.core.database import (
    DatabaseEngine,
    TenantRepository,
    TenantStateRepository,
    set_database_engine,
)
from scripts.core.state_model import ProjectState, LifecycleState


WRITER_SCRIPT = """
import sys
import json
import time
from scripts.core.database import DatabaseEngine, TenantStateRepository, StateConflictError
from scripts.core.state_model import LifecycleState

db_url = sys.argv[1]
project_id = sys.argv[2]
workspace_id = sys.argv[3]
new_lifecycle = sys.argv[4]
expected_rev = int(sys.argv[5])

engine = DatabaseEngine(db_url=db_url)
state_repo = TenantStateRepository(engine)

state = state_repo.load_state(project_id)
if not state:
    sys.exit(44)

state.lifecycle_state = LifecycleState(new_lifecycle)

try:
    updated = state_repo.update_state_cas(
        project_id=project_id,
        workspace_id=workspace_id,
        expected_revision=expected_rev,
        new_state=state,
    )
    print(f"SUCCESS: revision={updated.revision}")
    sys.exit(0)
except StateConflictError as conflict:
    print(f"CONFLICT: expected={conflict.expected_revision}, actual={conflict.actual_revision}")
    sys.exit(49)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    sys.exit(50)
"""


def test_fi08_multiprocess_cas_race(tmp_path: Path):
    """Two concurrent OS processes racing to update state from the exact same revision 1."""
    db_file = tmp_path / "fi08_concurrent.db"
    db_url = f"sqlite:///{db_file}"
    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    repo = TenantRepository(engine)
    state_repo = TenantStateRepository(engine)

    u = repo.create_user("usr_cas", "cas@test.com")
    ws = repo.create_workspace("ws_cas", "Workspace CAS", created_by=u.id)
    prj = repo.create_project("prj_cas_race", ws.id, "Race Video", created_by=u.id)

    # Initial state: revision 1, DRAFT
    initial_state = state_repo.load_state(prj.id)
    assert initial_state.revision == 1

    # Launch two independent OS processes concurrently, BOTH passing expected_revision=1
    cmd1 = [sys.executable, "-c", WRITER_SCRIPT, db_url, prj.id, ws.id, LifecycleState.ASSETS_READY.value, "1"]
    cmd2 = [sys.executable, "-c", WRITER_SCRIPT, db_url, prj.id, ws.id, LifecycleState.PLAN_READY.value, "1"]

    proc1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    out1, err1 = proc1.communicate(timeout=10)
    out2, err2 = proc2.communicate(timeout=10)

    exit_codes = sorted([proc1.returncode, proc2.returncode])
    outputs = [out1.strip(), out2.strip()]

    # Invariant: exactly one process succeeds (0), and one gets conflict (49)
    assert exit_codes == [0, 49], f"Expected exit codes [0, 49], got {exit_codes}. Outputs: {outputs}. Errors: {[err1, err2]}"

    success_out = [o for o in outputs if "SUCCESS" in o]
    conflict_out = [o for o in outputs if "CONFLICT" in o]

    assert len(success_out) == 1, f"Expected 1 SUCCESS, got {success_out}"
    assert len(conflict_out) == 1, f"Expected 1 CONFLICT, got {conflict_out}"

    assert "revision=2" in success_out[0]
    assert "expected=1" in conflict_out[0]

    # Verify final state in database: revision MUST be strictly 2
    final_state = state_repo.load_state(prj.id)
    assert final_state.revision == 2
    assert final_state.lifecycle_state in (LifecycleState.ASSETS_READY, LifecycleState.PLAN_READY)
