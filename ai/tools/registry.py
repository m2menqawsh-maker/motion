"""
ai/tools/registry.py
====================
Deterministic, thread-safe registry for AI Tools and domain adapters (S27.9).

Responsibilities:
- Register known tools with canonical names and versions.
- Prevent duplicate names and version conflicts.
- Expose enabled tools in stable, deterministic alphabetical order.
- Expose sanitized tool schemas to Context Builder / LLM.
- Exclude disabled tools from schema exposure and execution lookup.
- Reject unknown or unregistered tools.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional
from pydantic import JsonValue

from ai.tools.contracts import ToolDefinition
from ai.tools.errors import DuplicateToolError, UnknownToolError
from ai.tools.types import TrustedToolExecutionContext

# Signature for tool adapters: (input_model, trusted_context) -> output_model
ToolAdapterCallable = Callable[[Any, TrustedToolExecutionContext], Any]


class ToolRegistration:
    """Internal registry container associating a ToolDefinition with its executable adapter."""
    def __init__(self, definition: ToolDefinition, adapter: ToolAdapterCallable):
        self.definition = definition
        self.adapter = adapter

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def enabled(self) -> bool:
        return self.definition.enabled


class ToolRegistry:
    """
    Deterministic in-memory registry of authorized tools.
    """

    def __init__(self):
        self._tools: Dict[str, ToolRegistration] = {}
        self._lock = threading.Lock()

    def register(self, definition: ToolDefinition, adapter: ToolAdapterCallable) -> None:
        """
        Registers a tool definition and executable adapter.
        
        Raises:
            DuplicateToolError: If a tool with the same canonical name is already registered.
        """
        with self._lock:
            if definition.name in self._tools:
                existing = self._tools[definition.name]
                raise DuplicateToolError(definition.name, existing.definition.version)
            self._tools[definition.name] = ToolRegistration(definition=definition, adapter=adapter)

    def unregister(self, tool_name: str) -> bool:
        """Removes a tool registration by name (primarily used for test isolation)."""
        with self._lock:
            if tool_name in self._tools:
                del self._tools[tool_name]
                return True
            return False

    def get(self, tool_name: str) -> Optional[ToolRegistration]:
        """Retrieves registration container by canonical tool name."""
        with self._lock:
            return self._tools.get(tool_name)

    def get_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Retrieves ToolDefinition by canonical tool name."""
        reg = self.get(tool_name)
        return reg.definition if reg else None

    def has_tool(self, tool_name: str) -> bool:
        """Checks if a tool is registered."""
        with self._lock:
            return tool_name in self._tools

    def list_tools(self, include_disabled: bool = False) -> List[ToolDefinition]:
        """
        Returns all registered tool definitions in stable, deterministic alphabetical order.
        Excludes disabled tools unless explicitly requested.
        """
        with self._lock:
            registrations = list(self._tools.values())

        if not include_disabled:
            registrations = [r for r in registrations if r.enabled]

        definitions = [r.definition for r in registrations]
        return sorted(definitions, key=lambda d: d.name)

    def get_schemas(
        self,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> List[Dict[str, JsonValue]]:
        """
        Generates public JSON schemas for tools in canonical deterministic order.
        
        Guarantees:
        - Disabled tools are strictly excluded.
        - Output is sorted deterministically by tool name.
        - Authoritative tenant/identity fields are never exposed.
        - If context is provided, tools requiring permissions the actor lacks can be filtered.
        """
        tools = self.list_tools(include_disabled=False)

        if context is not None and not context.is_admin:
            # Filter tools where the principal lacks required permission
            filtered = []
            for t in tools:
                if context.has_permission(t.required_permission):
                    filtered.append(t)
            tools = filtered

        return [t.get_tool_metadata() for t in tools]

    def clear(self) -> None:
        """Clears all registrations (for testing)."""
        with self._lock:
            self._buffer = None
            self._tools.clear()


# Canonical global registry instance
default_tool_registry = ToolRegistry()
