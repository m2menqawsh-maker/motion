"""
tests/security/test_certifi_cve_fixed.py
========================================
Verifies certifi is upgraded past version 2026.7.22 (vulnerable to PYSEC-2026-4320).
"""

from packaging.version import Version
import re
from pathlib import Path


def test_requirements_certifi_version_not_vulnerable():
    """Assert certifi version in requirements.txt >= 2026.10.19 to remediate PYSEC-2026-4320."""
    req_file = Path("requirements.txt")
    assert req_file.exists(), "requirements.txt must exist"
    content = req_file.read_text(encoding="utf-8")
    
    match = re.search(r"^certifi==([0-9\.]+)", content, re.MULTILINE)
    assert match is not None, "certifi must be explicitly pinned in requirements.txt"
    version_str = match.group(1)
    
    assert Version(version_str) >= Version("2026.10.19"), (
        f"certifi version {version_str} in requirements.txt is vulnerable to PYSEC-2026-4320. "
        "Upgrade to >= 2026.10.19 required."
    )
