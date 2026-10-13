#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/core/test_tenant_project_migration.py — Tests for tenant project filesystem migration utility.
Verifies discovery, collision detection, missing-owner fallback, atomic moves, idempotency, and rollback on disposable fixtures.
"""

import json
from pathlib import Path
import pytest

from scripts.migration.tenant_project_migration import TenantProjectMigrator


@pytest.fixture
def migration_fixture(tmp_path: Path):
    """Sets up a test projects directory with legacy and existing tenant projects."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    # Legacy project 1: has project.json with workspace_id="ws_alpha"
    p1 = projects_dir / "prj_legacy_001"
    p1.mkdir()
    (p1 / "project.json").write_text(json.dumps({"project_id": "prj_legacy_001", "workspace_id": "ws_alpha"}), encoding="utf-8")
    (p1 / "01_manifest.json").write_text(json.dumps({"title": "Test 1"}), encoding="utf-8")
    (p1 / "out.mp4").write_bytes(b"dummy video data 1")

    # Legacy project 2: has .pipeline_state.json with workspace_id="ws_beta"
    p2 = projects_dir / "prj_legacy_002"
    p2.mkdir()
    (p2 / ".pipeline_state.json").write_text(json.dumps({"project_id": "prj_legacy_002", "workspace_id": "ws_beta"}), encoding="utf-8")
    (p2 / "notes.txt").write_text("dummy notes", encoding="utf-8")

    # Legacy project 3: has no workspace info (should fallback to default)
    p3 = projects_dir / "prj_legacy_003"
    p3.mkdir()
    (p3 / "01_manifest.json").write_text(json.dumps({"title": "Test 3"}), encoding="utf-8")

    # Pre-existing workspace directory with project that will collide
    # Target: projects/ws_alpha/prj_collision
    ws_alpha_dir = projects_dir / "ws_alpha"
    ws_alpha_dir.mkdir()
    target_collision = ws_alpha_dir / "prj_collision"
    target_collision.mkdir()
    (target_collision / "collision_marker.txt").write_text("existing content", encoding="utf-8")

    # Legacy project that collides with ws_alpha/prj_collision
    p_coll = projects_dir / "prj_collision"
    p_coll.mkdir()
    (p_coll / "project.json").write_text(json.dumps({"project_id": "prj_collision", "workspace_id": "ws_alpha"}), encoding="utf-8")
    (p_coll / "source_marker.txt").write_text("source content", encoding="utf-8")

    return projects_dir


def test_dry_run_discovers_and_plans_without_moving(migration_fixture: Path):
    migrator = TenantProjectMigrator(base_dir=migration_fixture, default_workspace="ws_default")
    report = migrator.plan()

    assert report.dry_run is True
    assert report.total_discovered == 4  # prj_legacy_001, prj_legacy_002, prj_legacy_003, prj_collision
    assert report.planned_moves == 3     # 001, 002, 003 (collision is skipped)
    assert report.collisions == 1        # prj_collision
    assert report.missing_owner_fallback == 1  # prj_legacy_003

    # Verify no files were moved
    assert (migration_fixture / "prj_legacy_001").exists()
    assert (migration_fixture / "prj_legacy_002").exists()
    assert (migration_fixture / "prj_legacy_003").exists()
    assert (migration_fixture / "prj_collision").exists()


def test_execute_and_rollback_cycle(migration_fixture: Path, tmp_path: Path):
    migrator = TenantProjectMigrator(base_dir=migration_fixture, default_workspace="ws_default")
    manifest_file = tmp_path / "test_manifest.json"

    # 1. Execute Migration
    report = migrator.execute(manifest_out=manifest_file)

    assert report.dry_run is False
    assert report.successful_moves == 3
    assert report.failed_moves == 0
    assert report.collisions == 1

    # Verify new locations exist
    target_001 = migration_fixture / "ws_alpha" / "prj_legacy_001"
    target_002 = migration_fixture / "ws_beta" / "prj_legacy_002"
    target_003 = migration_fixture / "ws_default" / "prj_legacy_003"

    assert target_001.exists()
    assert (target_001 / "out.mp4").read_bytes() == b"dummy video data 1"
    assert target_002.exists()
    assert target_003.exists()

    # Verify old locations are gone for moved projects
    assert not (migration_fixture / "prj_legacy_001").exists()
    assert not (migration_fixture / "prj_legacy_002").exists()
    assert not (migration_fixture / "prj_legacy_003").exists()

    # Verify collision project remained in place safely
    assert (migration_fixture / "prj_collision").exists()
    assert (migration_fixture / "ws_alpha" / "prj_collision" / "collision_marker.txt").exists()

    # Verify audit manifest exists and is populated
    assert manifest_file.exists()
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["successful_moves"] == 3

    # 2. Test Idempotency: Running plan or execute again should find NO new legacy projects to move
    second_plan = migrator.plan()
    assert second_plan.planned_moves == 0
    # Only the collided one remains at top level
    assert second_plan.total_discovered == 1
    assert second_plan.collisions == 1

    # 3. Test Rollback
    rollback_res = TenantProjectMigrator.rollback(manifest_file)
    assert rollback_res["rolled_back"] == 3
    assert rollback_res["failed"] == 0

    # Verify restored original structure
    assert (migration_fixture / "prj_legacy_001").exists()
    assert (migration_fixture / "prj_legacy_001" / "out.mp4").read_bytes() == b"dummy video data 1"
    assert (migration_fixture / "prj_legacy_002").exists()
    assert (migration_fixture / "prj_legacy_003").exists()

    # Verify target paths no longer have those projects
    assert not target_001.exists()
    assert not target_002.exists()
    assert not target_003.exists()
