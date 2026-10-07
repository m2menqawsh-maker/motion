"""
tests/architecture/test_s28_r10_architecture_guards.py
Pytest Architecture Enforcement for S28-R10: Canvas Headless Renderer Adapter & Multi-Renderer Isolation.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_contracts_layer_has_zero_canvas_or_ffmpeg_imports():
    """Verifies that all files in contracts/ have ZERO imports from canvas or ffmpeg packages."""
    contracts_dir = REPO_ROOT / "contracts"
    forbidden = ["fluent-ffmpeg", "@ffmpeg", "canvas", "@napi-rs/canvas"]

    for file_path in contracts_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        for pkg in forbidden:
            assert f'from "{pkg}"' not in content, f"{file_path.name} must not import {pkg}"
            assert f"from '{pkg}'" not in content, f"{file_path.name} must not import {pkg}"


def test_mutation_core_does_not_import_canvas_adapter():
    """Verifies that mutation core and editor session do not import CanvasRendererAdapter."""
    mut_file = REPO_ROOT / "contracts" / "mutations.ts"
    sess_file = REPO_ROOT / "contracts" / "editor-session.ts"

    m_content = mut_file.read_text(encoding="utf-8")
    s_content = sess_file.read_text(encoding="utf-8")

    assert "CanvasRendererAdapter" not in m_content
    assert "CanvasRendererAdapter" not in s_content


def test_template_spec_does_not_import_canvas_adapter():
    """Verifies that TemplateSpec core and instantiator do not import CanvasRendererAdapter."""
    spec_file = REPO_ROOT / "contracts" / "template-spec.ts"
    inst_file = REPO_ROOT / "contracts" / "template-instantiator.ts"

    sp_content = spec_file.read_text(encoding="utf-8")
    in_content = inst_file.read_text(encoding="utf-8")

    assert "CanvasRendererAdapter" not in sp_content
    assert "CanvasRendererAdapter" not in in_content


def test_preview_runtime_does_not_import_canvas_adapter():
    """Verifies that preview runtime does not import CanvasRendererAdapter."""
    preview_file = REPO_ROOT / "preview" / "preview-runtime.ts"
    content = preview_file.read_text(encoding="utf-8")

    assert "CanvasRendererAdapter" not in content


def test_canvas_adapter_exists_in_canvas_boundary_and_does_not_mutate():
    """Verifies canvas/canvas-renderer-adapter.ts exists, implements CanvasRendererAdapter, and does NOT mutate documents."""
    adapter_file = REPO_ROOT / "canvas" / "canvas-renderer-adapter.ts"
    assert adapter_file.is_file(), "canvas/canvas-renderer-adapter.ts must exist"

    content = adapter_file.read_text(encoding="utf-8")
    assert "class CanvasRendererAdapter" in content
    assert "export function createCanvasRendererAdapter" in content
    assert "export function registerCanvasRenderer" in content

    # Adapter must NOT mutate documents directly
    assert "applyMutation" not in content
    assert "EditorSession" not in content
