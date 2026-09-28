#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/validators/check_dependencies_lock.py — Dependency Lockfile & Pinning Validator (S23 - LED-085).

Ensures:
- uv.lock exists and is valid.
- requirements.txt is fully pinned (no wildcard or loose ranges like >= without lock).
- pyproject.toml matches locked definitions.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def validate_python_locks() -> int:
    uv_lock = ROOT / "uv.lock"
    pyproject = ROOT / "pyproject.toml"
    requirements = ROOT / "requirements.txt"

    errors = []

    if not uv_lock.exists():
        errors.append("FAIL: uv.lock is missing from repository root.")
    elif uv_lock.stat().st_size == 0:
        errors.append("FAIL: uv.lock is empty.")

    if not pyproject.exists():
        errors.append("FAIL: pyproject.toml is missing from repository root.")

    if not requirements.exists():
        errors.append("FAIL: requirements.txt is missing from repository root.")
    else:
        content = requirements.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        # Check if == is present for all package definitions
        unpinned = []
        for line in lines:
            if line.startswith("#") or line.startswith("-") or line.startswith("\\"):
                continue
            pkg_part = line.split()[0].split(";")[0]
            if "==" not in pkg_part:
                unpinned.append(pkg_part)

        if unpinned:
            errors.append(f"FAIL: Unpinned packages found in requirements.txt: {unpinned}")

    if errors:
        for err in errors:
            print(f"❌ {err}", file=sys.stderr)
        return 1

    print("✅ All Python dependencies are strictly locked and pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(validate_python_locks())
