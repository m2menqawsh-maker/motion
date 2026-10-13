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

