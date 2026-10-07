"""
ai/mcp/compatibility/server.py
================================
Compatibility FastMCP server exposing legacy tools backed by canonical ToolGateway (S28-M09).

Invariants:
- Exposes all approved legacy MCP tool interfaces to external clients.
- Every invocation delegates to MCPCompatibilityFacade -> ToolGateway.
- ZERO business logic resides in this server layer (strictly transport adapter).
- Fails closed with structured errors on security violations, missing permissions, or invalid payloads.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from ai.mcp.compatibility.contracts import CompatibilityRequest
from ai.mcp.compatibility.facade import (
    MCPCompatibilityFacade,
    get_mcp_compatibility_facade,
)
from ai.mcp.compatibility.registry import (
    CompatibilityRegistry,
    default_compatibility_registry,
)

logger = logging.getLogger("clean_video.ai.mcp.compatibility.server")


class CompatibilityMCPServer:
    """
    Server adapter providing MCP stdio / RPC compatibility for external tools.
    """

    def __init__(
        self,
        facade: Optional[MCPCompatibilityFacade] = None,
        registry: Optional[CompatibilityRegistry] = None,
    ) -> None:
        self._facade = facade
        self.registry = registry or default_compatibility_registry

    @property
    def facade(self) -> MCPCompatibilityFacade:
        if self._facade is None:
            self._facade = get_mcp_compatibility_facade()
        return self._facade

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        workspace_id: str = "ws_default",
        project_id: str = "prj_default",
        actor_id: str = "usr_external_mcp",
        roles: Optional[list[str]] = None,
        permissions: Optional[list[str]] = None,
    ) -> Any:
        """
        Main entrypoint for external MCP clients calling a tool through the compatibility server.
        """
        req = CompatibilityRequest(
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments,
            workspace_id=workspace_id,
            project_id=project_id,
            actor_id=actor_id,
            roles=roles or ["EDITOR"],
            permissions=permissions or ["editor", "viewer", "asset:read", "asset:upload"],
        )

        resp = await self.facade.execute(req)
        if not resp.success:
            err = resp.error
            err_msg = err.message if err else "Unknown MCP capability failure"
            err_code = err.code.value if (err and hasattr(err.code, "value")) else "ERROR"
            raise RuntimeError(f"[{err_code}] {err_msg}")

        return resp.data

    def create_fastmcp_instance(self, server_id: str) -> Any:
        """
        Creates a FastMCP instance for the specified server_id with all registered tools bound.
        """
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            logger.warning("mcp package not installed in current environment; FastMCP instance unavailable.")
            return None

        mcp_app = FastMCP(server_id)
        tools = self.registry.get_tools_by_server(server_id)

        for desc in tools:
            tool_name = desc.legacy_tool_name

            # Dynamic binding closure
            def _make_tool_fn(t_name: str, s_id: str):
                async def _tool_fn(**kwargs) -> Any:
                    return await self.call_tool(
                        server_id=s_id,
                        tool_name=t_name,
                        arguments=kwargs,
                    )
                _tool_fn.__name__ = t_name
                _tool_fn.__doc__ = desc.description
                return _tool_fn

            mcp_app.tool(name=tool_name, description=desc.description)(_make_tool_fn(tool_name, server_id))

        return mcp_app


_default_server: Optional[CompatibilityMCPServer] = None


def get_compatibility_server() -> CompatibilityMCPServer:
    global _default_server
    if _default_server is None:
        _default_server = CompatibilityMCPServer()
    return _default_server


class _LazyServerProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_compatibility_server(), name)


default_compatibility_server = _LazyServerProxy()
