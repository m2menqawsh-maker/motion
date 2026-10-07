"""
tests/architecture/test_s28_r09_architecture_guards.py
Pytest Architecture Enforcement for S28-R09: Remotion Renderer Adapter Decoupling.
"""
from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_contracts_layer_has_zero_remotion_imports():
    """Verifies that all files in contracts/ have ZERO imports from Remotion or React."""
    contracts_dir = REPO_ROOT / "contracts"
    forbidden = ["remotion", "@remotion", "react", "fluent-ffmpeg", "@ffmpeg"]

    for file_path in contracts_dir.glob("*.ts"):
        content = file_path.read_text(encoding="utf-8")
        for pkg in forbidden:
            assert f'from "{pkg}"' not in content, f"{file_path.name} must not import {pkg}"
            assert f"from '{pkg}'" not in content, f"{file_path.name} must not import {pkg}"


def test_mutation_core_does_not_import_remotion_adapter():
    """Verifies that mutation core does not import RemotionRendererAdapter."""
    mut_file = REPO_ROOT / "contracts" / "mutations.ts"
    sess_file = REPO_ROOT / "contracts" / "editor-session.ts"

    m_content = mut_file.read_text(encoding="utf-8")
    s_content = sess_file.read_text(encoding="utf-8")

    assert "RemotionRendererAdapter" not in m_content
    assert "RemotionRendererAdapter" not in s_content


def test_preview_runtime_does_not_import_remotion_adapter():
    """Verifies that preview runtime does not import RemotionRendererAdapter."""
    preview_file = REPO_ROOT / "preview" / "preview-runtime.ts"
    content = preview_file.read_text(encoding="utf-8")

    assert "RemotionRendererAdapter" not in content
    assert "from 'remotion'" not in content
    assert 'from "remotion"' not in content


def test_remotion_adapter_exists_in_remotion_boundary():
    """Verifies remotion/remotion-renderer-adapter.ts exists and implements RemotionRendererAdapter."""
    adapter_file = REPO_ROOT / "remotion" / "remotion-renderer-adapter.ts"
    assert adapter_file.is_file(), "remotion/remotion-renderer-adapter.ts must exist"

    content = adapter_file.read_text(encoding="utf-8")
    assert "class RemotionRendererAdapter" in content
    assert "export function createRemotionRendererAdapter" in content
    assert "export function registerRemotionRenderer" in content

    # Adapter must NOT mutate documents directly
    assert "applyMutation" not in content
    assert "EditorSession" not in content
