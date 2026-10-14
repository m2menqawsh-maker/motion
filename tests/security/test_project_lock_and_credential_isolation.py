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

    def test_unregistered_project_cannot_trust_directory_name(self, tmp_path: Path, isolated_db: dict):
        """Unregistered project under projects/ cannot infer workspace identity solely from directory name."""
        proj_id = "proj_unregistered_spoof"
        ws_id = "tenant_innocent_victim"

        # Directory exists under projects, but project is NOT registered in database
        proj_dir = tmp_path / "projects" / ws_id / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(TenantSecurityError, match="Workspace identity cannot be trusted solely from a directory name"):
            ProjectExecutionLock(
                project_dir=proj_dir,
                owner_id="attacker_worker",
                db_path=isolated_db["db_path"],
                workspace_id=None,
            )

    def test_arbitrary_path_outside_canonical_projects_root_rejected(self, tmp_path: Path, isolated_db: dict):
        """Project directory outside canonical projects root is strictly rejected even with valid directory name."""
        proj_id = "proj_external_attack"
        ws_id = "tenant_valid_syntax"

        # Path under /tmp/some_random/ws_id/proj_id (grandparent is NOT 'projects')
        proj_dir = tmp_path / "some_random_folder" / ws_id / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        # Case A: No explicit workspace provided -> fails closed
        with pytest.raises(TenantSecurityError, match="Workspace identity cannot be trusted solely from a directory name"):
            ProjectExecutionLock(
                project_dir=proj_dir,
                owner_id="attacker_worker",
                db_path=isolated_db["db_path"],
                workspace_id=None,
            )

        # Case B: Explicit workspace provided on unregistered project outside projects root -> rejected as non-canonical
        with pytest.raises(TenantSecurityError, match="not verified to reside under.*canonical projects root"):
            ProjectExecutionLock(
                project_dir=proj_dir,
                owner_id="attacker_worker",
                db_path=isolated_db["db_path"],
                workspace_id=ws_id,
            )

    def test_primary_db_fallback_when_repo_db_unregistered(self, tmp_path: Path, isolated_db: dict, monkeypatch):
        """When repo db has no project registration, lock queries primary database engine authoritatively."""
        authoritative_ws = "tenant_primary_registered"
        proj_id = "proj_multi_db_test"

        # Register project in isolated_db
        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_multi", "multi@example.com")
        repo.create_workspace(authoritative_ws, "Primary Org", created_by="usr_multi")
        repo.create_project(proj_id, authoritative_ws, "Multi DB Video", created_by="usr_multi")

        # Point get_database_engine to isolated_db
        monkeypatch.setattr("scripts.core.database.get_database_engine", lambda: isolated_db["engine"])

        # Create a secondary empty repo database (e.g. local worker runs db)
        worker_runs_db = tmp_path / "worker_local_runs.db"
        worker_engine = DatabaseEngine(f"sqlite:///{worker_runs_db}")
        # Note: worker_runs_db does NOT have the project registration in its tenant table
        worker_repo = TenantRepository(worker_engine)

        proj_dir = tmp_path / "projects" / authoritative_ws / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        # Lock initialized with worker_runs_db where project is NOT registered
        # It must fall back to get_database_engine() and discover authoritative_ws!
        lock = ProjectExecutionLock(
            project_dir=proj_dir,
            owner_id="worker_secondary",
            db_path=worker_runs_db,
            workspace_id=None,
        )
        assert lock.workspace_id == authoritative_ws


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

    def test_provider_secrets_strictly_stripped_from_untrusted_targets(self):
        """Untrusted rendering, media, Git, and generic subprocesses must NEVER receive external provider secrets."""
        from scripts.core.security.command_policy import AI_PROVIDER_SECRET_ENV_VARS

        base_env = {
            "PATH": "/bin:/usr/bin",
            "OPENAI_API_KEY": "sk-proj-super-secret-openai-key",
            "ANTHROPIC_API_KEY": "sk-ant-secret-anthropic-key",
            "ELEVENLABS_API_KEY": "el_secret_elevenlabs_token",
            "OPENROUTER_API_KEY": "sk-or-v1-secret-openrouter-key",
            "REPLICATE_API_TOKEN": "r8_secret_replicate_token",
            "MOTION_API_KEY": "motion-internal-service-key",
            "MOTION_ADMIN_TOKEN": "motion-admin-jwt-token",
            "MOTION_PROJECTS_ROOT": "/canonical/projects",
        }

        untrusted_targets = [
            "scripts/render_project.py",
            "remotion",
            "npx remotion",
            "ffmpeg",
            "ffprobe",
            "git",
            "scripts/gates/taste_gate.py",
            "scripts/gates/asset_gate.py",
            "scripts/generators/materialize_project.py",
            None,  # General default subprocess target
        ]

        for target in untrusted_targets:
            clean = CommandPolicy.sanitize_environment(
                base_env=base_env,
                target_script=target,
                allow_ai_env=False,
                is_production=True,
            )
            for secret_var in AI_PROVIDER_SECRET_ENV_VARS:
                assert secret_var not in clean, f"Leak: '{secret_var}' leaked to untrusted target '{target}'"
            assert "MOTION_API_KEY" not in clean, f"Leak: MOTION_API_KEY leaked to '{target}'"
            assert "MOTION_ADMIN_TOKEN" not in clean, f"Leak: MOTION_ADMIN_TOKEN leaked to '{target}'"
            # Benign configuration variable MUST be preserved
            assert clean.get("MOTION_PROJECTS_ROOT") == "/canonical/projects"

    def test_provider_secrets_granted_to_authorized_ai_integrations(self):
        """Explicitly authorized AI integration targets and allow_ai_env=True receive external provider secrets."""
        base_env = {
            "PATH": "/bin:/usr/bin",
            "OPENAI_API_KEY": "sk-proj-authorized-key",
            "ANTHROPIC_API_KEY": "sk-ant-authorized-key",
            "OPENROUTER_API_KEY": "sk-or-authorized-key",
            "REPLICATE_API_TOKEN": "r8_authorized_token",
        }

        authorized_scripts = [
            "scripts/smoke_openrouter.py",
            "scripts/run_creative_e2e.py",
            "scripts/run_creative_cost_audit.py",
            "scripts/run_real_cost_performance_benchmark.py",
        ]

        for target in authorized_scripts:
            clean = CommandPolicy.sanitize_environment(
                base_env=base_env,
                target_script=target,
                is_production=True,
            )
            assert clean.get("OPENROUTER_API_KEY") == "sk-or-authorized-key"
            assert clean.get("OPENAI_API_KEY") == "sk-proj-authorized-key"
            assert clean.get("ANTHROPIC_API_KEY") == "sk-ant-authorized-key"
            assert clean.get("REPLICATE_API_TOKEN") == "r8_authorized_token"

        # Explicit allow_ai_env=True override
        clean_override = CommandPolicy.sanitize_environment(
            base_env=base_env,
            target_script="scripts/custom_ai_call.py",
            allow_ai_env=True,
            is_production=True,
        )
        assert clean_override.get("OPENROUTER_API_KEY") == "sk-or-authorized-key"

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


class TestProjectLockCanonicalRootContainment:
    """Finding A Security Tests: Trusted Project Root & Canonical Containment."""

    def test_forged_projects_directory_outside_trusted_root_rejected(self, tmp_path: Path, isolated_db: dict):
        """A path with grandparent named 'projects' outside trusted canonical root is strictly rejected."""
        trusted_root = tmp_path / "projects"
        trusted_root.mkdir(parents=True, exist_ok=True)

        # Forged directory tree outside trusted root: /tmp/.../attacker/projects/ws_alpha/proj_forged
        forged_root = tmp_path / "attacker_controlled" / "projects"
        ws_id = "ws_alpha"
        proj_id = "proj_forged_01"
        forged_proj_dir = forged_root / ws_id / proj_id
        forged_proj_dir.mkdir(parents=True, exist_ok=True)

        # Register in database so caller claims registration
        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_victim", "victim@example.com")
        repo.create_workspace(ws_id, "Alpha Org", created_by="usr_victim")
        repo.create_project(proj_id, ws_id, "Forged Target", created_by="usr_victim")

        # Even with registered project and explicit workspace, forged path outside trusted root MUST fail closed
        with pytest.raises(TenantSecurityError, match="not verified to reside under trusted canonical projects root"):
            ProjectExecutionLock(
                project_dir=forged_proj_dir,
                owner_id="attacker_worker",
                db_path=isolated_db["db_path"],
                workspace_id=ws_id,
                base_dir=trusted_root,
            )

    def test_symlink_escape_outside_canonical_root_rejected(self, tmp_path: Path, isolated_db: dict):
        """Symlink pointing outside canonical projects root is strictly rejected with TenantSecurityError."""
        trusted_root = tmp_path / "projects"
        ws_id = "ws_symlink_org"
        proj_id = "proj_symlink_attack"

        # Create outside payload directory
        outside_dir = tmp_path / "outside_payload" / proj_id
        outside_dir.mkdir(parents=True, exist_ok=True)

        # Create symlink inside trusted root pointing to outside_dir
        ws_dir = trusted_root / ws_id
        ws_dir.mkdir(parents=True, exist_ok=True)
        symlink_proj = ws_dir / proj_id
        symlink_proj.symlink_to(outside_dir)

        # Register project
        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_sym", "sym@example.com")
        repo.create_workspace(ws_id, "Symlink Org", created_by="usr_sym")
        repo.create_project(proj_id, ws_id, "Symlink Video", created_by="usr_sym")

        with pytest.raises(TenantSecurityError, match="(escapes designated base boundary|Path confinement violation|not verified to reside under trusted canonical projects root)"):
            ProjectExecutionLock(
                project_dir=symlink_proj,
                owner_id="test_worker",
                db_path=isolated_db["db_path"],
                workspace_id=ws_id,
                base_dir=trusted_root,
            )

    def test_registered_project_at_noncanonical_location_rejected(self, tmp_path: Path, isolated_db: dict):
        """A registered project presented at a non-canonical location under trusted root is strictly rejected."""
        trusted_root = tmp_path / "projects"
        registered_ws = "ws_legit"
        wrong_ws = "ws_intruder"
        proj_id = "proj_misplaced_01"

        # Register in database under ws_legit
        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_legit", "legit@example.com")
        repo.create_workspace(registered_ws, "Legit Org", created_by="usr_legit")
        repo.create_workspace(wrong_ws, "Intruder Org", created_by="usr_legit")
        repo.create_project(proj_id, registered_ws, "Misplaced Target", created_by="usr_legit")

        # Create directory under wrong_ws
        wrong_proj_dir = trusted_root / wrong_ws / proj_id
        wrong_proj_dir.mkdir(parents=True, exist_ok=True)

        # When caller does not specify workspace, DB resolves ws_legit, but path is under ws_intruder -> conflict
        with pytest.raises(TenantSecurityError, match="Conflicting workspace identity"):
            ProjectExecutionLock(
                project_dir=wrong_proj_dir,
                owner_id="test_worker",
                db_path=isolated_db["db_path"],
                workspace_id=None,
                base_dir=trusted_root,
            )

    def test_authorized_test_workspace_operates_cleanly(self, tmp_path: Path, isolated_db: dict):
        """An authorized project under trusted root acquires and releases execution lock cleanly."""
        trusted_root = tmp_path / "projects"
        ws_id = "ws_clean_tenant"
        proj_id = "proj_clean_01"

        repo: TenantRepository = isolated_db["tenant_repo"]
        repo.create_user("usr_clean", "clean@example.com")
        repo.create_workspace(ws_id, "Clean Org", created_by="usr_clean")
        repo.create_project(proj_id, ws_id, "Clean Video", created_by="usr_clean")

        proj_dir = trusted_root / ws_id / proj_id
        proj_dir.mkdir(parents=True, exist_ok=True)

        lock = ProjectExecutionLock(
            project_dir=proj_dir,
            owner_id="worker_clean",
            run_id="run_clean_99",
            db_path=isolated_db["db_path"],
            workspace_id=ws_id,
            base_dir=trusted_root,
        )

        with lock:
            assert lock.workspace_id == ws_id
            active_lease = lock.repo.get_active_project_lease(proj_id)
            assert active_lease is not None
            assert active_lease["workspace_id"] == ws_id
