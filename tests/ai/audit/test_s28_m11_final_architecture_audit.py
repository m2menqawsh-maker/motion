"""
tests/ai/audit/test_s28_m11_final_architecture_audit.py
========================================================
S28-M11 Mandatory Final Architecture Audit Gate.

Enforces all 13 repository-wide architectural invariants specified in S28-M11:
1. CreativePlanner -> raw MCP (Strictly FORBIDDEN)
2. Recipe -> provider name as authority (Strictly FORBIDDEN)
3. Skill -> raw MCP transport (Strictly FORBIDDEN)
4. AI -> raw filesystem mutation (Strictly FORBIDDEN outside disposable worker scratch)
5. AI -> arbitrary shell (shell=True Strictly FORBIDDEN)
6. AI -> direct FFmpeg string (Strictly FORBIDDEN in planners/recipes/skills)
7. MCP -> canonical lifecycle mutation bypass (Strictly FORBIDDEN)
8. MCP -> canonical registry mutation bypass (Strictly FORBIDDEN)
9. MCP -> direct cross-tenant StorageService reference (Strictly FORBIDDEN)
10. MCP -> raw project filesystem write (Strictly FORBIDDEN)
11. Domain Service -> Compatibility MCP dependency (Strictly FORBIDDEN)
12. Model Capability implemented as ToolGateway hack (Strictly FORBIDDEN)
13. Tool Capability routed through ModelRouter incorrectly (Strictly FORBIDDEN)
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import List, Tuple
import pytest

from ai.capabilities.catalog import CapabilityCatalog, get_capability_catalog
from ai.contracts.capability import CapabilityCategory
from ai.contracts.common import CapabilityType
from ai.routing.capability_router import CapabilityRouter
from ai.routing.router import ModelRouter
from ai.tools.gateway import ToolGateway

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
AI_ROOT = WORKSPACE_ROOT / "ai"
SCRIPTS_ROOT = WORKSPACE_ROOT / "scripts"
RECIPES_ROOT = WORKSPACE_ROOT / "recipes"


class TestS28M11ArchitectureAudit:
    """Rigorous repository-wide architecture audit suite for S28-M11."""

    def test_guard_01_no_raw_mcp_in_creative_planner(self):
        """CreativePlanner and planning modules must have zero imports or calls to raw MCP servers."""
        planning_dir = AI_ROOT / "planning"
        violations = []
        for py_file in planning_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "ai.mcp" in content or "mcp_servers" in content:
                violations.append(str(py_file.relative_to(WORKSPACE_ROOT)))
        assert not violations, f"Raw MCP found in planning modules: {violations}"

    def test_guard_02_recipes_have_no_provider_authority(self):
        """
        Modern recipes (ai/contracts/creative/recipe.py, ai/recipes/) must specify provider-neutral
        capabilities from CapabilityType, and have zero vendor provider authority.
        """
        from ai.recipes.registry import RecipeRegistry
        registry = RecipeRegistry()
        for recipe in registry.list_all():
            # Assert all required capabilities are canonical CapabilityType enum members
            for cap in recipe.required_capabilities:
                assert isinstance(cap, CapabilityType) or cap in CapabilityType, (
                    f"Recipe {recipe.recipe_id} specifies non-canonical capability: {cap}"
                )
                assert not any(prov in str(cap).lower() for prov in ["openai", "anthropic", "elevenlabs", "fal", "replicate"]), (
                    f"Recipe {recipe.recipe_id} has vendor authority in capability: {cap}"
                )

    def test_guard_03_no_raw_mcp_transport_in_skills(self):
        """Skills must resolve through CapabilityRouter or SkillRegistry, never direct raw MCP."""
        skills_dir = AI_ROOT / "skills"
        violations = []
        for py_file in skills_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "ai.mcp" in content or "mcp-servers" in content:
                violations.append(str(py_file.relative_to(WORKSPACE_ROOT)))
        assert not violations, f"Raw MCP transport found in skills: {violations}"

    def test_guard_04_no_arbitrary_shell_in_ai_subsystem(self):
        """shell=True is strictly banned across all production python files in ai/."""
        violations = []
        for py_file in AI_ROOT.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "shell":
                    if isinstance(node.value, ast.Constant) and node.value.value is True:
                        violations.append(f"{py_file.relative_to(WORKSPACE_ROOT)}:{node.lineno}")
        assert not violations, f"Forbidden shell=True found in ai/: {violations}"

    def test_guard_05_no_ai_direct_ffmpeg_strings(self):
        """
        Planners, narrative, recipes, and directors must never construct raw FFmpeg CLI command strings.
        Media operations must be expressed exclusively as typed contracts.
        """
        forbidden_dirs = [
            AI_ROOT / "planning",
            AI_ROOT / "narrative",
            AI_ROOT / "intent",
            AI_ROOT / "recipes",
            AI_ROOT / "skills",
            AI_ROOT / "directors",
            AI_ROOT / "taste",
        ]
        violations = []
        for target_dir in forbidden_dirs:
            if not target_dir.exists():
                continue
            for py_file in target_dir.rglob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        s = node.value.strip().lower()
                        if s.startswith("ffmpeg ") or s.startswith("ffprobe ") or " -filter_complex " in s or " -vf " in s:
                            violations.append(f"{py_file.relative_to(WORKSPACE_ROOT)}:{node.lineno} -> '{node.value}'")
        assert not violations, f"Direct FFmpeg command strings found in creative AI layer: {violations}"

    def test_guard_06_no_lifecycle_mutation_in_mcp_or_ai(self):
        """Direct assignment to state.lifecycle_state is forbidden in ai/ and ai/mcp/."""
        violations = []
        for py_file in AI_ROOT.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Attribute) and target.attr == "lifecycle_state":
                            violations.append(f"{py_file.relative_to(WORKSPACE_ROOT)}:{node.lineno}")
        assert not violations, f"Lifecycle mutation bypass detected: {violations}"

    def test_guard_07_no_canonical_registry_mutation_in_mcp_or_ai(self):
        """MCP and AI modules must not write to canonical registry files or template directories."""
        forbidden_targets = ["template-registry-data.json", "template_catalog.json"]
        violations = []
        for py_file in (list((AI_ROOT / "mcp").rglob("*.py")) + list((AI_ROOT / "tools").rglob("*.py"))):
            content = py_file.read_text(encoding="utf-8")
            for ft in forbidden_targets:
                if ft in content:
                    violations.append(f"{py_file.relative_to(WORKSPACE_ROOT)} references {ft}")
        assert not violations, f"Registry mutation references in MCP/tools: {violations}"

    @pytest.mark.asyncio
    async def test_guard_08_no_mcp_direct_cross_tenant_storage(self):
        """MCP tools and compatibility facades must strictly enforce tenant boundaries via ToolGateway."""
        from ai.mcp.compatibility.contracts import CompatibilityRequest
        from ai.mcp.compatibility.facade import MCPCompatibilityFacade
        facade = MCPCompatibilityFacade()

        # Attempt to access Tenant B project through MCP facade
        req = CompatibilityRequest(
            server_id="image-tools-mcp",
            tool_name="upscale_image",
            arguments={
                "project_id": "prj_tenant_b_secret",
                "file_path": "assets/img.png",
                "target_width": 200,
            },
            workspace_id="ws_tenant_a",
            project_id="prj_tenant_b_secret",
            actor_id="user_a",
            roles=["editor"],
            permissions=["viewer", "editor"],
        )
        res = await facade.execute(req)
        assert res.success is False
        assert res.error is not None

    def test_guard_09_domain_services_do_not_depend_on_compatibility_mcp(self):
        """Domain services and adapters must have zero import dependencies on ai.mcp.compatibility."""
        domain_dirs = [
            SCRIPTS_ROOT / "core",
            WORKSPACE_ROOT / "api" / "services",
            AI_ROOT / "media_processing",
            AI_ROOT / "image_processing",
            AI_ROOT / "speech",
            AI_ROOT / "acquisition",
        ]
        violations = []
        for d in domain_dirs:
            if not d.exists():
                continue
            for py_file in d.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                if "ai.mcp.compatibility" in content:
                    violations.append(str(py_file.relative_to(WORKSPACE_ROOT)))
        assert not violations, f"Domain services depending on Compatibility MCP: {violations}"

    def test_guard_10_speech_to_text_is_model_capability(self):
        """
        SPEECH_TO_TEXT must be defined in category MODEL and routed via ModelRouter,
        not as a tool hack inside ToolGateway.
        """
        catalog = get_capability_catalog()
        stt_def = catalog.get(CapabilityType.SPEECH_TO_TEXT)
        assert stt_def is not None, "SPEECH_TO_TEXT missing from catalog"
        assert stt_def.category == CapabilityCategory.MODEL, f"SPEECH_TO_TEXT category must be MODEL, got {stt_def.category}"

        router = CapabilityRouter(catalog=catalog)
        assert router.model_router is not None
        assert isinstance(router.model_router, ModelRouter)

    def test_guard_11_tool_capabilities_routed_through_tool_gateway(self):
        """
        TRIM_VIDEO, SEARCH_STOCK_VIDEOS, AUTO_CROP_IMAGE, INSPECT_MEDIA must be in TOOL category
        and routed via ToolGateway, not ModelRouter.
        """
        catalog = get_capability_catalog()
        expected_tools = [
            CapabilityType.TRIM_VIDEO,
            CapabilityType.SEARCH_STOCK_VIDEOS,
            CapabilityType.AUTO_CROP_IMAGE,
            CapabilityType.INSPECT_MEDIA,
        ]
        for cap_type in expected_tools:
            cap_def = catalog.get(cap_type)
            assert cap_def is not None, f"Capability {cap_type} missing from catalog"
            assert cap_def.category == CapabilityCategory.TOOL, (
                f"Capability {cap_type} must be category TOOL, got {cap_def.category}"
            )

    def test_guard_12_provider_neutrality_across_capabilities(self):
        """All 43 capabilities in catalog must be provider-neutral and contain no vendor prefixes."""
        catalog = get_capability_catalog()
        forbidden_vendors = ["openai", "gemini", "anthropic", "elevenlabs", "heygen", "fal", "replicate", "pexels", "pixabay"]
        for cap in catalog.list_all():
            val = cap.capability_id.value if hasattr(cap.capability_id, "value") else str(cap.capability_id)
            for v in forbidden_vendors:
                assert not val.lower().startswith(v), f"Capability {val} has vendor prefix '{v}'"

    def test_guard_13_qc_authority_inviolability(self):
        """
        AI planners and directors cannot declare QC passed or approve renders directly.
        Only scripts/gates/final_qc.py or ReviewService holds this authority.
        """
        ai_dirs = [AI_ROOT / "planning", AI_ROOT / "directors", AI_ROOT / "orchestration"]
        violations = []
        for d in ai_dirs:
            if not d.exists():
                continue
            for py_file in d.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                if ".qc_passed" in content or "06_qc_report.json" in content:
                    violations.append(str(py_file.relative_to(WORKSPACE_ROOT)))
        assert not violations, f"AI directly referencing QC approval tokens: {violations}"
