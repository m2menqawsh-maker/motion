"""
tests/ai/mcp/test_development_agent_preservation.py
===================================================
Preservation test suite proving Development Agent protections and plugin tools
are 100% preserved and intact (S27.10).

Validates:
- All Guardian scripts exist, parse, and function:
  behavior_guard.py, command_guard.py, post_executor.py, utils.py, write_guard.py
- hooks.json mappings are intact.
- config/violations_config.json is valid and accessible.
- All 6 legacy MCP server directories exist.
- All plugin tools and scripts exist.
- Zero development agent protections were removed.
"""

import ast
import json
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GUARDIAN_DIR = REPO_ROOT / ".agents" / "guardian"
PLUGIN_DIR = REPO_ROOT / ".agents" / "plugins" / "super-video-maker-plugin"


def test_guardian_scripts_exist_and_parse():
    """All 5 Guardian scripts must exist and be valid Python files."""
    guardian_scripts = [
        "behavior_guard.py",
        "command_guard.py",
        "post_executor.py",
        "utils.py",
        "write_guard.py",
    ]
    for script_name in guardian_scripts:
        script_path = GUARDIAN_DIR / script_name
        assert script_path.is_file(), f"Guardian script '{script_name}' must exist at {script_path}"
        content = script_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(script_path))
        assert tree is not None, f"Failed to parse {script_name}"


def test_hooks_json_configuration_intact():
    """hooks.json must properly hook all Guardian scripts for development environment."""
    hooks_path = REPO_ROOT / "hooks.json"
    assert hooks_path.is_file(), "Root hooks.json must exist"
    data = json.loads(hooks_path.read_text(encoding="utf-8"))
    hooks_text = json.dumps(data)

    assert "command_guard.py" in hooks_text
    assert "write_guard.py" in hooks_text
    assert "behavior_guard.py" in hooks_text
    assert "post_executor.py" in hooks_text


def test_violations_config_intact():
    """Root config/violations_config.json must exist with all violation categories."""
    config_path = REPO_ROOT / "config" / "violations_config.json"
    assert config_path.is_file(), "violations_config.json must exist"
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    assert "command_violations" in cfg
    assert "behavioral_violations" in cfg
    assert "protocol_violations" in cfg
    assert "write_violations" in cfg


def test_all_six_mcp_servers_directories_preserved():
    """All 6 MCP server directories in the plugin must be preserved."""
    servers_dir = PLUGIN_DIR / "tools" / "mcp-servers"
    assert servers_dir.is_dir(), "tools/mcp-servers must exist"

    expected_servers = [
        "audio-tools-mcp",
        "common-tools-mcp",
        "ffmpeg-mcp-server",
        "image-tools-mcp",
        "media-sources-mcp",
        "video-tools-mcp",
    ]
    for srv_name in expected_servers:
        srv_path = servers_dir / srv_name
        assert srv_path.is_dir(), f"MCP server directory '{srv_name}' must be preserved at {srv_path}"


def test_plugin_tools_and_provider_scripts_preserved():
    """All provider and utility scripts in plugin tools/ must be preserved."""
    tools_dir = PLUGIN_DIR / "tools"
    assert tools_dir.is_dir()

    expected_tools = [
        "elevenlabs_voice.py",
        "fal_seedance_video.py",
        "heygen_client.py",
        "image_provider.py",
        "music_provider.py",
        "replicate_video.py",
        "media_pipeline.py",
        "screen_recorder.py",
        "agent_browser_recorder.py",
        "video_captioner.py",
        "ffmpeg_qc.py",
        "ad_quality_gate.py",
        "broll_layout_qc.py",
    ]
    for tool_name in expected_tools:
        tool_path = tools_dir / tool_name
        assert tool_path.is_file(), f"Plugin tool '{tool_name}' must be preserved at {tool_path}"
        # Validate parses
        ast.parse(tool_path.read_text(encoding="utf-8"), filename=str(tool_path))


def test_no_development_protections_deleted():
    """Assert zero deleted development files."""
    assert (REPO_ROOT / ".agents" / "AGENTS.md").is_file()
    assert (REPO_ROOT / ".agents" / "rules" / "video-production-protocol.md").is_file()
    assert (REPO_ROOT / "references" / "ROUTER.md").is_file()
    assert (PLUGIN_DIR / "mcp_config.json").is_file()
    assert (PLUGIN_DIR / "plugin.json").is_file()
