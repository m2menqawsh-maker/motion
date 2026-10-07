"""
tests/architecture/test_s28_r12_architecture_guards.py
Pytest Architecture Enforcement for S28-R12: Multi-Engine RenderGraph & Planner Boundaries.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_contracts_layer_has_zero_planner_implementation_imports():
    """Verifies that all files in contracts/ have ZERO imports from planner/ implementation."""
    contracts_dir = REPO_ROOT / "contracts"

    for file_path in contracts_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        assert 'from "../planner' not in content, f"{file_path.name} must not import ../planner"
        assert 'from "./planner' not in content, f"{file_path.name} must not import ./planner"


def test_mutation_core_does_not_import_render_planner():
    """Verifies that mutation core and editor session do not import RenderPlanner or RenderGraph."""
    mut_file = REPO_ROOT / "contracts" / "mutations.ts"
    sess_file = REPO_ROOT / "contracts" / "editor-session.ts"

    m_content = mut_file.read_text(encoding="utf-8")
    s_content = sess_file.read_text(encoding="utf-8")

    assert "RenderPlanner" not in m_content
    assert "RenderGraph" not in m_content
    assert "RenderPlanner" not in s_content
    assert "RenderGraph" not in s_content


def test_template_spec_does_not_import_concrete_renderers():
    """Verifies that TemplateSpec and instantiator do not import concrete renderers."""
    spec_file = REPO_ROOT / "contracts" / "template-spec.ts"
    inst_file = REPO_ROOT / "contracts" / "template-instantiator.ts"

    sp_content = spec_file.read_text(encoding="utf-8")
    in_content = inst_file.read_text(encoding="utf-8")

    assert "remotion-renderer-adapter" not in sp_content
    assert "canvas-renderer-adapter" not in sp_content
    assert "remotion-renderer-adapter" not in in_content
    assert "canvas-renderer-adapter" not in in_content


def test_render_planner_has_zero_direct_rendering_or_bundler_imports():
    """Verifies that RenderPlanner does not import concrete bundler or renderer packages."""
    planner_file = REPO_ROOT / "planner" / "render-planner.ts"
    content = planner_file.read_text(encoding="utf-8")

    assert "@remotion/bundler" not in content
    assert "@remotion/renderer" not in content
    assert "canvas-renderer-adapter" not in content


def test_render_planner_has_zero_ffmpeg_imports():
    """Verifies that RenderPlanner has zero FFmpeg references."""
    planner_file = REPO_ROOT / "planner" / "render-planner.ts"
    content = planner_file.read_text(encoding="utf-8")

    assert "fluent-ffmpeg" not in content
    assert "@ffmpeg" not in content


def test_renderer_registry_has_zero_planning_policy():
    """Verifies that RendererRegistry in contracts/renderer.ts contains zero planning policy logic."""
    reg_file = REPO_ROOT / "contracts" / "renderer.ts"
    content = reg_file.read_text(encoding="utf-8")

    assert "RenderPlanner" not in content
    assert "PlanningPolicy" not in content
    assert "RenderGraph" not in content


def test_master_compositor_does_not_select_renderers():
    """Verifies that MasterCompositor does not contain renderer selection."""
    mc_file = REPO_ROOT / "compositor" / "master-compositor.ts"
    content = mc_file.read_text(encoding="utf-8")

    assert "selectRenderer" not in content
    assert "CANONICAL_RENDERER_REGISTRY" not in content


def test_render_graph_executor_does_not_mutate_canonical_documents():
    """Verifies that RenderGraphExecutor has zero mutation imports."""
    exec_file = REPO_ROOT / "planner" / "render-graph-executor.ts"
    content = exec_file.read_text(encoding="utf-8")

    assert "applyMutation" not in content
    assert "EditorSession" not in content
