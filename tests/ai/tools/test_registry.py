"""
tests/ai/tools/test_registry.py
===============================
Unit tests for deterministic ToolRegistry and schema exposure (S27.9).
"""

import threading
import pytest

from ai.tools.contracts import (
    GetProjectStatusInput,
    GetProjectStatusOutput,
    ListAssetsInput,
    ListAssetsOutput,
    ToolDefinition,
)
from ai.tools.domain import register_canonical_tools
from ai.tools.errors import DuplicateToolError
from ai.tools.registry import ToolRegistry
from ai.tools.types import (
    IdempotencyPolicy,
    SideEffectClass,
    ToolAuditPolicy,
    TrustedToolExecutionContext,
)


def _dummy_adapter(inp, ctx):
    return {"status": "ok"}


def test_registry_register_and_get():
    """Verify tool can be registered and retrieved by canonical name."""
    reg = ToolRegistry()
    tool_def = ToolDefinition(
        name="my_tool",
        description="My tool description",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
    )
    reg.register(tool_def, _dummy_adapter)

    assert reg.has_tool("my_tool") is True
    retrieved = reg.get("my_tool")
    assert retrieved is not None
    assert retrieved.name == "my_tool"
    assert retrieved.definition.description == "My tool description"


def test_registry_duplicate_registration_rejected():
    """Duplicate tool name registration must be strictly rejected."""
    reg = ToolRegistry()
    tool_def = ToolDefinition(
        name="duplicate_tool",
        description="First registration",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
    )
    reg.register(tool_def, _dummy_adapter)

    with pytest.raises(DuplicateToolError):
        reg.register(tool_def, _dummy_adapter)


def test_registry_unknown_tool_lookup():
    """Looking up an unregistered tool returns None."""
    reg = ToolRegistry()
    assert reg.get("non_existent_tool") is None
    assert reg.has_tool("non_existent_tool") is False


def test_registry_disabled_tool_handling():
    """Disabled tools must be excluded from public listing unless requested."""
    reg = ToolRegistry()
    enabled_tool = ToolDefinition(
        name="tool_enabled",
        description="Enabled tool",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=True,
    )
    disabled_tool = ToolDefinition(
        name="tool_disabled",
        description="Disabled tool",
        input_contract=ListAssetsInput,
        output_contract=ListAssetsOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="asset:read",
        enabled=False,
    )
    reg.register(enabled_tool, _dummy_adapter)
    reg.register(disabled_tool, _dummy_adapter)

    # list_tools without disabled
    active_tools = reg.list_tools(include_disabled=False)
    assert len(active_tools) == 1
    assert active_tools[0].name == "tool_enabled"

    # list_tools with disabled
    all_tools = reg.list_tools(include_disabled=True)
    assert len(all_tools) == 2


def test_registry_stable_ordering():
    """Registry must sort tools in deterministic alphabetical order."""
    reg = ToolRegistry()
    names = ["zeta_tool", "alpha_tool", "gamma_tool", "beta_tool"]
    for n in names:
        td = ToolDefinition(
            name=n,
            description=f"Desc for {n}",
            input_contract=GetProjectStatusInput,
            output_contract=GetProjectStatusOutput,
            side_effect_class=SideEffectClass.READ_ONLY,
            required_permission="project:read",
        )
        reg.register(td, _dummy_adapter)

    listed = reg.list_tools()
    listed_names = [t.name for t in listed]
    assert listed_names == ["alpha_tool", "beta_tool", "gamma_tool", "zeta_tool"]


def test_registry_schema_exposure():
    """get_schemas produces deterministic schemas excluding disabled tools."""
    reg = ToolRegistry()
    register_canonical_tools(reg)

    schemas = reg.get_schemas()
    assert len(schemas) == 7
    # Verify alphabetical ordering of exposed schemas
    schema_names = [s["name"] for s in schemas]
    assert schema_names == sorted(schema_names)

    # Verify input_schema contains properties without sensitive identity fields
    for s in schemas:
        inp_schema = s["input_schema"]
        props = inp_schema.get("properties", {})
        assert "workspace_id" not in props
        assert "actor_id" not in props
        assert "role" not in props
        assert "approved_by" not in props


def test_registry_schema_exposure_context_filtering():
    """Context with restricted permissions filters exposed schemas for non-admins."""
    reg = ToolRegistry()
    register_canonical_tools(reg)

    viewer_ctx = TrustedToolExecutionContext(
        workspace_id="ws_test",
        actor_id="usr_viewer",
        roles=["viewer"],
        permissions=["project:read", "asset:read"],
        is_admin=False,
    )

    schemas = reg.get_schemas(context=viewer_ctx)
    exposed_names = [s["name"] for s in schemas]
    # Viewer has project:read and asset:read -> get_project_status and list_assets
    assert "get_project_status" in exposed_names
    assert "list_assets" in exposed_names
    # Viewer does NOT have blueprint:edit or run:execute
    assert "patch_blueprint" not in exposed_names
    assert "start_run" not in exposed_names


def test_registry_thread_safety():
    """Verify concurrent registrations do not corrupt state."""
    reg = ToolRegistry()
    errors = []

    def _worker(idx):
        try:
            td = ToolDefinition(
                name=f"worker_tool_{idx}",
                description="desc",
                input_contract=GetProjectStatusInput,
                output_contract=GetProjectStatusOutput,
                side_effect_class=SideEffectClass.READ_ONLY,
                required_permission="project:read",
            )
            reg.register(td, _dummy_adapter)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(reg.list_tools()) == 20
