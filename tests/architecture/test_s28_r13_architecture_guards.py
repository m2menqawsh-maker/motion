"""
tests/architecture/test_s28_r13_architecture_guards.py
Pytest Architecture Enforcement for S28-R13: Unified Authoring Boundaries.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_authoring_layer_has_zero_remotion_imports():
    """Verifies that authoring/ has ZERO imports from Remotion."""
    authoring_dir = REPO_ROOT / "authoring"
    for file_path in authoring_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        assert "@remotion" not in content, f"{file_path.name} must not import @remotion"
        assert "remotion-renderer-adapter" not in content, f"{file_path.name} must not import remotion adapter"


def test_authoring_layer_has_zero_canvas_adapter_imports():
    """Verifies that authoring/ has ZERO imports from canvas-renderer-adapter."""
    authoring_dir = REPO_ROOT / "authoring"
    for file_path in authoring_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        assert "canvas-renderer-adapter" not in content, f"{file_path.name} must not import canvas adapter"


def test_authoring_layer_has_zero_ffmpeg_imports():
    """Verifies that authoring/ has ZERO imports from ffmpeg or direct spawns."""
    authoring_dir = REPO_ROOT / "authoring"
    for file_path in authoring_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        assert "fluent-ffmpeg" not in content, f"{file_path.name} must not import fluent-ffmpeg"
        assert "@ffmpeg" not in content, f"{file_path.name} must not import @ffmpeg"


def test_authoring_layer_has_zero_render_planner_imports():
    """Verifies that authoring/ does not import RenderPlanner or selectRenderer."""
    authoring_dir = REPO_ROOT / "authoring"
    for file_path in authoring_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        assert "RenderPlanner" not in content, f"{file_path.name} must not import RenderPlanner"
        assert "selectRenderer" not in content, f"{file_path.name} must not call selectRenderer"


def test_authoring_and_contracts_have_zero_ai_vendor_sdks():
    """Verifies that contracts/ and authoring/ do not import vendor AI SDKs."""
    target_dirs = [REPO_ROOT / "contracts", REPO_ROOT / "authoring"]
    forbidden_sdks = ["openai", "@anthropic-ai", "@google/generative-ai", "langchain"]

    for d in target_dirs:
        for file_path in d.glob("*.ts"):
            content = file_path.read_text(encoding="utf-8")
            for sdk in forbidden_sdks:
                assert sdk not in content, f"{file_path.name} must not import {sdk}"


def test_creative_plan_does_not_import_renderers():
    """Verifies that CreativePlan contracts in Python do not import renderers."""
    creative_plan_file = REPO_ROOT / "ai" / "contracts" / "creative" / "plan.py"
    if creative_plan_file.exists():
        content = creative_plan_file.read_text(encoding="utf-8")
        assert "remotion" not in content.lower(), "CreativePlan must not import remotion"
        assert "ffmpeg" not in content.lower(), "CreativePlan must not import ffmpeg"
