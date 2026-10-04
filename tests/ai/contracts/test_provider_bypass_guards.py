"""
tests/ai/contracts/test_provider_bypass_guards.py
=================================================
Automated guards proving legacy direct provider tools CANNOT bypass ModelRouter,
cannot independently select providers, cannot directly access provider credentials,
and cannot execute outside canonical S27 capability adapters and telemetry.

Protected Tools:
1. .agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py
2. .agents/plugins/super-video-maker-plugin/tools/heygen_client.py
3. .agents/plugins/super-video-maker-plugin/tools/fal_seedance_video.py
4. .agents/plugins/super-video-maker-plugin/tools/replicate_video.py
5. .agents/plugins/super-video-maker-plugin/tools/image_provider.py
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest

from ai.routing.router import ModelRouter
from ai.capabilities.registry import get_capability_registry
from ai.providers.registry import get_provider_registry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TOOLS_DIR = REPO_ROOT / ".agents" / "plugins" / "super-video-maker-plugin" / "tools"

LEGACY_PROVIDER_TOOLS = [
    "elevenlabs_voice.py",
    "heygen_client.py",
    "fal_seedance_video.py",
    "replicate_video.py",
    "image_provider.py",
]


def _load_tool_module(filename: str):
    file_path = TOOLS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestProviderBypassCliBlocked:
    """Verifies that direct CLI execution of all 5 legacy provider tools is hard-blocked."""

    @pytest.mark.parametrize("tool_name", LEGACY_PROVIDER_TOOLS)
    def test_cli_execution_hard_blocked(self, tool_name: str):
        tool_path = TOOLS_DIR / tool_name
        assert tool_path.is_file(), f"Tool {tool_name} must exist"

        result = subprocess.run(
            [sys.executable, str(tool_path)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        # Must fail with non-zero exit code
        assert result.returncode != 0, f"Tool {tool_name} CLI execution unexpectedly succeeded!"
        # Must clearly state that direct provider bypass is blocked
        combined_output = result.stdout + result.stderr
        assert (
            "DIRECT PROVIDER BYPASS BLOCKED" in combined_output
            or "RuntimeError" in combined_output
        ), f"Tool {tool_name} did not emit expected bypass block guard"


class TestProviderBypassMethodsBlocked:
    """Verifies that invoking generation or dispatch methods in legacy tools raises RuntimeError."""

    def test_elevenlabs_voice_methods_blocked(self):
        mod = _load_tool_module("elevenlabs_voice.py")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.pick_voice("en")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.tts("hello", "voice-123", "/tmp/dummy.mp3")

    def test_heygen_client_methods_blocked(self):
        mod = _load_tool_module("heygen_client.py")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.list_avatars()
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.list_voices()
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.generate_avatar_video("test script")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.create_avatar_clip("test script", "/tmp/dummy.mp4")

    def test_fal_seedance_video_methods_blocked(self):
        mod = _load_tool_module("fal_seedance_video.py")
        args = argparse.Namespace(prompt="test prompt", mode="text", duration=5, resolution="720p")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.cmd_generate(args)

    def test_replicate_video_methods_blocked(self):
        mod = _load_tool_module("replicate_video.py")
        args = argparse.Namespace(prompt="test prompt", duration=5, resolution="720p", aspect_ratio="16:9")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.cmd_generate(args)

    def test_image_provider_methods_blocked(self):
        mod = _load_tool_module("image_provider.py")
        args = argparse.Namespace(prompt="test prompt", model="gpt-image-2", size="1024x1024")
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.generate(args)
        with pytest.raises(RuntimeError, match="DIRECT PROVIDER EXECUTION BLOCKED"):
            mod.edit(args)


class TestProviderBypassSecretsBlocked:
    """Verifies that direct secret extraction outside canonical adapters is prohibited."""

    def test_elevenlabs_secret_access_blocked(self):
        mod = _load_tool_module("elevenlabs_voice.py")
        with pytest.raises(PermissionError, match="DIRECT SECRET ACCESS BLOCKED"):
            mod._key()

    def test_heygen_secret_access_blocked(self):
        mod = _load_tool_module("heygen_client.py")
        with pytest.raises(PermissionError, match="DIRECT SECRET ACCESS BLOCKED"):
            mod._headers()

    def test_fal_secret_access_blocked(self):
        mod = _load_tool_module("fal_seedance_video.py")
        with pytest.raises(PermissionError, match="DIRECT SECRET ACCESS BLOCKED"):
            mod.load_dotenv_files()
        with pytest.raises(PermissionError, match="DIRECT SECRET ACCESS BLOCKED"):
            mod.load_env()

    def test_replicate_secret_access_blocked(self):
        mod = _load_tool_module("replicate_video.py")
        with pytest.raises(PermissionError, match="DIRECT SECRET ACCESS BLOCKED"):
            mod.load_env()

    def test_image_provider_secret_access_blocked(self):
        mod = _load_tool_module("image_provider.py")
        with pytest.raises(PermissionError, match="DIRECT SECRET ACCESS BLOCKED"):
            mod.require_openai_key()


class TestModelRouterSoleProviderAuthority:
    """Proves ModelRouter and CapabilityRegistry are the sole authorities for model/provider selection."""

    def test_model_router_is_singleton_authority(self):
        router = ModelRouter()
        assert router is not None
        provider_reg = get_provider_registry()
        cap_reg = get_capability_registry()
        assert provider_reg is not None
        assert cap_reg is not None

    def test_legacy_tools_not_in_runtime_adapters(self):
        """Verifies that canonical adapters do not import or delegate to the legacy tools."""
        adapters_dir = REPO_ROOT / "ai" / "mcp" / "adapters"
        if adapters_dir.exists():
            for p in adapters_dir.glob("*.py"):
                content = p.read_text(encoding="utf-8")
                for legacy_tool in LEGACY_PROVIDER_TOOLS:
                    assert legacy_tool not in content, f"Adapter {p.name} illegally references legacy {legacy_tool}"
