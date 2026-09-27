"""Unit tests for S01 Security Scaffolding contracts."""

import sys
import pytest
from pathlib import Path
from pydantic import ValidationError

from scripts.core.security import (
    Principal,
    PrincipalType,
    Role,
    Action,
    create_anonymous_principal,
    create_system_principal,
    AuthorizationPolicy,
    AccessDeniedError,
    AuthenticationRequiredError,
    CommandPolicy,
    CommandSecurityViolation,
    EnvironmentPolicyAuditor,
    EnvironmentType,
    SecuritySettings,
)


class TestPrincipalModel:
    def test_anonymous_principal(self):
        anon = create_anonymous_principal()
        assert not anon.is_authenticated
        assert anon.principal_type == PrincipalType.ANONYMOUS
        assert not anon.is_human
        assert not anon.is_admin
        assert len(anon.get_roles_for_project("any_project")) == 0

    def test_human_principal_roles(self):
        user = Principal(
            principal_id="usr_123",
            principal_type=PrincipalType.HUMAN,
            roles={Role.VIEWER},
            project_scopes={
                "proj_alpha": {Role.EDITOR},
                "proj_beta": {Role.REVIEWER},
            }
        )
        assert user.is_authenticated
        assert user.is_human
        assert not user.is_admin

        # Global role applies everywhere
        assert user.has_role(Role.VIEWER, "proj_gamma")
        # Project alpha has EDITOR
        assert user.has_role(Role.EDITOR, "proj_alpha")
        assert not user.has_role(Role.REVIEWER, "proj_alpha")
        # Project beta has REVIEWER
        assert user.has_role(Role.REVIEWER, "proj_beta")
        assert not user.has_role(Role.EDITOR, "proj_beta")

    def test_admin_principal_inherits_all_roles(self):
        admin = Principal(
            principal_id="adm_001",
            principal_type=PrincipalType.HUMAN,
            roles={Role.ADMIN}
        )
        assert admin.is_admin
        for role in Role:
            assert admin.has_role(role, "any_project")

    def test_system_principal(self):
        worker = create_system_principal("transcoder")
        assert worker.is_authenticated
        assert worker.is_service
        assert worker.has_role(Role.OPERATOR)


class TestAuthorizationPolicy:
    def test_unauthenticated_request_rejected(self):
        anon = create_anonymous_principal()
        assert not AuthorizationPolicy.is_authorized(anon, Action.PROJECT_READ, "proj_1")
        with pytest.raises(AuthenticationRequiredError):
            AuthorizationPolicy.enforce(anon, Action.PROJECT_READ, "proj_1")

    def test_editor_cannot_approve_review(self):
        editor = Principal(
            principal_id="usr_editor",
            principal_type=PrincipalType.HUMAN,
            roles=set(),
            project_scopes={"proj_1": {Role.EDITOR}}
        )
        # Editor can edit blueprint
        assert AuthorizationPolicy.is_authorized(editor, Action.BLUEPRINT_EDIT, "proj_1")
        # Editor CANNOT approve review
        assert not AuthorizationPolicy.is_authorized(editor, Action.REVIEW_APPROVE, "proj_1")
        with pytest.raises(AccessDeniedError):
            AuthorizationPolicy.enforce(editor, Action.REVIEW_APPROVE, "proj_1")

    def test_reviewer_can_approve_review(self):
        reviewer = Principal(
            principal_id="usr_reviewer",
            principal_type=PrincipalType.HUMAN,
            roles=set(),
            project_scopes={"proj_1": {Role.REVIEWER}}
        )
        assert AuthorizationPolicy.is_authorized(reviewer, Action.REVIEW_APPROVE, "proj_1")
        assert AuthorizationPolicy.is_authorized(reviewer, Action.REVIEW_REJECT, "proj_1")
        # Reviewer cannot edit blueprint
        assert not AuthorizationPolicy.is_authorized(reviewer, Action.BLUEPRINT_EDIT, "proj_1")

    def test_project_isolation(self):
        user = Principal(
            principal_id="usr_scoped",
            principal_type=PrincipalType.HUMAN,
            roles=set(),
            project_scopes={"proj_allowed": {Role.EDITOR}}
        )
        assert AuthorizationPolicy.is_authorized(user, Action.PROJECT_READ, "proj_allowed")
        assert not AuthorizationPolicy.is_authorized(user, Action.PROJECT_READ, "proj_forbidden")


class TestCommandPolicy:
    def test_canonical_python_resolution_disc_004(self):
        cmd = ["python", "scripts/pipeline.py", "my_proj"]
        res = CommandPolicy.validate_command(cmd)
        assert res.is_allowed
        # Must resolve to sys.executable and not bare "python"
        assert res.sanitized_cmd[0] == str(Path(sys.executable).resolve())

    def test_unregistered_python_script_rejected(self):
        cmd = ["python", "scripts/evil_unregistered.py"]
        res = CommandPolicy.validate_command(cmd)
        assert not res.is_allowed
        assert any("not in the allowed scripts registry" in v for v in res.violations)

    def test_dangerous_flag_c_rejected(self):
        cmd = ["python", "-c", "import os; os.system('id')"]
        res = CommandPolicy.validate_command(cmd)
        assert not res.is_allowed
        assert any("Dangerous flag '-c'" in v for v in res.violations)

    def test_python_m_allowed_module(self):
        cmd = ["python", "-m", "pytest", "tests/"]
        res = CommandPolicy.validate_command(cmd)
        assert res.is_allowed
        assert res.subcommand == "-m pytest"

    def test_python_m_unregistered_module_rejected(self):
        cmd = ["python", "-m", "http.server", "8080"]
        res = CommandPolicy.validate_command(cmd)
        assert not res.is_allowed
        assert any("Python module '-m http.server' is not in the allowed modules registry" in v for v in res.violations)

    def test_node_eval_rejected(self):
        cmd = ["npm", "run", "build", "--eval", "console.log(process.env)"]
        res = CommandPolicy.validate_command(cmd)
        assert not res.is_allowed
        assert any("Node flag '--eval'" in v for v in res.violations)

    def test_docker_subcommand_validation(self):
        # docker run clean-video-builder is allowed
        res_run = CommandPolicy.validate_command(["docker", "run", "--rm", "clean-video-builder"])
        assert res_run.is_allowed

        # docker exec is rejected
        res_exec = CommandPolicy.validate_command(["docker", "exec", "-it", "my_container", "bash"])
        assert not res_exec.is_allowed
        assert any("Docker subcommand 'exec' is forbidden" in v for v in res_exec.violations)

        # docker --privileged is rejected
        res_priv = CommandPolicy.validate_command(["docker", "run", "--privileged", "clean-video-builder"])
        assert not res_priv.is_allowed
        assert any("Docker --privileged is forbidden" in v for v in res_priv.violations)

    def test_environment_sanitization_strips_bypass_vars_in_production(self):
        dirty_env = {
            "PATH": "/usr/bin",
            "SKIP_STRICT_QC": "1",
            "AGY_IS_MANAGED": "1",
            "OPENAI_API_KEY": "sk-secret",
            "EVIL_INJECTED_VAR": "malicious",
        }
        clean = CommandPolicy.sanitize_environment(dirty_env, is_production=True)
        assert "SKIP_STRICT_QC" not in clean
        assert "AGY_IS_MANAGED" not in clean
        assert "EVIL_INJECTED_VAR" not in clean
        assert clean.get("OPENAI_API_KEY") == "sk-secret"


class TestEnvironmentPolicyAuditor:
    def test_detects_forbidden_vars_in_production(self):
        env = {
            "SKIP_STRICT_QC": "1",
            "AGY_IS_MANAGED": "1",
            "MOTION_ENV": "production",
        }
        violations = EnvironmentPolicyAuditor.audit_environment(env, target_env="production")
        assert len(violations) == 2
        assert any("SKIP_STRICT_QC" in v for v in violations)
        assert any("AGY_IS_MANAGED" in v for v in violations)

    def test_allows_in_test_environment(self):
        env = {
            "SKIP_STRICT_QC": "1",
            "AGY_IS_MANAGED": "1",
            "TESTING": "1",
        }
        violations = EnvironmentPolicyAuditor.audit_environment(env, target_env="test")
        assert len(violations) == 0


class TestSecuritySettingsSchema:
    def test_production_rejects_anonymous_access(self):
        with pytest.raises(ValidationError, match="allow_anonymous cannot be True in PRODUCTION"):
            SecuritySettings(
                env=EnvironmentType.PRODUCTION,
                allow_anonymous=True,
                enforce_strict_qc=True,
                enforce_studio_approval=True
            )

    def test_production_rejects_qc_bypass(self):
        with pytest.raises(ValidationError, match="enforce_strict_qc cannot be disabled in PRODUCTION"):
            SecuritySettings(
                env=EnvironmentType.PRODUCTION,
                allow_anonymous=False,
                enforce_strict_qc=False,
                enforce_studio_approval=True
            )

    def test_production_rejects_approval_bypass(self):
        with pytest.raises(ValidationError, match="enforce_studio_approval cannot be disabled in PRODUCTION"):
            SecuritySettings(
                env=EnvironmentType.PRODUCTION,
                allow_anonymous=False,
                enforce_strict_qc=True,
                enforce_studio_approval=False
            )
