"""
tests/ai/migration/test_legacy_migration.py
===========================================
Legacy Migration Audit, Preservation, and Workflow Parity Test Suite (S27.23 / AI-15).
"""

from pathlib import Path
import pytest

from ai.contracts.tools import ToolCall, ToolCallStatus
from ai.tools.contracts import (
    GetProjectStatusInput,
    GetProjectStatusOutput,
    ToolDefinition,
)
from ai.tools.dispatcher import ToolDispatcher
from ai.tools.registry import ToolRegistry
from ai.tools.types import SideEffectClass, TrustedToolExecutionContext


# =============================================================================
# 1. Legacy Tree Classification Audit
# =============================================================================

LEGACY_INVENTORY_CLASSIFICATION = {
    ".agents/guardian/command_guard.py": "DEV_ONLY",
    ".agents/guardian/write_guard.py": "DEV_ONLY",
    ".agents/guardian/behavior_guard.py": "DEV_ONLY",
    ".agents/guardian/post_executor.py": "DEV_ONLY",
    ".agents/guardian/circuit_breaker.json": "DEV_ONLY",
    ".agents/rules/video-production-protocol.md": "SHARED_INVARIANT",
    ".agents/docker/Dockerfile.remotion": "RUNTIME_CONTROL",
    ".agents/secrets/.qc_salt": "SHARED_INVARIANT",
    ".agents/plugins/super-video-maker-plugin": "MIGRATED",
    ".agents/skills/prompt-engineering-expert": "DEFER_TO_S28",
}


def test_legacy_tree_inventory_preserved():
    """
    Mandatory Rule: Never Delete Blindly.
    Verifies that all required legacy and development agent components remain intact.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    for rel_path, classification in LEGACY_INVENTORY_CLASSIFICATION.items():
        full_path = repo_root / rel_path
        assert full_path.exists(), f"Critical legacy component missing: {rel_path} (classified as {classification})"

    # Specifically verify Guardian remains intact for development agent safety
    guardian_dir = repo_root / ".agents" / "guardian"
    assert (guardian_dir / "command_guard.py").exists()
    assert (guardian_dir / "write_guard.py").exists()
    assert (guardian_dir / "behavior_guard.py").exists()


# =============================================================================
# 2. Representative Old vs New Workflow Parity
# =============================================================================

@pytest.mark.asyncio
async def test_old_vs_new_workflow_parity():
    """
    Demonstrates that the new S27 architecture:
    1. Does NOT require raw external-agent filesystem control.
    2. Uses typed services, tools, and capabilities.
    3. Preserves required behavior under strict server-side authorization.
    """
    registry = ToolRegistry()
    dispatcher = ToolDispatcher(registry)

    def domain_adapter(inp: GetProjectStatusInput, ctx: TrustedToolExecutionContext):
        return GetProjectStatusOutput(
            project_id=inp.project_id,
            lifecycle_state="DRAFT",
            revision=1,
            allowed_actions=["project:read"],
        )

    tool_def = ToolDefinition(
        name="get_project_status",
        description="Retrieves current project status and pipeline state",
        input_contract=GetProjectStatusInput,
        output_contract=GetProjectStatusOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission="project:read",
        enabled=True,
    )

    registry.register(tool_def, domain_adapter)

    # 1. Old Path: External agent directly manipulating file paths without tenant checks (BANNED in Prod)
    # 2. New S27 Path: Mediated through ToolDispatcher and TrustedToolExecutionContext
    context = TrustedToolExecutionContext(
        workspace_id="ws_parity_test",
        actor_id="user_parity_tester",
        roles=["editor"],
        permissions=["project:read"],
        accessible_projects=["prj_parity_001"],
        is_admin=False,
    )

    call = ToolCall(
        call_id="call_parity_1",
        tool_name="get_project_status",
        parameters={"project_id": "prj_parity_001"},
    )
    result = await dispatcher.dispatch_async(call, context)

    assert result.status == ToolCallStatus.SUCCESS
    assert result.error is None
    assert result.output["project_id"] == "prj_parity_001"
    assert result.output["lifecycle_state"] == "DRAFT"
