#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/architecture/test_platform_portability.py — Platform portability tests (UNK-004).
Verifies that configuration files and MCP server definitions do not contain hardcoded Windows absolute paths.
"""

import json
from pathlib import Path


def test_mcp_config_no_hardcoded_windows_paths():
    config_file = Path(".agents/plugins/super-video-maker-plugin/mcp_config.json")
    assert config_file.exists(), "mcp_config.json missing"

    raw_text = config_file.read_text(encoding="utf-8")
    assert "C:/" not in raw_text, "Hardcoded Windows drive letter 'C:/' found in mcp_config.json"
    assert "C:\\" not in raw_text, "Hardcoded Windows drive letter 'C:\\' found in mcp_config.json"

    data = json.loads(raw_text)
    servers = data.get("mcpServers", {})
    assert len(servers) >= 6

    # Verify that each configured cwd exists on the current filesystem
    for server_name, server_cfg in servers.items():
        cwd = server_cfg.get("cwd")
        assert cwd is not None, f"Server {server_name} missing cwd"
        server_path = Path(cwd)
        assert server_path.exists(), f"Server {server_name} directory not found on disk: {cwd}"


def test_package_json_portable():
    for pkg_path in [Path("package.json"), Path("remotion-app/package.json")]:
        assert pkg_path.exists()
        raw = pkg_path.read_text(encoding="utf-8")
        assert "C:/" not in raw and "C:\\" not in raw
