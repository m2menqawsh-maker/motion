#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/security/test_tenant_path_isolation.py — Security tests for tenant filesystem and state isolation.
Verifies path traversal blocking, symlink escape detection, cross-tenant isolation enforcement, and legacy fallback.
"""

import json
import os
from pathlib import Path
import pytest

from scripts.core.security.path_policy import (
    PathTraversalError,
    PathSecurityViolation,
    TenantSecurityError,
    check_confinement_and_symlink,
    get_canonical_project_dir,
    resolve_project_dir,
    validate_workspace_id,
)


@pytest.fixture
def tenant_workspace(tmp_path: Path):
    """Sets up a test directory layout with two distinct tenants."""
    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Workspace A
    ws_a = base_dir / "workspace_alpha"
    ws_a.mkdir()
    proj_a1 = ws_a / "prj_alpha_iso_1"
    proj_a1.mkdir()
    (proj_a1 / "project.json").write_text(json.dumps({"project_id": "prj_alpha_iso_1", "workspace_id": "workspace_alpha"}), encoding="utf-8")

    # Workspace B
    ws_b = base_dir / "workspace_beta"
    ws_b.mkdir()
    proj_b1 = ws_b / "prj_beta_iso_1"
    proj_b1.mkdir()
    (proj_b1 / "project.json").write_text(json.dumps({"project_id": "prj_beta_iso_1", "workspace_id": "workspace_beta"}), encoding="utf-8")

    # Legacy flat project belonging to Workspace A
    legacy_proj = base_dir / "prj_legacy_iso_a"
    legacy_proj.mkdir()
    (legacy_proj / "project.json").write_text(json.dumps({"project_id": "prj_legacy_iso_a", "workspace_id": "workspace_alpha"}), encoding="utf-8")

    return base_dir


def test_validate_workspace_id():
    assert validate_workspace_id("ws_alpha-123_test") == "ws_alpha-123_test"

    with pytest.raises((ValueError, TenantSecurityError)):
        validate_workspace_id("../evil")

    with pytest.raises((ValueError, TenantSecurityError)):
        validate_workspace_id("ws/evil")

    with pytest.raises((ValueError, TenantSecurityError)):
        validate_workspace_id("")


def test_canonical_project_dir(tmp_path: Path):
    base_dir = tmp_path / "projects"
    canonical = get_canonical_project_dir("prj_001", "ws_team", base_dir=base_dir)
    assert canonical == (base_dir / "ws_team" / "prj_001").resolve()


def test_cross_tenant_isolation_enforced(tenant_workspace: Path):
    # Workspace Alpha accessing own project -> succeeds
    p_a = resolve_project_dir("prj_alpha_iso_1", workspace_id="workspace_alpha", base_dir=tenant_workspace)
    assert p_a.exists()
    assert "workspace_alpha" in str(p_a)

    # Workspace Beta accessing Workspace Alpha's project -> REJECTED with TenantSecurityError
    with pytest.raises(TenantSecurityError):
        resolve_project_dir("prj_alpha_iso_1", workspace_id="workspace_beta", base_dir=tenant_workspace)


def test_mandatory_workspace_id_enforced(tenant_workspace: Path):
    # Attempting to resolve project without workspace_id when not in DB/env -> REJECTED
    with pytest.raises(TenantSecurityError, match="workspace_id is strictly required"):
        resolve_project_dir("prj_unscoped_test", workspace_id=None, base_dir=tenant_workspace)


def test_no_legacy_flat_fallback(tenant_workspace: Path):
    # A flat legacy project in base_dir/prj_legacy_iso_a is NOT resolved as a flat path
    p = resolve_project_dir("prj_legacy_iso_a", workspace_id="workspace_alpha", base_dir=tenant_workspace)
    # Target path must be strictly within workspace_alpha
    assert p == (tenant_workspace / "workspace_alpha" / "prj_legacy_iso_a").resolve()
    # It does not point to the flat legacy path
    assert str(p) != str((tenant_workspace / "prj_legacy_iso_a").resolve())


def test_database_cross_tenant_mismatch_rejected(tenant_workspace: Path, monkeypatch):
    from unittest.mock import MagicMock
    from scripts.core.database import ProjectRecord

    # Mock TenantRepository to return project belonging to workspace_alpha
    mock_repo = MagicMock()
    mock_repo.get_project.return_value = ProjectRecord(
        id="prj_db_test",
        workspace_id="workspace_alpha",
        created_by="usr_test",
        name="DB Test Project",
        created_at="2026-10-12T00:00:00Z",
        updated_at="2026-10-12T00:00:00Z",
    )

    import scripts.core.database as db_mod
    monkeypatch.setattr(db_mod, "TenantRepository", lambda engine: mock_repo)

    # Requesting access for workspace_beta must be rejected due to DB record mismatch
    with pytest.raises(TenantSecurityError, match="Cross-tenant project access rejected"):
        resolve_project_dir("prj_db_test", workspace_id="workspace_beta", base_dir=tenant_workspace)


def test_path_traversal_prevention(tenant_workspace: Path):
    with pytest.raises((PathTraversalError, TenantSecurityError, ValueError)):
        resolve_project_dir("../../etc/passwd", workspace_id="workspace_alpha", base_dir=tenant_workspace)

    with pytest.raises((PathTraversalError, TenantSecurityError, ValueError)):
        resolve_project_dir("prj_alpha_1", workspace_id="../../root", base_dir=tenant_workspace)


def test_symlink_escape_prevention(tenant_workspace: Path, tmp_path: Path):
    # Target outside base_dir
    secret_dir = tmp_path / "system_secrets"
    secret_dir.mkdir()
    (secret_dir / "passwd").write_text("secret", encoding="utf-8")

    # Create a project with a symlink pointing to outside target
    evil_project = tenant_workspace / "workspace_alpha" / "prj_evil_symlink"
    evil_project.mkdir()
    evil_symlink = evil_project / "leaked_dir"
    try:
        os.symlink(secret_dir, evil_symlink)
    except OSError:
        pytest.skip("Symlinks not supported in this test environment")

    # check_confinement_and_symlink must catch the escape
    with pytest.raises((PathSecurityViolation, TenantSecurityError)):
        check_confinement_and_symlink(evil_symlink, tenant_workspace / "workspace_alpha")


def test_new_project_lifecycle_under_pure_tenant_layout(tmp_path: Path):
    """Proves that newly created projects complete their full lifecycle strictly under projects/{workspace_id}/{project_id}/ without legacy fallbacks."""
    from scripts.core.state_store import StateStore, LifecycleState, ProjectState

    base_dir = tmp_path / "projects"
    ws_id = "ws_tenant_gamma"
    proj_id = "prj_lifecycle_001"

    # 1. Resolve & create pure tenant path
    proj_dir = resolve_project_dir(proj_id, workspace_id=ws_id, base_dir=base_dir, create=True)
    assert proj_dir == (base_dir / ws_id / proj_id).resolve()
    assert proj_dir.exists()

    # 2. Write project metadata & manifest
    (proj_dir / "project.json").write_text(
        json.dumps({"project_id": proj_id, "workspace_id": ws_id, "name": "Pure Tenant Project"}),
        encoding="utf-8"
    )
    (proj_dir / "02_asset_manifest.json").write_text(
        json.dumps({"manifest_version": "2.0.0", "project_id": proj_id, "assets": []}),
        encoding="utf-8"
    )

    # 3. Initialize canonical state
    state = ProjectState(
        project_id=proj_id,
        workspace_id=ws_id,
        revision=1,
        lifecycle_state=LifecycleState.DRAFT,
    )
    StateStore.save(proj_dir, state)

    # 4. Verify state persistence and load
    loaded = StateStore.load(proj_dir)
    assert loaded is not None
    assert loaded.project_id == proj_id
    assert loaded.workspace_id == ws_id
    assert loaded.revision == 1
    assert loaded.lifecycle_state == LifecycleState.DRAFT

    # 5. Advance lifecycle state to ASSETS_READY -> PLAN_READY
    def mutator(s):
        s.lifecycle_state = LifecycleState.PLAN_READY
    updated = StateStore.atomic_update(proj_dir, 1, mutator)
    assert updated.revision == 2
    assert updated.lifecycle_state == LifecycleState.PLAN_READY

    # 6. Verify cross-tenant confinement: foreign tenant cannot access this project
    with pytest.raises(TenantSecurityError):
        resolve_project_dir(proj_id, workspace_id="ws_foreign_intruder", base_dir=base_dir)


def test_workspace_level_symlink_escape_rejected(tmp_path: Path):
    """Verifies that if a workspace directory itself is a symlink pointing outside canonical projects root, it is rejected."""
    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)
    outside_dir = tmp_path / "host_secrets"
    outside_dir.mkdir()

    evil_ws_symlink = base_dir / "ws_evil_symlink"
    try:
        os.symlink(outside_dir, evil_ws_symlink)
    except OSError:
        pytest.skip("Symlinks not supported in this test environment")

    # 1. get_canonical_project_dir must reject workspace-level symlink escape
    with pytest.raises((PathSecurityViolation, TenantSecurityError)):
        get_canonical_project_dir("prj_victim", "ws_evil_symlink", base_dir=base_dir)

    # 2. resolve_project_dir must reject workspace-level symlink escape
    with pytest.raises((PathSecurityViolation, TenantSecurityError)):
        resolve_project_dir("prj_victim", workspace_id="ws_evil_symlink", base_dir=base_dir)


def test_missing_identity_rejects_filesystem_access(tmp_path: Path, monkeypatch):
    """Verifies that missing or unverifiable workspace identity strictly denies filesystem access."""
    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Create unmanaged project directory directly under projects/
    unmanaged = base_dir / "prj_orphan"
    unmanaged.mkdir()

    monkeypatch.delenv("AGY_WORKSPACE_ID", raising=False)

    with pytest.raises(TenantSecurityError, match="workspace_id is strictly required"):
        resolve_project_dir("prj_orphan", workspace_id=None, base_dir=base_dir)


def test_database_lookup_failure_fails_closed(tmp_path: Path, monkeypatch):
    """Verifies that database operational failures during authorization verification fail closed."""
    from unittest.mock import MagicMock
    import scripts.core.database as db_mod

    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)

    mock_repo = MagicMock()
    mock_repo.get_project.side_effect = RuntimeError("Database connection pool exhausted")

    monkeypatch.setattr(db_mod, "TenantRepository", lambda engine: mock_repo)

    # Failing DB during cross-tenant boundary verification must raise TenantSecurityError (fail closed)
    with pytest.raises(TenantSecurityError, match="Database lookup failed"):
        resolve_project_dir("prj_any", workspace_id="ws_test", base_dir=base_dir, enforce_tenant_boundary=True)


def test_legacy_flat_directory_access_rejected(tmp_path: Path, monkeypatch):
    """Verifies that legacy flat directories cannot be accessed as standalone unmanaged projects."""
    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)
    legacy_flat = base_dir / "prj_legacy_standalone"
    legacy_flat.mkdir()
    (legacy_flat / "master_plan.md").write_text("# Plan", encoding="utf-8")

    monkeypatch.delenv("AGY_WORKSPACE_ID", raising=False)

    # 1. Without workspace_id -> Strictly rejected, never returns flat path
    with pytest.raises(TenantSecurityError, match="workspace_id is strictly required"):
        resolve_project_dir("prj_legacy_standalone", workspace_id=None, base_dir=base_dir)

    # 2. With workspace_id -> Resolved under tenant workspace directory, NOT flat path
    resolved = resolve_project_dir("prj_legacy_standalone", workspace_id="ws_legit", base_dir=base_dir)
    assert resolved == (base_dir / "ws_legit" / "prj_legacy_standalone").resolve()
    assert str(resolved) != str(legacy_flat.resolve())


def test_final_qc_fails_closed_on_resolution_error(tmp_path: Path, monkeypatch):
    """Verifies that run_final_qc fails closed with structured reporting if tenant path resolution fails."""
    from scripts.gates.final_qc import run_final_qc

    monkeypatch.delenv("AGY_WORKSPACE_ID", raising=False)
    ok, report = run_final_qc("prj_unresolvable_qc", workspace_root=tmp_path)

    assert ok is False
    assert report["status"] == "FAIL"
    assert "path_resolution" in report["checks"]
    assert report["checks"]["path_resolution"]["status"] == "FAIL"
    assert "Fail-closed" in report["checks"]["path_resolution"]["message"]


# ─── Probe QC Security & Boundary Hardening Tests ─────────────────────────────

def test_probe_qc_untrusted_absolute_path_fails_closed(tmp_path: Path):
    """
    Verifies that run_probe_qc strictly rejects direct filesystem paths,
    and that the mere presence of 05_blueprint.json does NOT grant authorization.
    """
    from scripts.gates.probe_qc import run_probe_qc

    evil_dir = tmp_path / "untrusted_arbitrary_dir"
    evil_dir.mkdir(parents=True, exist_ok=True)

    # Place a valid blueprint and manifest inside evil_dir
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_evil",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 30}]
    }
    (evil_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (evil_dir / "media_map.json").write_text("{}", encoding="utf-8")

    # 1. Calling run_probe_qc with Path object
    report_path = run_probe_qc(evil_dir)
    assert report_path["status"] == "EXECUTION_FAILURE"
    assert report_path["legacy_status"] == "fail"
    assert any("Direct filesystem paths are not accepted" in e["message"] for e in report_path["errors"])

    # 2. Calling run_probe_qc with string path
    report_str = run_probe_qc(str(evil_dir))
    assert report_str["status"] == "EXECUTION_FAILURE"
    assert report_str["legacy_status"] == "fail"
    assert any("Direct filesystem paths are not accepted" in e["message"] for e in report_str["errors"])

    # 3. Assert NO artifacts or unlock files are generated
    assert not (evil_dir / ".studio_unlocked").exists()
    assert not (evil_dir / "03_probe_qc").exists()
    assert not (evil_dir / "probe_qc_report.json").exists()


def test_probe_qc_legacy_flat_directory_rejected(tmp_path: Path):
    """
    Verifies that legacy flat project directories lacking workspace namespace
    are rejected by run_probe_qc_for_trusted_directory.
    """
    from scripts.gates.probe_qc import run_probe_qc_for_trusted_directory

    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)

    flat_dir = base_dir / "prj_legacy_flat"
    flat_dir.mkdir(parents=True, exist_ok=True)
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_legacy_flat",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 30}]
    }
    (flat_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")

    report = run_probe_qc_for_trusted_directory(
        project_dir=flat_dir,
        trusted_confinement_root=base_dir,
        authorization_context={"workspace_id": "ws_legit"},
    )

    assert report["status"] == "EXECUTION_FAILURE"
    assert any("Legacy flat project directory rejected" in e["message"] for e in report["errors"])
    assert not (flat_dir / ".studio_unlocked").exists()


def test_probe_qc_symlink_escape_rejected(tmp_path: Path):
    """
    Verifies that symlinked directories escaping trusted confinement root
    are strictly rejected by run_probe_qc_for_trusted_directory.
    """
    from scripts.gates.probe_qc import run_probe_qc_for_trusted_directory

    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)

    outside_dir = tmp_path / "outside_host_data" / "target_proj"
    outside_dir.mkdir(parents=True, exist_ok=True)
    (outside_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    ws_dir = base_dir / "ws_evil"
    ws_dir.mkdir()
    symlink_proj = ws_dir / "prj_symlink"
    try:
        os.symlink(outside_dir, symlink_proj)
    except OSError:
        pytest.skip("Symlinks not supported in environment")

    report = run_probe_qc_for_trusted_directory(
        project_dir=symlink_proj,
        trusted_confinement_root=base_dir,
        authorization_context={"workspace_id": "ws_evil"},
    )

    assert report["status"] == "EXECUTION_FAILURE"
    assert any("escapes trusted confinement root" in e["message"] for e in report["errors"])
    assert not (outside_dir / ".studio_unlocked").exists()


def test_probe_qc_missing_workspace_identity_fails_closed(tmp_path: Path, monkeypatch):
    """
    Verifies that calling run_probe_qc without workspace identity strictly fails closed.
    """
    from scripts.gates.probe_qc import run_probe_qc

    monkeypatch.delenv("AGY_WORKSPACE_ID", raising=False)

    report = run_probe_qc("prj_any_id", workspace_root=tmp_path, workspace_id=None)
    assert report["status"] == "EXECUTION_FAILURE"
    assert any("workspace_id is strictly required" in e["message"] for e in report["errors"])


def test_probe_qc_mismatched_tenant_ownership_rejected(tmp_path: Path):
    """
    Verifies that if ProjectState declares ownership by ws_victim, but
    authorization_context declares ws_attacker, access is rejected.
    """
    from scripts.gates.probe_qc import run_probe_qc_for_trusted_directory
    from scripts.core.state_store import StateStore

    base_dir = tmp_path / "projects"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Project directory located under ws_attacker
    attacker_ws = base_dir / "ws_attacker"
    attacker_ws.mkdir()
    proj_dir = attacker_ws / "prj_hijack"
    proj_dir.mkdir()

    # But StateStore asserts ownership by ws_victim
    st = StateStore.create(proj_dir, "prj_hijack", workspace_id="ws_victim")
    StateStore.save(proj_dir, st)

    report = run_probe_qc_for_trusted_directory(
        project_dir=proj_dir,
        trusted_confinement_root=base_dir,
        authorization_context={"workspace_id": "ws_attacker"},
    )

    assert report["status"] == "EXECUTION_FAILURE"
    assert any("Mismatched tenant ownership" in e["message"] for e in report["errors"])
    assert not (proj_dir / ".studio_unlocked").exists()


def test_probe_qc_failed_authorization_produces_no_approval_state(tmp_path: Path):
    """
    Verifies that failed authorization cannot produce ReviewBundle, .studio_unlocked,
    probe reports, or frame plans.
    """
    from scripts.gates.probe_qc import run_probe_qc_for_trusted_directory

    target_dir = tmp_path / "arbitrary_dir"
    target_dir.mkdir()

    # 1. Missing trusted_confinement_root
    r1 = run_probe_qc_for_trusted_directory(target_dir, trusted_confinement_root=None, authorization_context={"workspace_id": "ws_1"})
    assert r1["status"] == "EXECUTION_FAILURE"

    # 2. Missing authorization_context
    r2 = run_probe_qc_for_trusted_directory(target_dir, trusted_confinement_root=tmp_path, authorization_context=None)
    assert r2["status"] == "EXECUTION_FAILURE"

    # 3. Empty workspace_id
    r3 = run_probe_qc_for_trusted_directory(target_dir, trusted_confinement_root=tmp_path, authorization_context={"workspace_id": ""})
    assert r3["status"] == "EXECUTION_FAILURE"

    # Assert no approval artifacts exist
    assert not (target_dir / ".studio_unlocked").exists()
    assert not (target_dir / "03_probe_qc").exists()
    assert not (target_dir / "probe_qc_report.json").exists()



