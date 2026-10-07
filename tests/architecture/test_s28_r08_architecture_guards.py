"""
tests/architecture/test_s28_r08_architecture_guards.py
Pytest Architecture Enforcement for S28-R08 Renderer Registry & Engine Decoupling.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_contracts_renderer_exists_and_is_engine_neutral():
    """Verifies contracts/renderer.ts exists and has ZERO imports from concrete renderer packages."""
    renderer_file = REPO_ROOT / "contracts" / "renderer.ts"
    assert renderer_file.is_file(), "contracts/renderer.ts must exist"

    content = renderer_file.read_text(encoding="utf-8")
    forbidden = ["remotion", "@remotion", "react", "fluent-ffmpeg", "@ffmpeg", "canvas", "three", "maplibre-gl"]
    for pkg in forbidden:
        assert f"from \"{pkg}\"" not in content, f"contracts/renderer.ts must not import {pkg}"
        assert f"from '{pkg}'" not in content, f"contracts/renderer.ts must not import {pkg}"


def test_mutation_core_does_not_import_renderer_registry():
    """Verifies mutation core does not import RendererRegistry."""
    mut_file = REPO_ROOT / "contracts" / "mutations.ts"
    sess_file = REPO_ROOT / "contracts" / "editor-session.ts"

    assert mut_file.is_file()
    assert sess_file.is_file()

    m_content = mut_file.read_text(encoding="utf-8")
    s_content = sess_file.read_text(encoding="utf-8")

    assert "RendererRegistry" not in m_content
    assert "RendererRegistry" not in s_content


def test_renderer_registry_does_not_mutate_documents():
    """Verifies contracts/renderer.ts does not import document mutation logic."""
    renderer_file = REPO_ROOT / "contracts" / "renderer.ts"
    content = renderer_file.read_text(encoding="utf-8")

    assert "applyMutation" not in content
    assert "EditorSession" not in content


def test_single_renderer_authority_invariant():
    """Verifies CANONICAL_RENDERER_REGISTRY is defined as single authority."""
    renderer_file = REPO_ROOT / "contracts" / "renderer.ts"
    content = renderer_file.read_text(encoding="utf-8")

    assert "export const CANONICAL_RENDERER_REGISTRY" in content
    assert "class RendererRegistry" in content
