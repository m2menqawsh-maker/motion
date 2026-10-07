"""
ai/mcp/compatibility/__init__.py
==================================
MCP Compatibility Layer package (S28-M09).

Exposes:
- MCPCompatibilityFacade: Canonical façade routing external MCP calls to ToolGateway.
- CompatibilityRegistry: Authoritative registry of all 34 mapped legacy tools.
- CompatibilityMCPServer: Server transport adapter exposing tools to external MCP clients.
- Contracts and status enums.
"""

from __future__ import annotations

from ai.mcp.compatibility.contracts import (
    CompatibilityRequest,
    CompatibilityResponse,
    LegacyToolDescriptor,
    MCPCompatibilityStatus,
)
from ai.mcp.compatibility.facade import (
    MCPCompatibilityFacade,
    get_mcp_compatibility_facade,
)
from ai.mcp.compatibility.registry import (
    CompatibilityRegistry,
    default_compatibility_registry,
)
from ai.mcp.compatibility.server import (
    CompatibilityMCPServer,
    default_compatibility_server,
)

__all__ = [
    "MCPCompatibilityStatus",
    "CompatibilityRequest",
    "CompatibilityResponse",
    "LegacyToolDescriptor",
    "CompatibilityRegistry",
    "default_compatibility_registry",
    "MCPCompatibilityFacade",
    "get_mcp_compatibility_facade",
    "CompatibilityMCPServer",
    "default_compatibility_server",
]
