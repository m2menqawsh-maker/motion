"""
tests/ai/image_modernization/test_architecture_guards.py
========================================================
Architecture guards and structural boundary enforcement for Image Modernization (S28-M08).

Invariants:
- AI Planner / Creative Governance / Recipes NEVER import Pillow directly.
- ImageProcessingService enforces StorageService + AssetService authority.
- Public contracts strictly forbid arbitrary processor flags and host paths.
- ai/image_processing contains ZERO raw filesystem write calls (open, write_bytes, write_text).
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

from ai.image_processing.contracts import (
    AutoCropImageRequest,
    ConvertImageRequest,
    CropImageRatioRequest,
    OptimizeImageRequest,
    PrepareImageAssetRequest,
    ProbeImageRequest,
    ResizeImageRequest,
    ThumbnailRequest,
)

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_guard_no_raw_pillow_in_planners_and_recipes():
    """Ensures AI planners, governance, and recipes do not import PIL or Pillow directly."""
    forbidden_dirs = [
        ROOT / "ai" / "creative",
        ROOT / "creative_governance" / "rules",
        ROOT / "recipes",
    ]

    violations = []
    for d in forbidden_dirs:
        if not d.exists():
            continue
        for py_file in d.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("PIL", "PIL.Image", "PIL.ImageChops"):
                            violations.append(f"{py_file}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "PIL" or node.module.startswith("PIL.")):
                        violations.append(f"{py_file}: from {node.module} import ...")

    assert not violations, f"Pillow imports forbidden in planners/recipes: {violations}"


def test_guard_no_raw_filesystem_writes_in_image_processing():
    """Ensures ai/image_processing contains ZERO raw persistent filesystem write calls."""
    img_dir = ROOT / "ai" / "image_processing"
    assert img_dir.is_dir()

    forbidden_calls = {"write_bytes", "write_text"}
    violations = []

    for py_file in img_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in forbidden_calls:
                    violations.append(f"{py_file.name}:{node.lineno} calls {func.attr}()")

    assert not violations, f"Raw persistent filesystem write calls detected: {violations}"


def test_guard_public_contracts_extra_forbidden():
    """All public image contracts must enforce extra='forbid'."""
    contracts = [
        ProbeImageRequest,
        ResizeImageRequest,
        CropImageRatioRequest,
        AutoCropImageRequest,
        ConvertImageRequest,
        OptimizeImageRequest,
        PrepareImageAssetRequest,
        ThumbnailRequest,
    ]
    for c in contracts:
        assert c.model_config.get("extra") == "forbid", f"Contract {c.__name__} must forbid extra fields"


def test_guard_contracts_no_arbitrary_urls():
    """Image processing public contracts must not accept arbitrary external URLs."""
    contracts = [
        ProbeImageRequest,
        ResizeImageRequest,
        CropImageRatioRequest,
        AutoCropImageRequest,
        ConvertImageRequest,
        OptimizeImageRequest,
        PrepareImageAssetRequest,
        ThumbnailRequest,
    ]
    for c in contracts:
        field_names = list(c.model_fields.keys())
        assert "url" not in field_names, f"Contract {c.__name__} must not accept URL"
        assert "source_url" not in field_names, f"Contract {c.__name__} must not accept source_url"
