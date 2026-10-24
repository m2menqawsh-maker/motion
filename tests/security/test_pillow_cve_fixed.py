"""
tests/security/test_pillow_cve_fixed.py
======================================
Verifies Pillow is upgraded past versions vulnerable to CVE-2026-112895 and CVE-2026-112400.
"""

import importlib.metadata
from packaging.version import Version


def test_pillow_version_not_vulnerable():
    """Assert Pillow version >= 13.0.0 to remediate CVE-2026-112895 and CVE-2026-112400."""
    version_str = importlib.metadata.version("pillow")
    assert Version(version_str) >= Version("13.0.0"), (
        f"Pillow version {version_str} is vulnerable to CVE-2026-112895 and CVE-2026-112400. "
        "Upgrade to >= 13.0.0 required."
    )
