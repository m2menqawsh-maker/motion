"""
tests/architecture/test_s24_architecture_guards.py — Architecture Guards for S24
Enforces strict CI production gates, true E2E guarantees, multi-family template matrix,
canonical factory fixtures, Docker hermeticity, coverage threshold, and security scans.
"""

import ast
import re
import yaml
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

def test_guard_led_074_no_skip_strict_qc_in_e2e_or_ci():
    """LED-074 Guard: SKIP_STRICT_QC must be completely absent from E2E and CI workflows."""
    e2e_file = WORKSPACE_ROOT / "tests" / "e2e" / "true_e2e_suite.py"
    ci_file = WORKSPACE_ROOT / ".github" / "workflows" / "remediation-ci.yml"

    e2e_content = e2e_file.read_text(encoding="utf-8")
    assert "SKIP_STRICT_QC" not in e2e_content, "true_e2e_suite.py must not contain SKIP_STRICT_QC"

    ci_content = ci_file.read_text(encoding="utf-8")
    assert "SKIP_STRICT_QC" not in ci_content, "remediation-ci.yml must not contain SKIP_STRICT_QC"

    # Also check pipeline code
    pipeline_file = WORKSPACE_ROOT / "scripts" / "pipeline.py"
    assert "SKIP_STRICT_QC" not in pipeline_file.read_text(encoding="utf-8")


def test_guard_led_075_canonical_manifest_factory():
    """LED-075 Guard: Manifest fixtures must be generated canonically via canonical_factory."""
    factory_file = WORKSPACE_ROOT / "tests" / "factories" / "canonical_factory.py"
    assert factory_file.exists(), "canonical_factory.py must exist"

    from tests.factories.canonical_factory import create_canonical_manifest
    manifest = create_canonical_manifest("prj_test_guard")
    assert manifest["manifest_version"] == "2.0.0"
    assert "assets" in manifest
    assert isinstance(manifest["assets"], list)

    # Legacy malformed empty dict fixtures must not be present in true_e2e_suite
    e2e_content = (WORKSPACE_ROOT / "tests" / "e2e" / "true_e2e_suite.py").read_text(encoding="utf-8")
    assert 'write_text("{}", encoding="utf-8")' not in e2e_content


def test_guard_led_076_multi_family_template_matrix():
    """LED-076 Guard: E2E suite must represent multiple template families and aspects."""
    e2e_content = (WORKSPACE_ROOT / "tests" / "e2e" / "true_e2e_suite.py").read_text(encoding="utf-8")

    # At least 3 different templates from different families
    assert "animatedtext-element" in e2e_content
    assert "animatedcounter-element" in e2e_content
    assert "rui-title-card" in e2e_content

    # Representative aspect ratio matrix
    assert "16:9" in e2e_content
    assert "9:16" in e2e_content
    assert "1:1" in e2e_content

    # Negative defect scenario must be present
    assert "run_negative_qc_scenario" in e2e_content
    assert "run_unknown_template_negative_scenario" in e2e_content


def test_guard_led_077_no_state_bypass_in_integration_tests():
    """LED-077 Guard: Integration tests must not use finish_stage or direct state mutations."""
    integration_file = WORKSPACE_ROOT / "tests" / "e2e" / "test_pipeline_integration.py"
    content = integration_file.read_text(encoding="utf-8")

    # Direct manual transition calls in test flow are forbidden
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for direct calls to LifecycleService.transition
            if isinstance(node.func, ast.Attribute) and node.func.attr == "transition":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "LifecycleService":
                    pytest.fail("test_pipeline_integration.py must not call LifecycleService.transition directly")

    # Happy path must use ReviewService and PipelineService.run_pipeline
    assert "ReviewService" in content
    assert "PipelineService.run_pipeline" in content
    assert "PipelineService.approve_gate" in content


def test_guard_led_079_docker_render_ci_job_and_hermetic_context():
    """LED-079 Guard: CI must include a dedicated docker-render job and hermetic context."""
    dockerfile = WORKSPACE_ROOT / ".agents" / "docker" / "Dockerfile.remotion"
    assert dockerfile.exists(), "Dockerfile.remotion must exist"

    dockerignore = WORKSPACE_ROOT / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore must exist"
    dockerignore_content = dockerignore.read_text(encoding="utf-8")
    assert "node_modules" in dockerignore_content
    assert "remotion-app/node_modules" in dockerignore_content

    ci_file = WORKSPACE_ROOT / ".github" / "workflows" / "remediation-ci.yml"
    ci_content = ci_file.read_text(encoding="utf-8")
    assert "docker-render:" in ci_content
    assert "clean-video-builder" in ci_content
    assert "continue-on-error: true" not in ci_content


def test_guard_led_080_coverage_threshold_and_ci_enforcement():
    """LED-080 Guard: pyproject.toml and CI must enforce a minimum coverage threshold."""
    pyproject_file = WORKSPACE_ROOT / "pyproject.toml"
    content = pyproject_file.read_text(encoding="utf-8")

    assert "[tool.coverage.report]" in content
    assert "fail_under" in content

    ci_file = WORKSPACE_ROOT / ".github" / "workflows" / "remediation-ci.yml"
    ci_content = ci_file.read_text(encoding="utf-8")
    assert "--cov-fail-under" in ci_content
    assert "python-coverage" in ci_content


def test_guard_led_081_security_audits_and_severity_policy():
    """LED-081 Guard: CI must run pip-audit, npm-audit, bandit, secret scan with fail-closed semantics."""
    ci_file = WORKSPACE_ROOT / ".github" / "workflows" / "remediation-ci.yml"
    ci_content = ci_file.read_text(encoding="utf-8")

    assert "security-audit:" in ci_content
    assert "pip-audit" in ci_content
    assert "npm audit" in ci_content
    assert "bandit" in ci_content
    assert "check_secrets.py" in ci_content
    assert "trivy" in ci_content

    # Strict ban on swallows and continue-on-error
    assert "|| true" not in ci_content
    assert "continue-on-error: true" not in ci_content

    secret_scanner = WORKSPACE_ROOT / "scripts" / "validators" / "check_secrets.py"
    assert secret_scanner.exists(), "check_secrets.py must exist"
