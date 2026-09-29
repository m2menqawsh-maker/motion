"""
tests/core/test_tenant_database.py — Unit Tests for Multi-Tenant Database Engine (S24.5).
"""

from pathlib import Path
import pytest

from scripts.core.database import (
    DatabaseEngine,
    TenantRepository,
    TenantStateRepository,
    UsageRepository,
    TenantNotFoundError,
    TenantSecurityError,
    StateConflictError,
)
from scripts.core.tenant_model import UserStatus, UsageEventType
from scripts.core.security.principal import Role
from scripts.core.state_model import ProjectState, LifecycleState


@pytest.fixture
def db_engine(tmp_path: Path) -> DatabaseEngine:
    db_file = tmp_path / "test_tenant.db"
    return DatabaseEngine(db_url=f"sqlite:///{db_file}")


def test_user_and_workspace_lifecycle(db_engine: DatabaseEngine):
    repo = TenantRepository(db_engine)

    # 1. Create user
    user = repo.create_user("usr_alice", "alice@example.com")
    assert user.id == "usr_alice"
    assert user.email == "alice@example.com"
    assert user.status == UserStatus.ACTIVE

    fetched_user = repo.get_user("usr_alice")
    assert fetched_user is not None
    assert fetched_user.email == "alice@example.com"

    # 2. Create workspace
    ws = repo.create_workspace("ws_acme", "Acme Corporation", created_by="usr_alice")
    assert ws.id == "ws_acme"
    assert ws.name == "Acme Corporation"

    # Creator must automatically be ADMIN
    membership = repo.get_membership("ws_acme", "usr_alice")
    assert membership is not None
    assert membership.role == Role.ADMIN

    # 3. Add second member with REVIEWER role
    repo.create_user("usr_bob", "bob@example.com")
    member_bob = repo.add_member("ws_acme", "usr_bob", Role.REVIEWER)
    assert member_bob.role == Role.REVIEWER

    # Check workspaces for bob
    workspaces = repo.list_user_workspaces("usr_bob")
    assert len(workspaces) == 1
    assert workspaces[0][0].id == "ws_acme"
    assert workspaces[0][1] == Role.REVIEWER


def test_project_mandatory_workspace_invariants(db_engine: DatabaseEngine):
    repo = TenantRepository(db_engine)
    repo.create_user("usr_alice", "alice@example.com")
    repo.create_workspace("ws_acme", "Acme Corp", created_by="usr_alice")

    # Invariant: Empty or null workspace_id is strictly rejected
    with pytest.raises(ValueError, match="workspace_id cannot be null or empty"):
        repo.create_project("prj_invalid", "", "Test Proj", created_by="usr_alice")

    # Invariant: Non-existent workspace is rejected
    with pytest.raises(TenantNotFoundError):
        repo.create_project("prj_invalid", "ws_nonexistent", "Test Proj", created_by="usr_alice")

    # Valid project creation
    proj = repo.create_project("prj_valid", "ws_acme", "Marketing Video", created_by="usr_alice")
    assert proj.id == "prj_valid"
    assert proj.workspace_id == "ws_acme"

    # State record initialized automatically at revision 1
    state_repo = TenantStateRepository(db_engine)
    state = state_repo.load_state("prj_valid")
    assert state is not None
    assert state.revision == 1
    assert state.lifecycle_state == LifecycleState.DRAFT


def test_tenant_state_cas_concurrency(db_engine: DatabaseEngine):
    repo = TenantRepository(db_engine)
    state_repo = TenantStateRepository(db_engine)

    repo.create_user("usr_alice", "alice@example.com")
    repo.create_workspace("ws_acme", "Acme Corp", created_by="usr_alice")
    repo.create_project("prj_cas", "ws_acme", "CAS Video", created_by="usr_alice")

    state = state_repo.load_state("prj_cas")
    assert state.revision == 1

    # Writer 1 updates from rev 1 -> 2
    state.lifecycle_state = LifecycleState.ASSETS_READY
    updated = state_repo.update_state_cas("prj_cas", "ws_acme", expected_revision=1, new_state=state)
    assert updated.revision == 2

    # Writer 2 attempts stale update from rev 1 -> MUST FAIL with StateConflictError (409)
    stale_state = state.model_copy()
    stale_state.lifecycle_state = LifecycleState.PLAN_READY
    with pytest.raises(StateConflictError, match="State conflict"):
        state_repo.update_state_cas("prj_cas", "ws_acme", expected_revision=1, new_state=stale_state)

    # Cross-tenant mutation attempt -> MUST FAIL with TenantSecurityError
    with pytest.raises(TenantSecurityError, match="Cross-tenant mutation rejected"):
        state_repo.update_state_cas("prj_cas", "ws_other_tenant", expected_revision=2, new_state=stale_state)


def test_usage_accounting(db_engine: DatabaseEngine):
    repo = TenantRepository(db_engine)
    usage_repo = UsageRepository(db_engine)

    repo.create_user("usr_alice", "alice@example.com")
    repo.create_workspace("ws_acme", "Acme Corp", created_by="usr_alice")

    usage_repo.record_usage("ws_acme", UsageEventType.RENDER_SECONDS, 12.5, project_id="prj_1", user_id="usr_alice")
    usage_repo.record_usage("ws_acme", UsageEventType.RENDER_SECONDS, 7.5, project_id="prj_2", user_id="usr_alice")
    usage_repo.record_usage("ws_acme", UsageEventType.STORAGE_BYTES, 1048576, project_id="prj_1")

    totals = usage_repo.get_workspace_usage("ws_acme")
    assert totals[UsageEventType.RENDER_SECONDS.value] == 20.0
    assert totals[UsageEventType.STORAGE_BYTES.value] == 1048576.0
