"""
tests/architecture/test_s28_r11_architecture_guards.py
Pytest Architecture Enforcement for S28-R11: Master Compositor & Output Normalization Boundaries.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_contracts_layer_has_zero_ffmpeg_or_compositor_imports():
    """Verifies that all files in contracts/ have ZERO imports from ffmpeg packages or compositor implementation."""
    contracts_dir = REPO_ROOT / "contracts"
    forbidden = ["fluent-ffmpeg", "@ffmpeg", "canvas", "@napi-rs/canvas"]

    for file_path in contracts_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        for pkg in forbidden:
            assert f'from "{pkg}"' not in content, f"{file_path.name} must not import {pkg}"
            assert f"from '{pkg}'" not in content, f"{file_path.name} must not import {pkg}"

        # No importing compositor execution modules inside contracts
        assert 'from "../compositor"' not in content, f"{file_path.name} must not import ../compositor"
        assert 'from "./compositor/' not in content, f"{file_path.name} must not import implementation from compositor/"


def test_mutation_core_does_not_import_master_compositor():
    """Verifies that mutation core and editor session do not import MasterCompositor or compositor modules."""
    mut_file = REPO_ROOT / "contracts" / "mutations.ts"
    sess_file = REPO_ROOT / "contracts" / "editor-session.ts"

    m_content = mut_file.read_text(encoding="utf-8")
    s_content = sess_file.read_text(encoding="utf-8")

    assert "MasterCompositor" not in m_content
    assert "MasterCompositor" not in s_content


def test_template_spec_does_not_import_master_compositor():
    """Verifies that TemplateSpec core and instantiator do not import MasterCompositor."""
    spec_file = REPO_ROOT / "contracts" / "template-spec.ts"
    inst_file = REPO_ROOT / "contracts" / "template-instantiator.ts"

    sp_content = spec_file.read_text(encoding="utf-8")
    in_content = inst_file.read_text(encoding="utf-8")

    assert "MasterCompositor" not in sp_content
    assert "MasterCompositor" not in in_content


def test_renderer_registry_does_not_contain_composition_logic():
    """Verifies that RendererRegistry in contracts/renderer.ts contains zero composition logic."""
    reg_file = REPO_ROOT / "contracts" / "renderer.ts"
    content = reg_file.read_text(encoding="utf-8")

    assert "MasterCompositor" not in content
    assert "normalizeArtifactToSegment" not in content
    assert "assembleSceneSegments" not in content


def test_master_compositor_does_not_select_renderers():
    """Verifies that MasterCompositor does NOT select renderers (R12 boundary)."""
    mc_file = REPO_ROOT / "compositor" / "master-compositor.ts"
    content = mc_file.read_text(encoding="utf-8")

    assert "selectRenderer" not in content
    assert "CANONICAL_RENDERER_REGISTRY" not in content
    assert "RendererRegistry" not in content


def test_master_compositor_does_not_mutate_canonical_documents():
    """Verifies that MasterCompositor does NOT mutate documents directly."""
    mc_file = REPO_ROOT / "compositor" / "master-compositor.ts"
    content = mc_file.read_text(encoding="utf-8")

    assert "applyMutation" not in content
    assert "EditorSession" not in content


def test_intermediate_artifact_does_not_claim_canonical_authority():
    """Verifies that IntermediateArtifact in contracts/compositor.ts is an intermediate format, not Blueprint authority."""
    comp_file = REPO_ROOT / "contracts" / "compositor.ts"
    content = comp_file.read_text(encoding="utf-8")

    assert "IntermediateArtifact" in content
    assert "createIntermediateArtifact" in content
    assert "sourceRendererId" in content
    assert "contentFingerprint" in content
