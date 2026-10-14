"""
tests/security/test_project_lock_and_credential_isolation.py
============================================================
Authoritative Security Verification for Finding B and Finding C (Batch 4 Review):
1. Verifies that ProjectExecutionLock resolves workspace ownership authoritatively:
   - Valid workspace IDs without 'ws_' prefix (e.g. 'tenant_42', 'org_alpha') resolve cleanly.
   - Missing or ambiguous workspace identity fails closed with TenantSecurityError.
   - Mismatched ownership between explicit parameter and DB registration fails closed.
   - Mismatched ownership between explicit parameter and filesystem path fails closed.
   - Execution lease records the authoritative workspace ID, never 'ws_default'.
2. Verifies strict database credential isolation and non-disclosure:
   - scripts/pipeline.py receives DATABASE_URL when authorized.
   - Remotion, FFmpeg, and render_project.py have database credentials strictly stripped.
   - Git read-only subcommands are authorized via CommandPolicy; dangerous subcommands are rejected.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from scripts.core.database import DatabaseEngine, TenantRepository
from scripts.core.project_lock import ProjectExecutionLock, ProjectExecutionConflictError
from scripts.core.run_repository import RunRepository
from scripts.core.security.command_policy import CommandPolicy, DATABASE_CREDENTIAL_ENV_VARS
from scripts.security.path_security import TenantSecurityError


@pytest.fixture
def isolated_db(tmp_path: Path):
    db_file = tmp_path / "test_auth.db"
    db_url = f"sqlite:///{db_file}"
    engine = DatabaseEngine(db_url)
    repo = TenantRepository(engine)
    return {"engine": engine, "tenant_repo": repo, "db_path": db_file, "db_url": db_url}


class TestProjectLockWorkspaceSecurity:
    """Finding B Security Tests: Authoritative Workspace Resolution & Fail-Closed."""

    def test_valid_workspace_without_ws_prefix(self, tmp_path: Path, isolated_db: dict):
        """Workspace IDs without 'ws_' prefix must resolve cleanly from DB or explicit arg."""
        ws_id = "tenant_custom_org"
        proj_id = "proj_alpha_01"

        # Register in database
        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_admin", "admin@example.com")
        repo.create_workspace(ws_id, "Custom Org", created_by="usr_admin")
        repo.create_project(proj_id, ws_id, "Alpha Video", created_by="usr_admin")

        proj_dir = tmp_path / "projects" / ws_id / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        lock = ProjectExecutionLock(
            project_dir=proj_dir,
            owner_id="test_worker",
            db_path=isolated_db["db_path"],
            workspace_id=ws_id,
        )
        assert lock.workspace_id == ws_id

        # Also test discovery without explicit workspace_id (discovered via DB and path)
        lock_auto = ProjectExecutionLock(
            project_dir=proj_dir,
            owner_id="test_worker",
            db_path=isolated_db["db_path"],
        )
        assert lock_auto.workspace_id == ws_id

    def test_missing_workspace_identity_fails_closed(self, tmp_path: Path, isolated_db: dict):
        """Unregistered project with no explicit workspace and flat directory must fail closed."""
        proj_id = "proj_orphan_flat"
        # Flat directory under projects (no workspace parent directory)
        proj_dir = tmp_path / "projects" / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(TenantSecurityError, match="missing or ambiguous workspace identity"):
            ProjectExecutionLock(
                project_dir=proj_dir,
                owner_id="test_worker",
                db_path=isolated_db["db_path"],
            )

    def test_mismatched_explicit_vs_db_ownership_fails_closed(self, tmp_path: Path, isolated_db: dict):
        """Explicit workspace mismatch against authoritative DB registration must fail closed."""
        authoritative_ws = "tenant_authoritative"
        spoofed_ws = "tenant_attacker"
        proj_id = "proj_secured_42"

        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_owner", "owner@example.com")
        repo.create_workspace(authoritative_ws, "Authoritative Org", created_by="usr_owner")
        repo.create_workspace(spoofed_ws, "Attacker Org", created_by="usr_owner")
        repo.create_project(proj_id, authoritative_ws, "Secured Video", created_by="usr_owner")

        proj_dir = tmp_path / "projects" / authoritative_ws / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(TenantSecurityError, match="Workspace ownership mismatch"):
            ProjectExecutionLock(
                project_dir=proj_dir,
                owner_id="test_worker",
                db_path=isolated_db["db_path"],
                workspace_id=spoofed_ws,
            )

    def test_mismatched_explicit_vs_filesystem_ownership_fails_closed(self, tmp_path: Path, isolated_db: dict):
        """Explicit workspace mismatch against filesystem parent directory must fail closed."""
        fs_ws = "tenant_fs_actual"
        explicit_ws = "tenant_other"
        proj_id = "proj_mismatch_path"

        proj_dir = tmp_path / "projects" / fs_ws / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(TenantSecurityError, match="Workspace ownership mismatch"):
            ProjectExecutionLock(
                project_dir=proj_dir,
                owner_id="test_worker",
                db_path=isolated_db["db_path"],
                workspace_id=explicit_ws,
            )

    def test_lease_acquisition_records_authoritative_workspace(self, tmp_path: Path, isolated_db: dict):
        """Acquiring the lock must record the authoritative workspace in database leases."""
        ws_id = "tenant_production_99"
        proj_id = "proj_lease_test"

        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_prod", "prod@example.com")
        repo.create_workspace(ws_id, "Production Org", created_by="usr_prod")
        repo.create_project(proj_id, ws_id, "Production Video", created_by="usr_prod")

        proj_dir = tmp_path / "projects" / ws_id / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        lock = ProjectExecutionLock(
            project_dir=proj_dir,
            owner_id="worker_alpha",
            run_id="run_test_lease_01",
            db_path=isolated_db["db_path"],
            workspace_id=ws_id,
        )

        with lock:
            active_lease = lock.repo.get_active_project_lease(proj_id)
            assert active_lease is not None
            assert active_lease["workspace_id"] == ws_id
            assert active_lease["workspace_id"] != "ws_default"
            assert active_lease["worker_id"] == "worker_alpha"

        # After exit, lease should be released
        post_lease = lock.repo.get_active_project_lease(proj_id)
        assert post_lease is None


class TestDatabaseCredentialIsolation:
    """Finding C Security Tests: Credential Non-Disclosure & Propagation."""

    def test_pipeline_authorized_database_propagation(self):
        """scripts/pipeline.py receives database credentials when allow_database_env=True."""
        base_env = {
            "PATH": "/bin:/usr/bin",
            "DATABASE_URL": "postgresql://usr:secret@db.internal:5432/motion",
            "RUNS_DB_PATH": "/data/runs.db",
            "AUTH_SECRET_KEY": "super_secret_jwt_signing_key",
        }

        # 1. By default without allow_database_env, credentials are not leaked
        clean_default = CommandPolicy.sanitize_environment(
            base_env=base_env,
            target_script="scripts/pipeline.py",
            allow_database_env=False,
            is_production=True,
        )
        assert "DATABASE_URL" not in clean_default

        # 2. When explicitly requested via allow_database_env=True (as in PipelineService.run_pipeline)
        clean_auth = CommandPolicy.sanitize_environment(
            base_env=base_env,
            target_script="scripts/pipeline.py",
            allow_database_env=True,
            is_production=True,
        )
        assert "DATABASE_URL" in clean_auth
        assert clean_auth["DATABASE_URL"] == base_env["DATABASE_URL"]
        assert "RUNS_DB_PATH" in clean_auth

    def test_credentials_strictly_stripped_from_renderers_and_tools(self):
        """Rendering engines, FFmpeg, and external tools must NEVER receive DB credentials."""
        base_env = {
            "PATH": "/bin:/usr/bin",
            "DATABASE_URL": "postgresql://usr:secret@db.internal:5432/motion",
            "RUNS_DB_PATH": "/data/runs.db",
            "AUTH_SECRET_KEY": "super_secret_jwt_signing_key",
            "MOTION_DATABASE_URL": "postgresql://usr:secret@db.internal:5432/motion",
        }

        untrusted_targets = [
            "scripts/render_project.py",
            "remotion",
            "npx remotion",
            "ffmpeg",
            "ffprobe",
            "docker run clean-video-builder",
            "scripts/gates/taste_gate.py",
            "scripts/gates/asset_gate.py",
        ]

        for target in untrusted_targets:
            clean = CommandPolicy.sanitize_environment(
                base_env=base_env,
                target_script=target,
                allow_database_env=False,
                is_production=True,
            )
            for secret_var in DATABASE_CREDENTIAL_ENV_VARS:
                assert secret_var not in clean, f"Security leak: '{secret_var}' leaked to untrusted target '{target}'"

    def test_git_command_policy_validation(self):
        """Git read-only inventory enumeration allowed; git status and modifying subcommands strictly denied."""
        from scripts.security.security import safe_subprocess

        # Allowed read-only subcommands for inventory/tooling
        res_ls = CommandPolicy.validate_command(["git", "-c", "core.quotepath=false", "ls-files"])
        assert res_ls.is_allowed, f"git ls-files should be allowed: {res_ls.violations}"

        # Prohibited git commands in general runtime
        res_status = CommandPolicy.validate_command(["git", "status", "--porcelain"])
        assert not res_status.is_allowed
        assert any("forbidden" in v for v in res_status.violations)

        res_push = CommandPolicy.validate_command(["git", "push", "origin", "main"])
        assert not res_push.is_allowed
        assert any("forbidden" in v for v in res_push.violations)

        res_commit = CommandPolicy.validate_command(["git", "commit", "-m", "slop"])
        assert not res_commit.is_allowed
        assert any("forbidden" in v for v in res_commit.violations)

        # safe_subprocess raises PermissionError on prohibited commands
        with pytest.raises(PermissionError, match="forbidden"):
            safe_subprocess(["git", "status"])
