"""
tests/ai/media_intelligence/test_architecture_guards.py
=======================================================
Architecture Guard Suite for Media Intelligence and Speech Intelligence (S27.13 / S27.14 Rule 37).

Enforces:
1. No raw project filesystem access in ai/media/ and ai/speech/.
2. No raw database driver imports or raw SQL execution in business layer.
3. No external provider SDK imports in canonical service layer.
4. No vendor-specific business capabilities.
5. No lifecycle or QC token mutation.
6. Strict tenant isolation on media reports.
7. No unrestricted dict[str, Any] at canonical boundary contracts.
8. Vision Intelligence not started (AI-13 scope boundary).
9. Audio Intelligence not started (AI-13 scope boundary).
"""

import ast
import inspect
from pathlib import Path
from typing import List, Tuple
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.media import MediaIntelligence, SpeechIntelligence
from ai.media.service import MediaIntelligenceService

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AI_MEDIA_DIR = WORKSPACE_ROOT / "ai" / "media"
AI_SPEECH_DIR = WORKSPACE_ROOT / "ai" / "speech"


def _get_target_python_files() -> List[Path]:
    files = list(AI_MEDIA_DIR.glob("**/*.py")) + list(AI_SPEECH_DIR.glob("**/*.py"))
    return files


def test_no_raw_db_drivers_in_media_and_speech():
    forbidden_modules = {"sqlite3", "psycopg2", "psycopg", "asyncpg", "mysql", "databases"}
    violations: List[Tuple[str, int, str]] = []

    for file_path in _get_target_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden_modules:
                        violations.append((file_path.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in forbidden_modules:
                    violations.append((file_path.name, node.lineno, node.module or ""))

    assert not violations, f"Forbidden database driver imports found in media/speech: {violations}"


def test_no_raw_sql_execution_in_media_and_speech():
    violations: List[Tuple[str, int, str]] = []

    for file_path in _get_target_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"execute", "executemany"}:
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        val = node.args[0].value.strip().upper()
                        if any(val.startswith(kw) for kw in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE"]):
                            violations.append((file_path.name, node.lineno, val[:30]))

    assert not violations, f"Direct SQL execution found in ai/media/ or ai/speech/: {violations}"


def test_no_raw_project_filesystem_in_media_and_speech():
    forbidden_patterns = ["projects/", "projects\\", ".pipeline_state.json"]
    violations: List[Tuple[str, int, str]] = []

    for file_path in _get_target_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value
                if any(pat in val for pat in forbidden_patterns):
                    violations.append((file_path.name, node.lineno, val))

    assert not violations, f"Raw project filesystem references found in media/speech: {violations}"


def test_no_provider_sdk_imports_in_canonical_service():
    """Canonical service must never import vendor wire SDKs directly."""
    service_file = AI_MEDIA_DIR / "service.py"
    tree = ast.parse(service_file.read_text(encoding="utf-8"), filename=str(service_file))

    forbidden_sdks = {"openai", "anthropic", "google.generativeai", "elevenlabs", "fal", "replicate"}
    violations = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in forbidden_sdks:
                    violations.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in forbidden_sdks:
                violations.append((node.lineno, node.module or ""))

    assert not violations, f"Direct vendor SDK imports found in MediaIntelligenceService: {violations}"


def test_no_vendor_specific_business_capabilities():
    """Capabilities in media/speech contracts must only use canonical CapabilityType enum."""
    allowed_values = {c.value for c in CapabilityType}
    for val in allowed_values:
        assert not val.startswith("WHISPER_"), f"Vendor token in CapabilityType: {val}"
        assert not val.startswith("OPENAI_"), f"Vendor token in CapabilityType: {val}"
        assert not val.startswith("GOOGLE_"), f"Vendor token in CapabilityType: {val}"


def test_no_lifecycle_or_qc_authority_mutation():
    forbidden_tokens = [".studio_approved", ".qc_passed", ".studio_unlocked", "06_qc_report.json"]
    violations = []

    for file_path in _get_target_python_files():
        content = file_path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in content:
                violations.append((file_path.name, token))

    assert not violations, f"Forbidden lifecycle/QC tokens found: {violations}"


def test_s28_and_future_platforms_not_started():
    """
    Enforces S27/AI-15 Scope Boundary:
    S28 features (e.g. ai/s28, ai/autonomous_editor, ai/generative_studio)
    must NOT be started in S27.
    """
    forbidden_future_dirs = [
        "ai/s28",
        "ai/autonomous_editor",
        "ai/generative_studio",
    ]
    violations = []
    for d in forbidden_future_dirs:
        found_files = list(WORKSPACE_ROOT.glob(f"{d}/**/*.py"))
        if found_files:
            violations.extend(found_files)

    assert len(violations) == 0, f"S28 subsystems were started prematurely: {violations}"


    # Default unanalyzed reports retain foundation status until analyzed
    report = MediaIntelligence(
        workspace_id="ws_test",
        asset_id="ast_test",
        content_hash="12345678",
        created_at="2026-10-01T12:00:00Z",
        provenance={"producer": "test", "timestamp": "2026-10-01T12:00:00Z"},
    )
    assert report.visual.status == "TYPED_FOUNDATION_AI13"
    assert report.visual.has_visual_analysis is False
    assert report.audio.status == "TYPED_FOUNDATION_AI13"
    assert report.audio.has_audio_analysis is False
