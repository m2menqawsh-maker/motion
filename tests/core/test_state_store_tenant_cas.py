"""
tests/core/test_state_store_tenant_cas.py — Unit Tests for Tenant-Aware StateStore CAS (S24.5).
"""

import json
from pathlib import Path
import pytest

from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.state_store import StateStore, StateConflictError


@pytest.fixture
def clean_db(tmp_path: Path):
    db_file = tmp_path / "test_cas.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    tenant_repo = TenantRepository(engine)
    tenant_repo.create_user("usr_cas", "cas@example.com")
    tenant_repo.create_workspace("ws_cas", "CAS Workspace", created_by="usr_cas")
    tenant_repo.create_project("prj_db_cas", "ws_cas", "CAS Project", created_by="usr_cas")

    yield engine
    set_database_engine(None)


def test_state_store_db_cas(clean_db):
    # 1. Load by ID
    state = StateStore.load_by_id("prj_db_cas")
    assert state is not None
    assert state.revision == 1
    assert state.lifecycle_state == LifecycleState.DRAFT

    # 2. Atomic update by ID (rev 1 -> 2)
    def mutator(st: ProjectState):
        st.lifecycle_state = LifecycleState.ASSETS_READY

    updated = StateStore.atomic_update_by_id("prj_db_cas", "ws_cas", expected_revision=1, mutator=mutator)
    assert updated.revision == 2
    assert updated.lifecycle_state == LifecycleState.ASSETS_READY

    # 3. Stale update attempt (expecting rev 1 when actual is 2) -> StateConflictError (409)
    with pytest.raises(StateConflictError):
        StateStore.atomic_update_by_id("prj_db_cas", "ws_cas", expected_revision=1, mutator=mutator)

    # 4. Verify DB now holds rev 2
    reloaded = StateStore.load_by_id("prj_db_cas")
    assert reloaded.revision == 2
    assert reloaded.lifecycle_state == LifecycleState.ASSETS_READY


def test_state_store_disk_syncs_with_db(tmp_path: Path, clean_db):
    proj_dir = tmp_path / "prj_db_cas"
    proj_dir.mkdir()

    # Initial save to disk creates revision 1
    state = StateStore.load_by_id("prj_db_cas")
    StateStore.save(proj_dir, state, expected_revision=1)

    disk_state = StateStore.load(proj_dir)
    assert disk_state.revision == 1

    # Atomic update on disk increments revision to 2 and syncs with DB
    def mutator(st: ProjectState):
        st.lifecycle_state = LifecycleState.ASSETS_READY

    updated = StateStore.atomic_update(proj_dir, expected_revision=1, mutator=mutator)
    assert updated.revision == 2

    # Reload from DB directly
    db_state = StateStore.load_by_id("prj_db_cas")
    assert db_state.revision == 2
    assert db_state.lifecycle_state == LifecycleState.ASSETS_READY


def test_db_update_syncs_to_disk_cache(tmp_path: Path, clean_db, monkeypatch):
    """
    State Authority: Mutations via database (API/Worker) MUST automatically export/sync
    the read-only cache to .pipeline_state.json on disk so CLI tools never diverge.
    """
    proj_dir = tmp_path / "projects" / "ws_cas" / "prj_db_cas"
    proj_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    # Initial save to disk creates revision 1
    state = StateStore.load_by_id("prj_db_cas")
    StateStore.save(proj_dir, state, expected_revision=1)
    assert (proj_dir / StateStore.STATE_FILE).exists()

    # Mutation applied via database engine / repository (e.g. API mutation)
    def mutator(st: ProjectState):
        st.lifecycle_state = LifecycleState.PLAN_READY

    updated = StateStore.atomic_update_by_id(
        project_id="prj_db_cas",
        workspace_id="ws_cas",
        expected_revision=1,
        mutator=mutator,
    )
    assert updated.revision == 2

    # Verify on-disk cache was updated to rev 2 automatically!
    disk_content = json.loads((proj_dir / StateStore.STATE_FILE).read_text(encoding="utf-8"))
    assert disk_content["revision"] == 2
    assert disk_content["lifecycle_state"] == LifecycleState.PLAN_READY.value


def test_load_reconciles_from_authoritative_db_even_without_managed_env(tmp_path: Path, clean_db):
    """
    When disk state file has an older revision than DB, StateStore.load() must ALWAYS
    reconcile from the authoritative database, returning rev 2 and healing the disk file.
    """
    proj_dir = tmp_path / "prj_db_cas"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Initial save to disk creates revision 1
    state = StateStore.load_by_id("prj_db_cas")
    StateStore.save(proj_dir, state, expected_revision=1)

    # Advance DB directly to revision 2 without updating disk
    from scripts.core.database import TenantStateRepository
    repo = TenantStateRepository(clean_db)
    state2 = repo.load_state("prj_db_cas")
    state2.lifecycle_state = LifecycleState.ASSETS_READY
    repo.update_state_cas("prj_db_cas", "ws_cas", expected_revision=1, new_state=state2)

    # On disk, .pipeline_state.json is still rev 1
    disk_file = proj_dir / StateStore.STATE_FILE
    assert json.loads(disk_file.read_text(encoding="utf-8"))["revision"] == 1

    # StateStore.load(proj_dir) MUST reconcile from DB and return rev 2
    loaded = StateStore.load(proj_dir)
    assert loaded.revision == 2
    assert loaded.lifecycle_state == LifecycleState.ASSETS_READY

    # And heal the disk cache file
    assert json.loads(disk_file.read_text(encoding="utf-8"))["revision"] == 2


def test_atomic_update_fails_closed_on_db_cas_conflict(tmp_path: Path, clean_db):
    """
    If the authoritative database has advanced ahead of disk, StateStore.atomic_update()
    must detect the DB conflict, fail closed, rollback disk, and raise StateConflictError.
    """
    proj_dir = tmp_path / "prj_db_cas"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Initial save to disk creates revision 1
    state = StateStore.load_by_id("prj_db_cas")
    StateStore.save(proj_dir, state, expected_revision=1)

    # Advance DB directly to revision 3
    from scripts.core.database import TenantStateRepository
    repo = TenantStateRepository(clean_db)
    state2 = repo.load_state("prj_db_cas")
    state2.lifecycle_state = LifecycleState.ASSETS_READY
    repo.update_state_cas("prj_db_cas", "ws_cas", expected_revision=1, new_state=state2)
    state3 = repo.load_state("prj_db_cas")
    state3.lifecycle_state = LifecycleState.PLAN_READY
    repo.update_state_cas("prj_db_cas", "ws_cas", expected_revision=2, new_state=state3)

    # Calling atomic_update on disk expecting revision 1 must raise StateConflictError because DB is at rev 3
    def mutator(st: ProjectState):
        st.lifecycle_state = LifecycleState.FINAL_QC_PASSED

    with pytest.raises(StateConflictError) as exc_info:
        StateStore.atomic_update(proj_dir, expected_revision=1, mutator=mutator)
    assert exc_info.value.expected_revision == 1
    assert exc_info.value.actual_revision == 3

    # And disk was healed to the authoritative DB revision 3 (not corrupted or advanced to 2)
    disk_file = proj_dir / StateStore.STATE_FILE
    assert json.loads(disk_file.read_text(encoding="utf-8"))["revision"] == 3


