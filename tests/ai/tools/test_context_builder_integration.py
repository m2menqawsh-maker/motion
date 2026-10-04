"""
tests/ai/tools/test_context_builder_integration.py
==================================================
Integration tests for tool schema exposure to Context Builder (S27.9).

Requirements:
- Section 25: Schema Exposure to Context Builder
- Section 26: Stable Schema Exposure (Deterministic ordering and serialization)
- Section 47: Context Builder Integration Verification
"""

import json
import pytest

from ai.context.types import (
    ContextAuthority,
    ContextItem,
    ContextSection,
    ContextSourceType,
)
from ai.tools import (
    ToolRegistry,
    TrustedToolExecutionContext,
    create_canonical_tool_registry,
)
from ai.tools.contracts import (
    GetProjectStatusInput,
    GetProjectStatusOutput,
    ToolDefinition,
)
from ai.tools.types import SideEffectClass


def test_tool_schema_exposure_structure():
    """Verify tool schemas exposed for Context Builder are clean and valid."""
    reg = create_canonical_tool_registry()
    schemas = reg.get_schemas()

    assert len(schemas) == 7
    # Verify deterministic alphabetical ordering
    names = [s["name"] for s in schemas]
    assert names == sorted(names)

    for s in schemas:
        assert "name" in s
        assert "description" in s
        assert "version" in s
        assert "side_effect_class" in s
        assert "input_schema" in s

        # Verify no identity or privileged fields exist in the exposed input schema
        props = s["input_schema"].get("properties", {})
        for forbidden_key in ("workspace_id", "actor_id", "user_id", "role", "approved_by", "tenant_id", "is_admin"):
            assert forbidden_key not in props, f"Forbidden identity field '{forbidden_key}' exposed in tool schema '{s['name']}'"


def test_disabled_tool_strictly_omitted_from_exposure():
    """Disabled tools must never be returned in get_schemas()."""
    reg = ToolRegistry()

    t_active = ToolDefinition(
        name="tool_active",
        description="Active tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=True,
    )
    t_disabled = ToolDefinition(
        name="tool_disabled",
        description="Disabled tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=False,
    )
    reg.register(t_active, lambda inp, ctx: None)
    reg.register(t_disabled, lambda inp, ctx: None)

    schemas = reg.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "tool_active"


def test_context_item_construction_from_tool_schemas():
    """Verify tool schemas can be packaged into canonical ContextItem for Context Builder."""
    reg = create_canonical_tool_registry()
    schemas = reg.get_schemas()

    content_str = json.dumps(schemas, sort_keys=True, separators=(",", ":"))

    import hashlib
    content_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    tool_context_item = ContextItem(
        id="tool_definitions_v1",
        section=ContextSection.TOOLS,
        source_type=ContextSourceType.TOOL_SCHEMA,
        source_id="tool_registry",
        authority=ContextAuthority.SYSTEM_AUTHORITY,
        content=content_str,
        content_hash=content_hash,
        estimated_tokens=len(content_str) // 4,
    )

    assert tool_context_item.section == ContextSection.TOOLS
    assert tool_context_item.source_type == ContextSourceType.TOOL_SCHEMA
    assert tool_context_item.authority == ContextAuthority.SYSTEM_AUTHORITY
    assert "get_project_status" in tool_context_item.content
