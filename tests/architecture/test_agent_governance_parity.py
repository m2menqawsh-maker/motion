#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/architecture/test_agent_governance_parity.py — Architecture tests verifying agent instruction governance.
Ensures AGENTS.md and ROUTER.md align with ARCHITECTURE_TRUTH.md, ToolGateway/CapabilityRouter, and omit fabricated limits.
"""

from pathlib import Path


def test_agents_md_no_fabricated_line_limits():
    agents_file = Path(".agents/AGENTS.md")
    assert agents_file.exists()
    content = agents_file.read_text(encoding="utf-8")

    # Finding REALITY-021: fabricated 480-490 line constraint must NOT be present
    assert "490 lines" not in content, "Fabricated 490 line limit found in AGENTS.md"
    assert "480 lines" not in content, "Fabricated 480 line limit found in AGENTS.md"


def test_agents_md_routes_via_tool_gateway():
    agents_file = Path(".agents/AGENTS.md")
    assert agents_file.exists()
    content = agents_file.read_text(encoding="utf-8")

    # Invariant REALITY-014: must route through CapabilityRouter / ToolGateway
    assert "ToolGateway" in content or "CapabilityRouter" in content
    assert "Direct, unmediated invocation of raw MCP clients" in content or "raw MCP" in content


def test_router_md_no_quarantined_video_editor():
    router_file = Path("references/ROUTER.md")
    assert router_file.exists()
    content = router_file.read_text(encoding="utf-8")

    # Quarantined Video_Editor_MCP must not be recommended
    assert "video-editor | execute_command" not in content
    assert "ToolGateway" in content
