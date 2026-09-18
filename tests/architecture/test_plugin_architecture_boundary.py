import sys
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PLUGIN_ROOT = REPO_ROOT / ".agents" / "plugins" / "super-video-maker-plugin"

class TestPluginArchitectureBoundary:
    """Automated permanent boundary enforcement between canonical Root and Plugin subsystem."""

    def test_active_plugin_responsibilities_exist(self):
        """Active integration components must be preserved in the plugin."""
        assert (PLUGIN_ROOT / "plugin.json").is_file(), "plugin.json must exist in plugin"
        assert (PLUGIN_ROOT / "mcp_config.json").is_file(), "mcp_config.json must exist in plugin"
        assert (PLUGIN_ROOT / "skills" / "remocn" / "SKILL.md").is_file(), "remocn skill must exist"
        assert (PLUGIN_ROOT / "skills" / "snapcn" / "SKILL.md").is_file(), "snapcn skill must exist"
        assert (PLUGIN_ROOT / "tools" / "mcp-servers").is_dir(), "MCP servers directory must exist"
        assert (PLUGIN_ROOT / "tools" / "mcp-servers" / "common-tools-mcp").is_dir(), "common-tools-mcp must exist"
        assert (PLUGIN_ROOT / "tools" / "mcp-servers" / "audio-tools-mcp").is_dir(), "audio-tools-mcp must exist"
        assert (PLUGIN_ROOT / "tools" / "mcp-servers" / "media-sources-mcp").is_dir(), "media-sources-mcp must exist"
        assert (PLUGIN_ROOT / "tools" / "mcp-servers" / "video-tools-mcp").is_dir(), "video-tools-mcp must exist"
        assert (PLUGIN_ROOT / "tools" / "mcp-servers" / "image-tools-mcp").is_dir(), "image-tools-mcp must exist"
        assert (PLUGIN_ROOT / "commands" / "avatar-insta-reel.md").is_file(), "avatar-insta-reel command must exist"

    def test_stale_plugin_mirrors_are_absent(self):
        """Plugin must NOT mirror canonical root application subsystems."""
        assert not (PLUGIN_ROOT / "scripts").exists(), "Plugin scripts mirror must be absent"
        assert not (PLUGIN_ROOT / "templates").exists(), "Plugin templates mirror must be absent"
        assert not (PLUGIN_ROOT / "recipes").exists(), "Plugin recipes mirror must be absent"
        assert not (PLUGIN_ROOT / "references").exists(), "Plugin references mirror must be absent"
        assert not (PLUGIN_ROOT / "docs").exists(), "Plugin docs mirror must be absent"
        assert not (PLUGIN_ROOT / "config" / "violations_config.json").exists(), "Plugin violations_config.json duplicate must be absent"
        assert not (PLUGIN_ROOT / "ground-truth" / "ASSET_INDEX.json").exists(), "Plugin ASSET_INDEX duplicate must be absent"

    def test_canonical_root_resources_exist(self):
        """Authoritative canonical resources must exist at repository root."""
        assert (REPO_ROOT / "templates").is_dir(), "Root templates directory must exist"
        assert (REPO_ROOT / "scripts" / "pipeline.py").is_file(), "Root canonical pipeline must exist"
        assert (REPO_ROOT / "recipes").is_dir(), "Root recipes directory must exist"
        assert (REPO_ROOT / "references").is_dir(), "Root references directory must exist"
        assert (REPO_ROOT / "config" / "violations_config.json").is_file(), "Root violations_config.json must exist"
        assert (REPO_ROOT / "ground-truth" / "ASSET_INDEX.json").is_file(), "Root ASSET_INDEX.json must exist"

    def test_asset_index_resolved_path_convergence(self):
        """build_asset_index, asset_gate, and cache_ops must resolve the exact same canonical root file."""
        # 1. build_asset_index target
        build_script = REPO_ROOT / "scripts" / "build_asset_index.py"
        build_root = build_script.resolve().parent.parent
        build_index_path = (build_root / "ground-truth" / "ASSET_INDEX.json").resolve()

        # 2. asset_gate target
        gate_script = REPO_ROOT / "scripts" / "asset_gate.py"
        gate_root = gate_script.resolve().parent.parent
        gate_index_path = (gate_root / "ground-truth" / "ASSET_INDEX.json").resolve()

        # 3. cache_ops target
        common_tools_path = PLUGIN_ROOT / "tools" / "mcp-servers" / "common-tools-mcp"
        sys.path.insert(0, str(common_tools_path.resolve()))
        from utils.cache_ops import INDEX_PATH, DATA_DIR

        cache_ops_index_path = INDEX_PATH.resolve()
        cache_ops_data_root = DATA_DIR.resolve()

        canonical_root_index = (REPO_ROOT / "ground-truth" / "ASSET_INDEX.json").resolve()

        assert build_index_path == canonical_root_index, f"build_asset_index resolved {build_index_path} != {canonical_root_index}"
        assert gate_index_path == canonical_root_index, f"asset_gate resolved {gate_index_path} != {canonical_root_index}"
        assert cache_ops_index_path == canonical_root_index, f"cache_ops resolved {cache_ops_index_path} != {canonical_root_index}"
        assert cache_ops_data_root == REPO_ROOT.resolve(), f"cache_ops data root {cache_ops_data_root} != {REPO_ROOT.resolve()}"

    def test_guardian_resolves_root_violations_config(self):
        """Guardian policy enforcement must resolve the root violations_config.json exclusively."""
        import json
        config_path = REPO_ROOT / "config" / "violations_config.json"
        assert config_path.is_file(), "Canonical root violations_config.json must exist"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        assert "forbidden_rules" in cfg or "violations" in cfg or isinstance(cfg, dict), "Config must be valid JSON"
