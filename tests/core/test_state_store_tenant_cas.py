"""
tests/core/test_state_store_tenant_cas.py — Unit Tests for Tenant-Aware StateStore CAS (S24.5).
"""

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
