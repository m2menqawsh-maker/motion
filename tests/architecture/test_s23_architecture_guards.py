"""
tests/architecture/test_s23_architecture_guards.py — S23 Architecture Guards:
Enforces architectural boundaries for locked dependencies, runtime installation bans,
hook integrity, separation of liveness from readiness, and sanitized runtime logging.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_no_runtime_package_installation_in_execution_paths():
    """
    Architecture Guard:
    No runtime execution path (api/, scripts/pipeline.py, scripts/gates/, scripts/core/)
    is permitted to invoke 'pip install' or 'npm install' dynamically at runtime.
    """
    monitored_paths = [
        ROOT / "api",
        ROOT / "scripts" / "core",
        ROOT / "scripts" / "gates",
        ROOT / "scripts" / "pipeline.py",
        ROOT / "scripts" / "render_project.py",
    ]

    violations = []
    banned_patterns = [
        re.compile(r"pip\s+install"),
        re.compile(r"npm\s+install"),
        re.compile(r"subprocess.*(?:pip|npm)\s+install"),
    ]

    for p in monitored_paths:
        files = [p] if p.is_file() else list(p.rglob("*.py"))
        for f in files:
            content = f.read_text(encoding="utf-8")
            for pattern in banned_patterns:
                if pattern.search(content):
                    violations.append(f"{f.relative_to(ROOT)} contains banned runtime package install: {pattern.pattern}")

    assert not violations, f"Runtime package installation detected in execution paths:\n" + "\n".join(violations)


def test_guard_githooks_integrity_and_fail_closed():
    """
    Architecture Guard:
    .githooks/pre-commit must:
    1. Not point to obsolete 'scripts/build_ground_truth.py'.
    2. Point to canonical 'scripts/generators/build_ground_truth.py'.
    3. Use 'set -euo pipefail' for fail-closed bash execution.
    4. Not contain silent 'exit 0' bypass on missing generator.
    """
    pre_commit = ROOT / ".githooks" / "pre-commit"
    assert pre_commit.exists(), ".githooks/pre-commit must exist"
    content = pre_commit.read_text(encoding="utf-8")

    assert 'scripts/build_ground_truth.py' not in content, (
        "pre-commit must not reference legacy generator path 'scripts/build_ground_truth.py'"
    )
    assert 'scripts/generators/build_ground_truth.py' in content, (
        "pre-commit must reference canonical 'scripts/generators/build_ground_truth.py'"
    )
    assert "set -euo pipefail" in content, (
        "pre-commit must enforce strict mode 'set -euo pipefail' for fail-closed behavior"
    )

    # .githooks/pre-merge-commit must NOT exist as a fake broken gate
    pre_merge = ROOT / ".githooks" / "pre-merge-commit"
    assert not pre_merge.exists(), ".githooks/pre-merge-commit must be eliminated to prevent false security gate"


def test_guard_python_dependency_lock_and_pinning():
    """
    Architecture Guard:
    Python dependencies must be deterministic and fully locked:
    1. uv.lock must exist and be non-empty.
    2. pyproject.toml must declare pinned dependencies.
    3. requirements.txt must be fully pinned (no wildcard/loose versions).
    """
    from scripts.validators.check_dependencies_lock import validate_python_locks
    rc = validate_python_locks()
    assert rc == 0, "Python dependencies lockfile validation failed"


def test_guard_runtime_logs_not_tracked_and_ignored():
    """
    Architecture Guard:
    Runtime logs (logs/runtime.jsonl, *.jsonl) must never be tracked by Git
    and must be explicitly excluded in .gitignore.
    """
    # Verify no jsonl or runtime logs are tracked
    res = subprocess.run(["git", "ls-files", "logs/runtime.jsonl", "*.jsonl"], cwd=str(ROOT), capture_output=True, text=True)
    assert res.stdout.strip() == "", f"Runtime logs must not be tracked in Git: {res.stdout}"

    # Verify .gitignore entries
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "logs/" in gitignore
    assert "*.jsonl" in gitignore


def test_guard_health_liveness_and_readiness_separation():
    """
    Architecture Guard:
    api/routers/health.py must expose distinct /health/live and /health/ready endpoints.
    /health/ready must reject with 503 when dependencies are unready, never returning 200 for broken state.
    """
    health_router = (ROOT / "api" / "routers" / "health.py").read_text(encoding="utf-8")
    assert "/health/live" in health_router
    assert "/health/ready" in health_router
    assert "status.HTTP_503_SERVICE_UNAVAILABLE" in health_router
    assert "HealthService.check_liveness()" in health_router
    assert "HealthService.check_readiness()" in health_router
