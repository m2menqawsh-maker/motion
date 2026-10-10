"""
scripts/ci/ci_matrix.py
=======================
Canonical verification matrix and shared gate definitions for MOTION CI (PR-A3).

Invariants:
- 1:1 structural correspondence between local gates and remote GitHub Actions jobs.
- Single source of truth for:
    * Gate identifiers (exact match to .github/workflows/remediation-ci.yml jobs)
    * Invoked test commands and file sets
    * Coverage thresholds (--cov-fail-under=48 for python-tests)
    * Covered paths (api, scripts/core)
    * Environmental prerequisites (Docker daemon, Trivy binary, xvfb)
    * Classification of missing environmental dependencies (NOT RUN / BLOCKED)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN_UNAVAILABLE = "NOT RUN / ENVIRONMENT UNAVAILABLE"
    SKIPPED = "SKIPPED"


def check_prerequisite(prereq: str) -> Tuple[bool, str]:
    """
    Evaluates whether an environmental prerequisite is met without direct subprocess calls.
    Conforms to SEC-DOC-001 subprocess security policy.
    """
    if prereq == "docker":
        if shutil.which("docker") is None:
            return False, "Docker CLI binary is not installed in PATH"
        return True, "Docker CLI installed"
    elif prereq == "docker_running":
        if shutil.which("docker") is None:
            return False, "Docker CLI not found"
        docker_sock = Path("/var/run/docker.sock")
        if not docker_sock.exists():
            return False, "Docker daemon socket (/var/run/docker.sock) is inaccessible or daemon not running"
        return True, "Docker daemon socket active"
    elif prereq == "xvfb":
        has_xvfb = shutil.which("xvfb-run") is not None
        return has_xvfb, "xvfb-run available" if has_xvfb else "xvfb-run not installed (fallback to headless)"
    elif prereq == "trivy":
        has_trivy = shutil.which("trivy") is not None
        return has_trivy, "Trivy binary installed" if has_trivy else "Trivy binary not found (remote GitHub Action gate)"
    return True, f"Prerequisite '{prereq}' satisfied"


@dataclass
class CIGate:
    name: str
    description: str
    category: str
    commands: List[str]
    env_vars: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None
    coverage_threshold: Optional[float] = None
    coverage_targets: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    classification_on_missing_env: GateStatus = GateStatus.NOT_RUN_UNAVAILABLE
    remote_only_steps: List[str] = field(default_factory=list)
    notes: str = ""


# Canonical list of the 9 required CI gates in execution sequence
CI_GATES: List[CIGate] = [
    CIGate(
        name="python-quality",
        description="Python static analysis and code quality verification (ruff)",
        category="lint",
        commands=[
            "ruff check api/ scripts/core/",
        ],
        notes="Enforces strict lint conformance on api/ and scripts/core/",
    ),
    CIGate(
        name="contracts-ts",
        description="TypeScript contracts, Remotion app linting and Vitest contract suite",
        category="typescript",
        commands=[
            "(cd remotion-app && npm run lint)",
            "(cd remotion-app && npx tsc --noEmit)",
            "npm test",
        ],
        notes="Verifies TypeScript contract typings and frontend component linting",
    ),
    CIGate(
        name="ground-truth",
        description="Ground truth synchronization and dependency lock",
        category="validation",
        commands=[
            "python scripts/validators/check_ground_truth_sync.py --check",
            "python scripts/validators/check_dependencies_lock.py --check",
        ],
        notes="Ensures ground-truth indices and dependency locks are synchronized",
    ),
    CIGate(
        name="python-tests",
        description="Core Python pytest test suite with mandatory 48% test coverage threshold",
        category="test",
        commands=[
            "pytest --cov=api --cov=scripts/core --cov-report=xml --cov-report=term --cov-fail-under=48 "
            "tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts "
            "tests/fault_injection tests/security tests/api "
            "tests/integration/test_pr003_ai_runtime_vertical_slice.py "
            "tests/integration/test_pr004_state_consistency.py "
            "tests/integration/test_pr005_process_hard_death_recovery.py "
            "tests/integration/test_pr005_run_blueprint_provenance.py "
            "tests/e2e/test_pipeline_integration.py",
        ],
        env_vars={"PYTHONPATH": ".", "TESTING": "1"},
        coverage_threshold=48.0,
        coverage_targets=["api", "scripts/core"],
        notes="Executes 840+ unit, security, fault injection, and API integration tests",
    ),
    CIGate(
        name="strict-e2e",
        description="True end-to-end rendering and pipeline execution without bypasses",
        category="e2e",
        commands=[
            "python tests/e2e/true_e2e_suite.py",
        ],
        env_vars={"PYTHONPATH": ".", "TESTING": "1"},
        notes="True end-to-end pipeline execution verifying all stages without mocks",
    ),
    CIGate(
        name="docker-render",
        description="Hermetic Docker container build and subcommand execution validation",
        category="container",
        commands=[
            "docker run --rm clean-video-builder npx remotion versions",
            "pytest tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py -v",
        ],
        env_vars={"PYTHONPATH": ".", "TESTING": "1"},
        prerequisites=["docker", "docker_running"],
        classification_on_missing_env=GateStatus.NOT_RUN_UNAVAILABLE,
        notes="Requires active Docker daemon. Missing daemon is reported as NOT RUN / UNAVAILABLE, not PASS",
    ),
    CIGate(
        name="security-audit",
        description="Python and Node dependency vulnerability audits, Bandit SAST, and secret scanning",
        category="security",
        commands=[
            "pip-audit --desc -r requirements.txt",
            "npm audit --audit-level=high",
            "(cd remotion-app && npm audit --audit-level=high)",
            "bandit -r api/ scripts/core/ -lll",
            "python scripts/validators/check_secrets.py",
        ],
        remote_only_steps=["trivy fs --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 --trivyignores .trivyignore ."],
        notes="Audits Python & Node dependencies, scans secrets, and executes Bandit SAST scanner",
    ),
    CIGate(
        name="remotion-verification",
        description="Remotion 49-file conformance verification, timing gates, and strict accounting",
        category="remotion",
        commands=[
            "python3 -c \"import glob, os, subprocess, sys; t2={'s28_r09_remotion_adapter.test.ts','s28_r10_canvas_adapter.test.ts','s28_r11_master_compositor.test.ts','s28_r12_render_planner.test.ts','s28_r14_production_integration.test.ts','s28_r15_destruction_and_load.test.ts','s28_r15_part3_final_campaigns.test.ts'}; all_f=sorted(glob.glob('tests/remotion/*.test.ts')); t1=[f for f in all_f if os.path.basename(f) not in t2]; sys.exit(subprocess.run(['npx','vitest','run',*t1,'--reporter=default','--reporter=json','--outputFile=/tmp/vitest_pr_a1_reports/tier1_report.json']).returncode)\"",
            "python3 -c \"import os, shutil, subprocess, sys; t2=['tests/remotion/s28_r09_remotion_adapter.test.ts','tests/remotion/s28_r10_canvas_adapter.test.ts','tests/remotion/s28_r11_master_compositor.test.ts','tests/remotion/s28_r12_render_planner.test.ts','tests/remotion/s28_r14_production_integration.test.ts','tests/remotion/s28_r15_destruction_and_load.test.ts','tests/remotion/s28_r15_part3_final_campaigns.test.ts']; cmd=['npx','vitest','run',*t2,'--no-file-parallelism','--maxConcurrency=1','--reporter=default','--reporter=json','--outputFile=/tmp/vitest_pr_a1_reports/tier2_report.json']; cmd=['xvfb-run','--auto-servernum']+cmd if shutil.which('xvfb-run') else cmd; sys.exit(subprocess.run(cmd).returncode)\"",
            "python3 scripts/testing/remotion_test_accounting.py --tier1-report /tmp/vitest_pr_a1_reports/tier1_report.json --tier2-report /tmp/vitest_pr_a1_reports/tier2_report.json --output /tmp/vitest_pr_a1_reports/accounting_summary.json --strict",
        ],
        notes="49 test files, 1545 tests, R12-04 and R12-13 timing gates",
    ),
    CIGate(
        name="ai-verification",
        description="AI platform 270-file suite (Tier 1 fast + Tier 2 heavy) with strict accounting",
        category="ai",
        commands=[
            "pytest tests/ai/ --ignore=tests/ai/candidates -o junit_family=xunit2 --junitxml=/tmp/ai_test_reports/tier1_junit.xml",
            "python3 -c \"import shutil, subprocess, sys; cmd=['pytest','tests/ai/candidates/','-o','junit_family=xunit2','--junitxml=/tmp/ai_test_reports/tier2_junit.xml']; cmd=['xvfb-run','--auto-servernum']+cmd if shutil.which('xvfb-run') else cmd; sys.exit(subprocess.run(cmd).returncode)\"",
            "python3 scripts/testing/ai_test_accounting.py --tier1-report /tmp/ai_test_reports/tier1_junit.xml --tier2-report /tmp/ai_test_reports/tier2_junit.xml --output /tmp/ai_test_reports/accounting_summary.json --strict",
        ],
        env_vars={"PYTHONPATH": ".", "TESTING": "1"},
        notes="270 test files, 1906 tests, zero omitted, complete disjoint partition",
    ),
]


CI_GATES_BY_NAME: Dict[str, CIGate] = {g.name: g for g in CI_GATES}


def main() -> None:
    """CLI interface to inspect gates and export matrix definitions."""
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("Usage: python3 -m scripts.ci.ci_matrix [--list | --get-gate <name> | --json]")
        sys.exit(0)

    arg = sys.argv[1]
    if arg == "--list":
        print("Available CI Gates in Canonical Matrix:")
        for idx, g in enumerate(CI_GATES, start=1):
            prereq_str = f" [prereqs: {', '.join(g.prerequisites)}]" if g.prerequisites else ""
            print(f"  {idx}. {g.name:<25} ({g.category}){prereq_str} — {g.description}")
    elif arg == "--get-gate":
        if len(sys.argv) < 3:
            print("Error: --get-gate requires a gate name argument", file=sys.stderr)
            sys.exit(1)
        name = sys.argv[2]
        gate = CI_GATES_BY_NAME.get(name)
        if not gate:
            print(f"Error: Unknown gate '{name}'", file=sys.stderr)
            sys.exit(1)
        gate_dict = asdict(gate)
        gate_dict["classification_on_missing_env"] = gate.classification_on_missing_env.value
        print(json.dumps(gate_dict, indent=2))
    elif arg == "--json":
        data = []
        for g in CI_GATES:
            d = asdict(g)
            d["classification_on_missing_env"] = g.classification_on_missing_env.value
            data.append(d)
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: Unknown argument '{arg}'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
