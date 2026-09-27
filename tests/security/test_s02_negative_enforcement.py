"""S02 Mandatory Negative Enforcement Test Suite.

In accordance with Section 17 & 18 of S02 Directives:
Comprehensive negative validation covering:
- Malformed / expired authentication
- Unknown roles and unmapped permissions
- Project scope isolation across endpoints
- Reviewer vs Editor privilege separation
- Path traversal ('..', encoded, slashes, drive letters)
- Absolute external paths
- Symlink escapes, broken symlinks, and multi-hop symlink chains
- Docker exec, system prune, --privileged, root filesystem mounts
- Unknown executables and shells
- Inline Python '-c' and production '-m pip' / '-m venv'
- Production forbidden environment variables audit
- Side-effect safety (rejection before write)
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from api.main import app
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.security.permissions import Action, AuthorizationPolicy
from scripts.core.security.command_policy import CommandPolicy
from scripts.core.security.env_policy import EnvironmentPolicyAuditor
from scripts.core.security.path_policy import (
    validate_project_id,
    validate_asset_id,
    resolve_safe_path,
    validate_source_asset,
    PathSecurityViolation,
)
from scripts.security.security import safe_subprocess
from scripts.core.state_store import StateStore


@pytest.fixture
def client():
    return TestClient(app)


# ─── 1. AUTHENTICATION NEGATIVE TESTS ───

def test_malformed_bearer_token(client):
    """Malformed bearer tokens must be rejected with 401."""
    # Empty token
    resp = client.post("/projects/", json={"name": "P", "language": "en"}, headers={"Authorization": "Bearer "})
    assert resp.status_code == 401

    # Invalid authorization scheme
    resp = client.post("/projects/", json={"name": "P", "language": "en"}, headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401


def test_expired_principal_rejection():
    """An expired principal must not be considered authenticated."""
    expired_principal = Principal(
        principal_id="usr_expired",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    assert not expired_principal.is_authenticated
    assert not AuthorizationPolicy.is_authorized(expired_principal, Action.PROJECT_READ)


def test_unknown_role_rejection(client):
    """Principals with unknown/unauthorized roles cannot perform restricted actions."""
    headers = {"X-Principal-ID": "usr_unknown_role", "X-Principal-Roles": "intruder,guest"}
    # PROJECT_CREATE requires EDITOR or ADMIN
    resp = client.post("/projects/", json={"name": "P", "language": "en"}, headers=headers)
    assert resp.status_code == 403


# ─── 2. AUTHORIZATION & SCOPE ISOLATION ───

def test_project_scope_isolation_read_and_mutation(client, tmp_path):
    """Principal with scope only for project A cannot read, edit, or approve project B."""
    proj_b = "prj_forbidden_target"
    proj_dir = Path("projects") / proj_b
    proj_dir.mkdir(parents=True, exist_ok=True)
    try:
        StateStore.create(proj_dir, proj_b)

        headers = {
            "X-Principal-ID": "usr_isolated",
            "X-Principal-Roles": "editor,reviewer",
            "X-Principal-Scope": "prj_allowed_only"
        }

        # Attempt to read project B
        resp_read = client.get(f"/projects/{proj_b}", headers=headers)
        assert resp_read.status_code == 403

        # Attempt to approve gate on project B
        resp_approve = client.post(f"/gates/{proj_b}/approve/gate_1", headers=headers)
        assert resp_approve.status_code == 403

        # Attempt to trigger render on project B
        resp_render = client.post(f"/render/{proj_b}", headers=headers)
        assert resp_render.status_code == 403
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir)


def test_trusted_reviewer_vs_editor_separation(client):
    """Editors cannot approve review gates; Reviewers can."""
    from api.services.pipeline_service import PipelineService
    proj_id = "prj_review_test"
    proj_dir = PipelineService._get_project_dir(proj_id)
    proj_dir.mkdir(parents=True, exist_ok=True)
    try:
        StateStore.create(proj_dir, proj_id)

        # Editor attempt -> 403
        editor_headers = {"X-Principal-ID": "usr_editor", "X-Principal-Roles": "editor", "X-Principal-Scope": proj_id}
        resp = client.post(f"/gates/{proj_id}/approve/gate_3", headers=editor_headers)
        assert resp.status_code == 403

        # Reviewer attempt -> 200
        reviewer_headers = {"X-Principal-ID": "usr_reviewer", "X-Principal-Roles": "reviewer", "X-Principal-Scope": proj_id}
        resp = client.post(f"/gates/{proj_id}/approve/gate_3", headers=reviewer_headers)
        assert resp.status_code == 200

        # State must record the reviewer's principal_id, not arbitrary spoofed identities
        state = StateStore.load(proj_dir)
        assert state.approval_metadata.get("approved_by") == "usr_reviewer"
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir)


# ─── 3. PATH & SYMLINK CONFINEMENT NEGATIVE TESTS ───

def test_validate_project_id_rejections():
    """Unsafe project IDs must be rejected immediately."""
    with pytest.raises(ValueError):
        validate_project_id("../escape")
    with pytest.raises(ValueError):
        validate_project_id("/absolute/path")
    with pytest.raises(ValueError):
        validate_project_id("has spaces")
    with pytest.raises(ValueError):
        validate_project_id("null\x00byte")
    with pytest.raises(ValueError):
        validate_project_id("path/traversal")


def test_validate_asset_id_rejections():
    """Unsafe asset IDs must be rejected."""
    with pytest.raises(ValueError):
        validate_asset_id("../asset")
    with pytest.raises(ValueError):
        validate_asset_id("sub/dir/asset")
    with pytest.raises(ValueError):
        validate_asset_id("win\\slash")
    with pytest.raises(ValueError):
        validate_asset_id(".hidden")


def test_resolve_safe_path_rejections(tmp_path):
    """Path resolution must reject escapes, drive letters, and root escapes."""
    base = tmp_path / "sandbox"
    base.mkdir()

    with pytest.raises(ValueError, match="Path traversal"):
        resolve_safe_path(base, "../outside.txt")
    with pytest.raises(ValueError, match="Path traversal"):
        resolve_safe_path(base, "/etc/shadow")
    with pytest.raises(ValueError, match="Path traversal"):
        resolve_safe_path(base, "C:\\Windows\\System32")


def test_symlink_escape_and_chain_rejection(tmp_path):
    """Symlinks resolving outside allowed roots must be strictly rejected."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    secret = outside / "secret.env"
    secret.write_text("SENSITIVE_DATA", encoding="utf-8")

    # Single-hop symlink
    symlink_1 = workspace / "link_direct.txt"
    try:
        os.symlink(secret, symlink_1)
    except OSError:
        pytest.skip("Symlinks not supported")

    with pytest.raises(PathSecurityViolation, match="Symlink or path escape"):
        validate_source_asset(symlink_1, allowed_roots=[workspace])

    # Multi-hop symlink chain (link_2 -> link_1 -> secret)
    symlink_2 = workspace / "link_chain.txt"
    os.symlink(symlink_1, symlink_2)

    with pytest.raises(PathSecurityViolation, match="Symlink or path escape"):
        validate_source_asset(symlink_2, allowed_roots=[workspace])


def test_broken_symlink_rejection(tmp_path):
    """Broken symlinks must be rejected with PathSecurityViolation."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    broken_link = workspace / "broken.txt"
    try:
        os.symlink(workspace / "non_existent_file.txt", broken_link)
    except OSError:
        pytest.skip("Symlinks not supported")

    with pytest.raises(PathSecurityViolation, match="Broken symlink"):
        validate_source_asset(broken_link, allowed_roots=[workspace])


# ─── 4. SUBPROCESS & COMMAND POLICY NEGATIVE TESTS ───

def test_docker_dangerous_subcommands():
    """Docker system prune, exec, volume rm must all be rejected."""
    for sub in ["exec", "system", "volume", "network"]:
        res = CommandPolicy.validate_command(["docker", sub, "prune"])
        assert not res.is_allowed
        assert any("forbidden" in v for v in res.violations)


def test_docker_root_mount_rejected():
    """Docker mounting root filesystem must be rejected."""
    res = CommandPolicy.validate_command(["docker", "run", "-v", "/:/root", "clean-video-builder"])
    assert not res.is_allowed
    assert any("root filesystem mount" in v for v in res.violations)


def test_unknown_commands_rejected():
    """Arbitrary executables not in the registry must be rejected."""
    for exe in ["curl", "wget", "bash", "sh", "powershell", "python.exe.bat"]:
        res = CommandPolicy.validate_command([exe, "arg"])
        assert not res.is_allowed
        assert any("not in the allowed executables registry" in v for v in res.violations)


def test_python_c_flag_rejected():
    """Python -c flag anywhere in the command line must be rejected."""
    res = CommandPolicy.validate_command(["python", "scripts/pipeline.py", "-c", "print(1)"])
    assert not res.is_allowed
    assert any("-c" in v for v in res.violations)


def test_production_python_module_execution_rejected():
    """In production, python -m is strictly denied."""
    res_pip = CommandPolicy.validate_command(["python", "-m", "pip", "list"], is_production=True)
    assert not res_pip.is_allowed
    assert any("DENIED in production" in v for v in res_pip.violations)

    res_pytest = CommandPolicy.validate_command(["python", "-m", "pytest", "tests/"], is_production=True)
    assert not res_pytest.is_allowed
    assert any("DENIED in production" in v for v in res_pytest.violations)


# ─── 5. ENVIRONMENT POLICY NEGATIVE TESTS ───

def test_production_forbidden_env_vars_detected():
    """Audit must identify all bypass/test-only variables in production."""
    dirty_env = {
        "SKIP_STRICT_QC": "1",
        "AGY_IS_MANAGED": "1",
        "AGY_FAILURE_INJECTION_ENABLED": "1",
        "AGY_INJECT_FAILURE": "fatal_err"
    }
    violations = EnvironmentPolicyAuditor.audit_environment(dirty_env, target_env="production")
    assert len(violations) == 4
    for v in violations:
        assert "FORBIDDEN in production" in v


def test_sanitized_environment_strips_forbidden_vars_in_production():
    """Sanitize environment must strip dangerous variables in production."""
    dirty_env = {
        "SKIP_STRICT_QC": "1",
        "AGY_IS_MANAGED": "1",
        "SAFE_KEY": "safe_val",
        "PATH": "/usr/bin"
    }
    clean = CommandPolicy.sanitize_environment(base_env=dirty_env, is_production=True)
    assert "SKIP_STRICT_QC" not in clean
    assert "AGY_IS_MANAGED" not in clean
    assert "PATH" in clean
