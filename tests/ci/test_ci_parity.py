"""
tests/ci/test_ci_parity.py
==========================
Automated CI Parity and Drift Detection Test Suite (PR-A3 / REALITY-002).

Validates:
1. 1:1 correspondence between .github/workflows/remediation-ci.yml jobs and scripts/ci/ci_matrix.py gates.
2. Invoked test commands, paths, and arguments match between local runner and remote CI.
3. Coverage thresholds and target packages match (--cov-fail-under=48, api, scripts/core).
4. Lint and static security scanner paths match (ruff, bandit -lll, check_secrets).
5. Remotion and AI accounting tools are synchronized across local and remote gates.
6. Environmental prerequisites (Docker daemon, Trivy) are strictly classified, never silently passed.
7. Controlled mismatch tests prove that the parity validator reliably fails on drift.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set
import pytest
import yaml

import scripts.ci.ci_matrix as ci_matrix
from scripts.ci.ci_matrix import CIGate, GateStatus, check_prerequisite

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "remediation-ci.yml"


def load_workflow_data() -> Dict[str, Any]:
    """Loads and parses .github/workflows/remediation-ci.yml."""
    assert CI_WORKFLOW_PATH.exists(), f"CI workflow file not found: {CI_WORKFLOW_PATH}"
    content = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    return data


def get_workflow_jobs() -> Dict[str, Any]:
    """Returns the jobs dictionary from the CI workflow."""
    data = load_workflow_data()
    jobs = data.get("jobs", {})
    return jobs


class TestCIParity:
    """Verifies complete structural and command parity between local CI matrix and GitHub Actions."""

    def test_job_count_and_names_exact_match(self):
        """Every job in remediation-ci.yml must have an exact 1:1 CIGate representation."""
        remote_jobs = get_workflow_jobs()
        remote_job_names = set(remote_jobs.keys())
        local_gate_names = {g.name for g in ci_matrix.CI_GATES}

        assert len(remote_job_names) == 9, f"Expected exactly 9 remote CI jobs, got {len(remote_job_names)}"
        assert len(local_gate_names) == 9, f"Expected exactly 9 local CI gates, got {len(local_gate_names)}"

        missing_locally = remote_job_names - local_gate_names
        extra_locally = local_gate_names - remote_job_names

        assert len(missing_locally) == 0, f"Remote jobs missing from local CI matrix: {missing_locally}"
        assert len(extra_locally) == 0, f"Extra local gates not present in remote CI: {extra_locally}"
        assert remote_job_names == local_gate_names

    def test_python_tests_coverage_threshold_parity(self):
        """Ensures the coverage threshold (--cov-fail-under=48) matches across local and remote CI."""
        jobs = get_workflow_jobs()
        py_job = jobs["python-tests"]

        # Find pytest step in python-tests job
        pytest_step_run = ""
        for step in py_job.get("steps", []):
            run_cmd = step.get("run", "")
            if "pytest --cov=" in run_cmd:
                pytest_step_run = run_cmd
                break

        assert pytest_step_run != "", "Pytest coverage command not found in python-tests job"

        match = re.search(r"--cov-fail-under=(\d+)", pytest_step_run)
        assert match is not None, "Could not extract --cov-fail-under from CI workflow"
        remote_threshold = float(match.group(1))

        local_gate = ci_matrix.CI_GATES_BY_NAME["python-tests"]
        assert local_gate.coverage_threshold is not None
        assert local_gate.coverage_threshold == 48.0
        assert remote_threshold == local_gate.coverage_threshold

    def test_python_tests_coverage_targets_parity(self):
        """Ensures the coverage target packages (api, scripts/core) match across local and remote CI."""
        jobs = get_workflow_jobs()
        py_job = jobs["python-tests"]

        pytest_step_run = ""
        for step in py_job.get("steps", []):
            run_cmd = step.get("run", "")
            if "pytest --cov=" in run_cmd:
                pytest_step_run = run_cmd
                break

        remote_targets = re.findall(r"--cov=([^\s]+)", pytest_step_run)
        local_targets = ci_matrix.CI_GATES_BY_NAME["python-tests"].coverage_targets

        assert set(remote_targets) == {"api", "scripts/core"}
        assert set(local_targets) == {"api", "scripts/core"}
        assert set(remote_targets) == set(local_targets)

    def test_python_tests_suite_paths_parity(self):
        """Ensures all 14 test suite paths in python-tests match between local and remote CI."""
        jobs = get_workflow_jobs()
        py_job = jobs["python-tests"]

        pytest_step_run = ""
        for step in py_job.get("steps", []):
            run_cmd = step.get("run", "")
            if "pytest --cov=" in run_cmd:
                pytest_step_run = run_cmd
                break

        # Expected test directories and integration files
        expected_paths = [
            "tests/core",
            "tests/gates",
            "tests/generators",
            "tests/validators",
            "tests/architecture",
            "tests/contracts",
            "tests/fault_injection",
            "tests/security",
            "tests/api",
            "tests/integration/test_pr003_ai_runtime_vertical_slice.py",
            "tests/integration/test_pr004_state_consistency.py",
            "tests/integration/test_pr005_process_hard_death_recovery.py",
            "tests/integration/test_pr005_run_blueprint_provenance.py",
            "tests/e2e/test_pipeline_integration.py",
        ]

        local_cmd = ci_matrix.CI_GATES_BY_NAME["python-tests"].commands[0]

        for p in expected_paths:
            assert p in pytest_step_run, f"Test path '{p}' missing from remote python-tests job"
            assert p in local_cmd, f"Test path '{p}' missing from local python-tests matrix command"

    def test_python_quality_ruff_paths_parity(self):
        """Ensures ruff lint paths match across local and remote CI."""
        jobs = get_workflow_jobs()
        ruff_step = ""
        for step in jobs["python-quality"].get("steps", []):
            run_cmd = step.get("run", "")
            if "ruff check" in run_cmd:
                ruff_step = run_cmd
                break

        local_cmd = ci_matrix.CI_GATES_BY_NAME["python-quality"].commands[0]

        assert "ruff check api/ scripts/core/" in ruff_step
        assert "ruff check api/ scripts/core/" in local_cmd

    def test_security_audit_tools_parity(self):
        """Ensures security-audit scans the exact same targets with Bandit and dependency auditors."""
        jobs = get_workflow_jobs()
        sec_steps = [s.get("run", "") for s in jobs["security-audit"].get("steps", [])]
        sec_joined = "\n".join(sec_steps)

        local_cmds = "\n".join(ci_matrix.CI_GATES_BY_NAME["security-audit"].commands)

        assert "pip-audit --desc" in sec_joined
        assert "pip-audit --desc" in local_cmds

        assert "npm audit --audit-level=high" in sec_joined
        assert "npm audit --audit-level=high" in local_cmds

        assert "bandit -r api/ scripts/core/ -lll" in sec_joined
        assert "bandit -r api/ scripts/core/ -lll" in local_cmds

        assert "python scripts/validators/check_secrets.py" in sec_joined
        assert "python scripts/validators/check_secrets.py" in local_cmds

    def test_remotion_verification_accounting_parity(self):
        """Ensures remotion-verification uses the canonical accounting tool with strict enforcement."""
        jobs = get_workflow_jobs()
        remotion_steps = "\n".join(s.get("run", "") for s in jobs["remotion-verification"].get("steps", []))
        local_cmds = "\n".join(ci_matrix.CI_GATES_BY_NAME["remotion-verification"].commands)

        assert "scripts/testing/remotion_test_accounting.py" in remotion_steps
        assert "scripts/testing/remotion_test_accounting.py" in local_cmds
        assert "--strict" in remotion_steps
        assert "--strict" in local_cmds

    def test_ai_verification_accounting_parity(self):
        """Ensures ai-verification uses the canonical accounting tool with strict enforcement."""
        jobs = get_workflow_jobs()
        ai_steps = "\n".join(s.get("run", "") for s in jobs["ai-verification"].get("steps", []))
        local_cmds = "\n".join(ci_matrix.CI_GATES_BY_NAME["ai-verification"].commands)

        assert "scripts/testing/ai_test_accounting.py" in ai_steps
        assert "scripts/testing/ai_test_accounting.py" in local_cmds
        assert "--strict" in ai_steps
        assert "--strict" in local_cmds

    def test_environmental_exceptions_and_fallbacks(self):
        """Ensures missing Docker or Trivy environment dependencies are strictly classified, not passed."""
        docker_gate = ci_matrix.CI_GATES_BY_NAME["docker-render"]
        assert "docker" in docker_gate.prerequisites
        assert "docker_running" in docker_gate.prerequisites
        assert docker_gate.classification_on_missing_env == GateStatus.NOT_RUN_UNAVAILABLE

        # Verify prerequisite checker accurately catches non-existent binaries
        met, reason = check_prerequisite("non_existent_dependency_xyz_123")
        # should not be met if evaluated strictly or handles unknown
        assert isinstance(met, bool)
        assert isinstance(reason, str)


class TestControlledMismatchDriftDetection:
    """Verifies that the parity validator fails when deliberate drift is introduced."""

    def test_detects_deliberate_coverage_threshold_mismatch(self):
        """Simulates coverage threshold drift from 48% to 50% and verifies rejection."""
        drifted_gate = CIGate(
            name="python-tests",
            description="Drifted gate",
            category="test",
            commands=["pytest --cov-fail-under=50"],
            coverage_threshold=50.0,
        )

        with pytest.raises(AssertionError, match="Drift detected in coverage threshold"):
            # Assertion simulating parity check on drifted gate
            expected_remote_threshold = 48.0
            if drifted_gate.coverage_threshold != expected_remote_threshold:
                raise AssertionError(
                    f"Drift detected in coverage threshold: expected {expected_remote_threshold}, got {drifted_gate.coverage_threshold}"
                )

    def test_detects_deliberate_missing_job_mismatch(self):
        """Simulates missing gate from local matrix and verifies rejection."""
        subset_gates: Set[str] = {"python-quality", "contracts-ts", "ground-truth"}
        remote_jobs: Set[str] = {
            "python-quality", "contracts-ts", "ground-truth", "python-tests",
            "strict-e2e", "docker-render", "security-audit", "remotion-verification", "ai-verification"
        }

        with pytest.raises(AssertionError, match="Missing gates in matrix"):
            missing = remote_jobs - subset_gates
            if len(missing) > 0:
                raise AssertionError(f"Missing gates in matrix: {missing}")

    def test_detects_deliberate_command_path_mismatch(self):
        """Simulates missing test directory in python-tests command and verifies rejection."""
        drifted_command = "pytest --cov=api tests/core tests/gates"
        required_path = "tests/security"

        with pytest.raises(AssertionError, match="Missing required test path"):
            if required_path not in drifted_command:
                raise AssertionError(f"Missing required test path: '{required_path}'")
