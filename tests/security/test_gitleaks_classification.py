import os
import subprocess
from pathlib import Path
import pytest


def test_gitleaksignore_exists_and_covers_false_positives():
    """
    Verifies that .gitleaksignore is present, populated with fingerprints,
    and has documented commentary explaining the false-positive classifications.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    ignore_file = repo_root / ".gitleaksignore"

    assert ignore_file.exists(), ".gitleaksignore file is missing from repository root"
    content = ignore_file.read_text(encoding="utf-8")

    # Verify key commentary exists explaining false-positive categories
    assert "Synthetic Test Fixtures" in content or "false-positive" in content
    assert "generic-api-key" in content
    assert ".pyc" not in content, ".pyc entries should not be in .gitleaksignore"

    # Verify non-empty fingerprints
    fingerprints = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(fingerprints) >= 27, f"Expected at least 27 ignored fingerprints, found {len(fingerprints)}"


def test_gitleaks_detect_returns_zero_exit_code():
    """
    Verifies that `gitleaks detect --no-banner` runs cleanly and reports no leaks.
    Skips cleanly if gitleaks binary is not installed in the execution environment.
    """
    import shutil
    if not shutil.which("gitleaks"):
        pytest.skip("gitleaks binary not found in PATH; skipping test")

    repo_root = Path(__file__).resolve().parent.parent.parent
    res = subprocess.run(
        ["gitleaks", "detect", "--no-banner", "--redact"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"gitleaks detect failed with code {res.returncode}: {res.stderr}\n{res.stdout}"
    combined = res.stdout + res.stderr
    assert "no leaks found" in combined.lower(), f"Expected 'no leaks found', got: {combined}"
