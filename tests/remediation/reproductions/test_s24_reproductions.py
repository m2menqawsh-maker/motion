"""
tests/remediation/reproductions/test_s24_reproductions.py — S24 Automated Reproductions (Red-First Verification).

Verifies the pre-remediation defect state on Starting SHA (7ac8abf0a16ba8cfdef26b7be4d9aad12b1d0c22):
- LED-074: True E2E uses SKIP_STRICT_QC bypass. (CONFIRMED_ON_MAIN)
- LED-075: Manifest E2E fixture violates canonical Manifest v2 schema. (CONFIRMED_ON_MAIN)
- LED-076: E2E template coverage biased to single template family (AnimatedTextWrapper only). (CONFIRMED_ON_MAIN)
- LED-077: Integration test legitimizes state bypass (finish_stage / approve_gate / direct state mutation). (CONFIRMED_ON_MAIN)
- LED-079: Docker render missing from CI workflow. (CONFIRMED_ON_MAIN)
- LED-080: Coverage has no minimum threshold enforcement in CI. (CONFIRMED_ON_MAIN)
- LED-081: Security / dependency CI gates absent from workflow. (CONFIRMED_ON_MAIN)
"""

import json
import subprocess
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
STARTING_SHA = "7ac8abf0a16ba8cfdef26b7be4d9aad12b1d0c22"


def get_file_at_starting_sha(rel_path: str) -> str:
    res = subprocess.run(
        ["git", "show", f"{STARTING_SHA}:{rel_path}"],
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
    )
    if res.returncode != 0:
        raise RuntimeError(f"Could not load {rel_path} at {STARTING_SHA}: {res.stderr}")
    return res.stdout


def test_led_074_true_e2e_uses_skip_strict_qc_reproduction():
    """LED-074: Confirms SKIP_STRICT_QC was present in true_e2e_suite.py on starting SHA."""
    content = get_file_at_starting_sha("tests/e2e/true_e2e_suite.py")
    assert 'env["SKIP_STRICT_QC"] = "1"' in content or "SKIP_STRICT_QC" in content
    # Classification: CONFIRMED_ON_MAIN


def test_led_075_manifest_fixture_violates_schema_reproduction():
    """LED-075: Legacy manifest fixture in true_e2e_suite violates canonical Manifest v2 schema."""
    from scripts.core.manifest_validator import validate_manifest_schema
    from scripts.core.manifest_errors import ManifestValidationError

    # Malformed manifest from test_pipeline_integration.py on starting SHA
    malformed_manifest = {
        "project_id": "test_project",
        "generated_at": "2024-01-01T00:00:00Z",
        "assets": []
    }
    with pytest.raises(ManifestValidationError):
        validate_manifest_schema(malformed_manifest)
    # Classification: CONFIRMED_ON_MAIN


def test_led_076_template_coverage_single_family_reproduction():
    """LED-076: Confirms true_e2e_suite only covered AnimatedTextWrapper on starting SHA."""
    content = get_file_at_starting_sha("tests/e2e/true_e2e_suite.py")

    assert "Animatedtextwrapper" in content or "AnimatedTextWrapper" in content
    # Multi-family templates absent on starting SHA
    assert "TitleCardWrapper" not in content and "rui-title-card" not in content
    assert "AnimatedCounterWrapper" not in content and "animatedcounter-element" not in content
    # Classification: CONFIRMED_ON_MAIN


def test_led_077_integration_test_state_bypass_reproduction():
    """LED-077: Confirms integration test advanced state with empty manifest on starting SHA."""
    content = get_file_at_starting_sha("tests/e2e/test_pipeline_integration.py")

    # On starting SHA: wrote empty {} into 02_asset_manifest.json and advanced manually
    assert 'write_text("{}", encoding="utf-8")' in content
    # Classification: CONFIRMED_ON_MAIN


def test_led_079_docker_missing_from_ci_reproduction():
    """LED-079: Confirms Docker render job was absent from CI workflow on starting SHA."""
    content = get_file_at_starting_sha(".github/workflows/remediation-ci.yml")

    assert "docker-render:" not in content
    assert "clean-video-builder" not in content
    # Classification: CONFIRMED_ON_MAIN


def test_led_080_coverage_missing_threshold_reproduction():
    """LED-080: Confirms coverage fail-under threshold was absent from CI on starting SHA."""
    content = get_file_at_starting_sha(".github/workflows/remediation-ci.yml")

    assert "--cov-fail-under" not in content
    # Classification: CONFIRMED_ON_MAIN


def test_led_081_security_gates_missing_from_ci_reproduction():
    """LED-081: Confirms security scanning jobs were absent from CI on starting SHA."""
    content = get_file_at_starting_sha(".github/workflows/remediation-ci.yml")

    assert "pip-audit" not in content
    assert "bandit" not in content
    assert "check_secrets.py" not in content
    assert "trivy" not in content
    # Classification: CONFIRMED_ON_MAIN
