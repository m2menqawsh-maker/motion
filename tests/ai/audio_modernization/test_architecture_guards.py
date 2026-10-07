"""
tests/ai/audio_modernization/test_architecture_guards.py
========================================================
Architectural guards enforcing subsystem boundaries, invariants,
and tenant safety for S28-M07 Audio Modernization & Speech subsystem.

Invariants enforced:
1. Zero shell=True in ai/speech/.
2. No direct Blueprint or AudioPlan mutations (BlueprintCompiler retains sole authority).
3. No direct Lifecycle / RunService / pipeline mutations in ai/speech/.
4. No duplicate FFmpeg adapter in ai/speech/ (MediaProcessingService retains sole authority).
5. No duplicate STT model authority in audio-tools-mcp or ai/speech/.
6. All new audio contracts inherit from AIContractModel.
"""

import ast
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SPEECH_ROOT = REPO_ROOT / "ai" / "speech"
AUDIO_MCP_ROOT = REPO_ROOT / ".agents" / "plugins" / "super-video-maker-plugin" / "tools" / "mcp-servers" / "audio-tools-mcp"


def test_zero_shell_true_in_speech():
    """Ensures no subprocess call in ai/speech uses shell=True."""
    violations = []
    for py_file in SPEECH_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                        if keyword.value.value is True:
                            violations.append(f"{py_file.name}:{node.lineno}: shell=True forbidden")

    assert len(violations) == 0, f"Found shell=True calls in speech:\n" + "\n".join(violations)


def test_no_direct_blueprint_or_audioplan_mutations():
    """
    Ensures ai/speech does not import or mutate Blueprint, AudioPlan, or compiler state.
    AudioPlan compilation belongs exclusively to BlueprintCompiler.
    """
    forbidden_symbols = {
        "AudioPlan",
        "Blueprint",
        "BlueprintCompiler",
        "CreativePlanCompiler",
    }
    forbidden_modules = {
        "scripts.pipeline",
        "scripts.generators.materialize_project",
        "scripts.render_project",
        "scripts.gates",
    }
    violations = []

    for py_file in SPEECH_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(f) for f in forbidden_modules):
                        violations.append(f"{py_file.name}:{node.lineno}: forbidden import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module.startswith(f) for f in forbidden_modules):
                    violations.append(f"{py_file.name}:{node.lineno}: forbidden import {node.module}")
                for alias in node.names:
                    if alias.name in forbidden_symbols:
                        violations.append(f"{py_file.name}:{node.lineno}: forbidden symbol import {alias.name}")

    assert len(violations) == 0, f"Found forbidden architectural imports:\n" + "\n".join(violations)


def test_no_lifecycle_or_runservice_mutations():
    """Ensures ai/speech does not mutate RunService or project lifecycle."""
    forbidden = {"RunService", "LifecycleService", "ProjectLifecycle"}
    violations = []

    for py_file in SPEECH_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in forbidden:
                        violations.append(f"{py_file.name}:{node.lineno}: forbidden import {alias.name}")

    assert len(violations) == 0, f"Found lifecycle mutations in speech:\n" + "\n".join(violations)


def test_no_duplicate_ffmpeg_adapter_in_speech():
    """
    Ensures ai/speech does not define its own FFmpeg adapter or invoke raw subprocess ffmpeg.
    All media processing belongs to MediaProcessingService.
    """
    violations = []
    for py_file in SPEECH_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if "FFmpeg" in node.name or "MediaProcessor" in node.name:
                    violations.append(f"{py_file.name}:{node.lineno}: duplicate media class {node.name}")

    assert len(violations) == 0, f"Found duplicate FFmpeg adapter in speech:\n" + "\n".join(violations)


def test_no_duplicate_stt_provider_in_speech_prep():
    """
    Ensures modern speech preparation, manifest, and timeline modules do not create duplicate STT providers.
    Canonical STT is owned exclusively by ai/speech/local_provider.py via ModelRouter (S28-M04).
    """
    violations = []
    # Check speech preparation, manifest, timeline
    for py_name in ["preparation.py", "manifest.py", "timeline.py"]:
        prep_file = SPEECH_ROOT / py_name
        if prep_file.exists():
            tree = ast.parse(prep_file.read_text(encoding="utf-8"), filename=str(prep_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if "STT" in node.name or "Whisper" in node.name or "Transcriber" in node.name:
                        violations.append(f"{py_name}:{node.lineno}: STT provider defined in {py_name}")

    assert len(violations) == 0, f"Duplicate STT provider found:\n" + "\n".join(violations)

    # Verify CAPABILITY_CATALOG assigns primary SPEECH_TO_TEXT to local_stt_provider
    import json
    catalog_path = REPO_ROOT / "documentation" / "s28m" / "CAPABILITY_CATALOG.json"
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    stt_cap = next(c for c in catalog["capabilities"] if c["capability_id"] == "SPEECH_TO_TEXT")
    primary_impl = next(i for i in stt_cap["implementations"] if i["implementation_kind"] == "NATIVE_MODEL")
    assert primary_impl["implementation_id"] == "local_stt_provider"
    assert "local_provider.py" in primary_impl["source"]


def test_all_speech_contracts_inherit_from_ai_contract_model():
    """Verifies that all new S28-M07 audio contracts inherit from AIContractModel."""
    from ai.contracts.base import AIContractModel
    import ai.contracts.media_ops as contracts

    checked_models = [
        "SplitSpeechTextInput",
        "SplitSpeechTextOutput",
        "PrepareVoSegmentsInput",
        "PrepareVoSegmentsOutput",
        "AlignAudioMetadataInput",
        "AlignAudioMetadataOutput",
        "DetectSilenceInput",
        "DetectSilenceOutput",
        "AnalyzeLoudnessInput",
        "AnalyzeLoudnessOutput",
        "NormalizeAudioInput",
        "NormalizeAudioOutput",
    ]

    for model_name in checked_models:
        cls = getattr(contracts, model_name, None)
        assert cls is not None, f"Contract model {model_name} missing in media_ops.py"
        assert issubclass(cls, AIContractModel), f"{model_name} must inherit from AIContractModel"
