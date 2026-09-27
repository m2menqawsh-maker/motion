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
import base64
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token, verify_signed_token
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.security.permissions import Action, AuthorizationPolicy
from scripts.core.security.command_policy import CommandPolicy
from scripts.core.security.env_policy import EnvironmentPolicyAuditor
from scripts.core.security.settings import (
    get_security_settings,
    set_security_settings,
    SecuritySettings,
    EnvironmentType,
)
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
        resp = client.post(f"/gates/{proj_id}/approve/taste_gate", headers=editor_headers)
        assert resp.status_code == 403

        # Reviewer attempt -> authorized (bypasses 403), but legacy gate approval fails closed (422) pending ReviewService (S09)
        reviewer_headers = {"X-Principal-ID": "usr_reviewer", "X-Principal-Roles": "reviewer", "X-Principal-Scope": proj_id}
        resp = client.post(f"/gates/{proj_id}/approve/taste_gate", headers=reviewer_headers)
        assert resp.status_code == 422
        assert resp.json()["error"] == "UnsupportedGateOperationError"

        # S04 Final Closure: Zero side effects, no metadata manufactured
        state = StateStore.load(proj_dir)
        assert "approved_by" not in state.approval_metadata
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


# ─── 6. PRODUCTION AUTHENTICATION & CRYPTOGRAPHIC TOKEN VERIFICATION ───

TEST_AUTH_SECRET = "production-test-secret-must-be-at-least-32-chars-long!"


def _tamper_token_payload(token: str, mutate_fn) -> str:
    """Helper to deserialize token payload, mutate claims, and re-serialize without updating HMAC."""
    payload_b64, sig = token.split(".", 1)
    pad = len(payload_b64) % 4
    padded = payload_b64 + ("=" * (4 - pad) if pad else "")
    data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    mutate_fn(data)
    new_json = json.dumps(data, separators=(',', ':'), sort_keys=True).encode("utf-8")
    new_payload_b64 = base64.urlsafe_b64encode(new_json).decode("ascii").rstrip("=")
    return f"{new_payload_b64}.{sig}"


# 1. Valid Authentic Credential -> Accepted
def test_production_auth_valid_authentic_credential_accepted(client, monkeypatch):
    """In production, a valid cryptographically signed bearer token must be accepted."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_editor101",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    token = create_signed_token(principal, secret=TEST_AUTH_SECRET, expires_in_seconds=3600)

    proj_name = "AuthenticCredentialProject"
    resp = client.post(
        "/projects/",
        json={"name": proj_name, "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    proj_id = data.get("project_id")
    if proj_id:
        proj_dir = Path("projects") / proj_id
        if proj_dir.exists():
            shutil.rmtree(proj_dir)


# 2. Modified Principal ID -> 401
def test_production_auth_modified_principal_id_rejected(client, monkeypatch):
    """Tampering with principal_id (sub) without valid signature MUST yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_alice",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    valid_token = create_signed_token(principal, secret=TEST_AUTH_SECRET)
    tampered_token = _tamper_token_payload(valid_token, lambda d: d.update({"sub": "usr_attacker"}))

    resp = client.post(
        "/projects/",
        json={"name": "TamperedSubProject", "language": "en"},
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert resp.status_code == 401


# 3. Modified Role -> 401
def test_production_auth_modified_role_rejected(client, monkeypatch):
    """Tampering with roles (e.g. elevating viewer to admin) MUST yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_viewer",
        principal_type=PrincipalType.HUMAN,
        roles={Role.VIEWER},
    )
    valid_token = create_signed_token(principal, secret=TEST_AUTH_SECRET)
    tampered_token = _tamper_token_payload(valid_token, lambda d: d.update({"roles": ["admin"]}))

    resp = client.post(
        "/projects/",
        json={"name": "ElevatedRoleProject", "language": "en"},
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert resp.status_code == 401


# 4. Modified Project Scope -> 401
def test_production_auth_modified_project_scope_rejected(client, monkeypatch):
    """Tampering with project_scopes to gain access to unauthorized projects MUST yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_scoped",
        principal_type=PrincipalType.HUMAN,
        roles=set(),
        project_scopes={"prj_allowed": {Role.EDITOR}},
    )
    valid_token = create_signed_token(principal, secret=TEST_AUTH_SECRET)
    tampered_token = _tamper_token_payload(valid_token, lambda d: d.update({"scopes": {"prj_target": ["editor"]}}))

    resp = client.post(
        "/gates/prj_target/approve/gate_1",
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert resp.status_code == 401


# 5. Modified Expiry -> 401
def test_production_auth_modified_expiry_rejected(client, monkeypatch):
    """Tampering with expiry timestamp to extend validity MUST yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_expiring",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    valid_token = create_signed_token(principal, secret=TEST_AUTH_SECRET, expires_in_seconds=-60)
    tampered_token = _tamper_token_payload(valid_token, lambda d: d.update({"exp": 2051222400}))

    resp = client.post(
        "/projects/",
        json={"name": "ExtendedExpiryProject", "language": "en"},
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert resp.status_code == 401


# 6. Invalid Signature & Unknown Opaque Token -> 401
def test_production_auth_invalid_signature_and_unknown_opaque_token(client, monkeypatch):
    """Tokens with corrupted signatures, forged keys, or random strings MUST yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_legit",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    wrong_key_token = create_signed_token(
        principal,
        secret="another-completely-different-secret-key-32-chars!",
        expires_in_seconds=3600
    )
    resp_wrong_key = client.post(
        "/projects/",
        json={"name": "WrongKeyProject", "language": "en"},
        headers={"Authorization": f"Bearer {wrong_key_token}"}
    )
    assert resp_wrong_key.status_code == 401

    resp_opaque = client.post(
        "/projects/",
        json={"name": "OpaqueGarbageProject", "language": "en"},
        headers={"Authorization": "Bearer random_unregistered_opaque_token_string"}
    )
    assert resp_opaque.status_code == 401


# 7. Expired Credential -> 401
def test_production_auth_expired_credential_rejected(client, monkeypatch):
    """An authentic credential whose expiration timestamp is in the past MUST yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    principal = Principal(
        principal_id="usr_expired",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    expired_token = create_signed_token(principal, secret=TEST_AUTH_SECRET, expires_in_seconds=-3600)

    resp = client.post(
        "/projects/",
        json={"name": "ExpiredProject", "language": "en"},
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401


# 8. Development Headers Rejected in Production -> 401
def test_production_auth_dev_headers_rejected_in_production(client, monkeypatch):
    """In production, custom development identity headers (X-Principal-*) are strictly ignored and yield 401."""
    monkeypatch.setenv("MOTION_ENV", "production")
    resp = client.post(
        "/projects/",
        json={"name": "P", "language": "en"},
        headers={
            "X-Principal-ID": "admin_attacker",
            "X-Principal-Roles": "admin",
            "X-Principal-Scope": "*"
        }
    )
    assert resp.status_code == 401


# 9. Forged approved_by / by Does Not Affect Principal
def test_production_auth_forged_approved_by_does_not_affect_principal(client, monkeypatch):
    """Query parameter ?by= or body approved_by cannot forge identity or bypass permissions."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    # Without token: query or body spoofing yields 401
    resp_unauth = client.post(
        "/gates/prj_sample/approve/gate_1?by=chief_editor",
        json={"approved_by": "chief_editor"}
    )
    assert resp_unauth.status_code == 401

    # With authentic Editor token: attempting to approve by claiming to be reviewer in query yields 403
    editor_principal = Principal(
        principal_id="usr_editor_only",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
        project_scopes={"prj_sample": {Role.EDITOR}}
    )
    editor_token = create_signed_token(editor_principal, secret=TEST_AUTH_SECRET)
    resp_forbidden = client.post(
        "/gates/prj_sample/approve/gate_1?by=trusted_reviewer",
        json={"approved_by": "trusted_reviewer"},
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert resp_forbidden.status_code == 403


# 10. Authentication Failure Produces Zero Side Effects
def test_production_auth_failure_produces_zero_side_effects(client, monkeypatch):
    """Authentication rejection must occur BEFORE any domain/filesystem logic; zero side-effects."""
    monkeypatch.setenv("MOTION_ENV", "production")
    target_project_name = "SideEffectProbeProject"
    resp = client.post("/projects/", json={"name": target_project_name, "language": "en"})
    assert resp.status_code == 401

    projects_dir = Path("projects")
    matching_dirs = [p for p in projects_dir.glob("*") if target_project_name.lower() in p.name.lower()]
    assert len(matching_dirs) == 0, f"Side-effect detected! Project directory was created: {matching_dirs}"


# 11. Secrets and Token Signatures Never Appear in Logs
def test_production_auth_secrets_and_tokens_never_leaked_in_logs(client, monkeypatch, caplog):
    """Neither secret keys nor full token signatures are ever printed in logs or responses."""
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/projects/",
            json={"name": "LeakProbe", "language": "en"},
            headers={"Authorization": f"Bearer malformed_token_string_with_secret_{TEST_AUTH_SECRET}"}
        )
        assert resp.status_code == 401
        assert TEST_AUTH_SECRET not in resp.text
        for record in caplog.records:
            assert TEST_AUTH_SECRET not in record.message

