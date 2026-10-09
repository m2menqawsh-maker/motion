import os
import pytest
import shutil
import asyncio
from pathlib import Path

from typing import Optional, Set, Dict, Union, Iterable
from scripts.core.security.principal import Principal, PrincipalType, Role
from api.core.auth import create_signed_token

TEST_PYTEST_AUTH_SECRET = "test-signing-secret-for-pytest-harness-32-chars!"


def make_test_auth_headers(
    principal_id: str = "usr_test_viewer",
    roles: Optional[Iterable[Union[Role, str]]] = None,
    project_scopes: Optional[Dict[str, Iterable[Union[Role, str]]]] = None,
    secret: Optional[str] = None,
    principal_type: PrincipalType = PrincipalType.HUMAN,
) -> Dict[str, str]:
    """Helper to generate authentic signed Authorization headers for test suites.

    Defaults to least-privilege:
    - Default identity: 'usr_test_viewer'
    - Default roles: {Role.VIEWER}
    - Default project_scopes: {} (no global wildcard admin)

    Test callers requiring elevated roles (e.g. Role.ADMIN, Role.OPERATOR, Role.EDITOR)
    or project scopes MUST declare them explicitly.
    """
    if roles is None:
        roles_set: Set[Role] = {Role.VIEWER}
    else:
        roles_set = {
            r if isinstance(r, Role) else Role(str(r).lower().strip())
            for r in roles
        }

    if project_scopes is None:
        project_scopes_dict: Dict[str, Set[Role]] = {}
    else:
        project_scopes_dict = {
            p_id: {
                r if isinstance(r, Role) else Role(str(r).lower().strip())
                for r in r_list
            }
            for p_id, r_list in project_scopes.items()
        }

    if secret is None:
        secret = os.environ.get("AUTH_SECRET_KEY", TEST_PYTEST_AUTH_SECRET)

    principal = Principal(
        principal_id=principal_id,
        principal_type=principal_type,
        roles=roles_set,
        project_scopes=project_scopes_dict,
    )
    token = create_signed_token(principal, secret=secret)
    return {"Authorization": f"Bearer {token}"}



@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ['TESTING'] = '1'
    os.environ.setdefault('AUTH_SECRET_KEY', TEST_PYTEST_AUTH_SECRET)
    try:
        from scripts.core.database import get_database_engine, TenantRepository, Role
        repo = TenantRepository(get_database_engine())
        for uid, role in (
            ("test_admin", Role.ADMIN),
            ("usr_admin_legit", Role.ADMIN),
            ("gui_client_user", Role.ADMIN),
            ("usr_test_admin", Role.ADMIN),
            ("editor_user", Role.EDITOR),
            ("rev_user", Role.REVIEWER),
            ("reviewer_alice", Role.REVIEWER),
            ("viewer_bob", Role.VIEWER),
        ):
            if not repo.get_user(uid):
                repo.create_user(uid, f"{uid}@motion.local")
        if not repo.get_workspace("ws_default"):
            repo.create_workspace("ws_default", "Default Workspace", created_by="test_admin")
        for uid, role in (
            ("test_admin", Role.ADMIN),
            ("usr_admin_legit", Role.ADMIN),
            ("gui_client_user", Role.ADMIN),
            ("usr_test_admin", Role.ADMIN),
            ("editor_user", Role.EDITOR),
            ("rev_user", Role.REVIEWER),
            ("reviewer_alice", Role.REVIEWER),
            ("viewer_bob", Role.VIEWER),
        ):
            if not repo.get_membership("ws_default", uid):
                repo.add_member("ws_default", uid, role)
    except Exception:
        pass
    yield
    os.environ.pop('TESTING', None)
    try:
        from scripts.core.template_contract import invalidate_template_contract_cache
        invalidate_template_contract_cache()
    except Exception:
        pass

@pytest.fixture(autouse=True)
def setup_tmpdir(monkeypatch, tmp_path):
    """Patch the current working directory or paths to avoid touching real projects"""
    from api.services.pipeline_service import PipelineService
    
    def mock_get_project_dir(cls, project_id: str) -> Path:
        p = tmp_path / "projects" / project_id
        p.mkdir(parents=True, exist_ok=True)
        return p
        
    monkeypatch.setattr(PipelineService, "_get_project_dir", classmethod(mock_get_project_dir))

@pytest.fixture
def test_project(tmp_path):
    """Test Project"""
    project_id = "test-golden-001"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    (project_dir / "master_plan.md").write_text("# Test Plan", encoding="utf-8")
    (project_dir / "blueprint.json").write_text('{"scenes": []}', encoding="utf-8")
    
    yield project_id
    
    if project_dir.exists():
        shutil.rmtree(project_dir)

@pytest.fixture
def mock_subprocess(monkeypatch):
    async def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '{"master_plan_hash": "abc", "blueprint_hash": "def"}'
            stderr = ""
        return Result()
        
    def fake_sync_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '__PIPELINE_STATE__{"master_plan_hash": "abc", "blueprint_hash": "def"}__PIPELINE_STATE__'
            stderr = ""
        return Result()
    
    import api.services.pipeline_service as ps
    monkeypatch.setattr(ps, "safe_subprocess", fake_sync_run)
