# -*- coding: utf-8 -*-
"""
tests/ai/contracts/test_capability_taxonomy_and_contracts.py
============================================================
Comprehensive tests for S28-M02:
- CapabilityDefinition contract invariants and validation
- ImplementationDescriptor validation
- Provider neutrality guards
- Migration map completeness (34 tools == 34 mapped records)
- Exactly one primary target capability per legacy tool
- No orphan capabilities
- M01 status preservation
- Catalog validation
- Authority chain integrity
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from ai.contracts import (
    AIContractModel,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityFamily,
    CapabilityLifecycleStatus,
    CapabilityType,
    CostClass,
    ExecutionMode,
    IdempotencyPolicy,
    ImplementationDescriptor,
    ImplementationStatus,
    LatencyClass,
    MigrationStrategy,
    RetryPolicy,
    SideEffectClass,
    TenantScope,
)

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CATALOG_PATH = ROOT / "documentation" / "s28m" / "CAPABILITY_CATALOG.json"
MIGRATION_MAP_PATH = ROOT / "documentation" / "s28m" / "LEGACY_TOOL_MIGRATION_MAP.json"
M01_INVENTORY_PATH = ROOT / "documentation" / "s28m" / "MCP_REALITY_INVENTORY.json"


# ==============================================================================
# 1. CONTRACT INVARIANT TESTS
# ==============================================================================

class TestCapabilityContracts:
    """Verifies that CapabilityDefinition and ImplementationDescriptor enforce all domain invariants."""

    def test_valid_capability_definition_passes(self):
        descriptor = ImplementationDescriptor(
            implementation_id="impl_test_trim",
            implementation_kind="LEGACY_MCP",
            current_status=ImplementationStatus.WORKING,
            source="audio-tools-mcp/server.py",
            provider_or_engine="FFmpeg CLI",
            constraints=["Local FFmpeg required"],
            known_issues=[],
        )

        cap = CapabilityDefinition(
            capability_id=CapabilityType.TRIM_AUDIO,
            version="1.0.0",
            name="Trim Audio",
            description="Trims an audio file to a specified duration",
            category=CapabilityCategory.TOOL,
            family=CapabilityFamily.AUDIO_PROCESSING,
            input_contract="TrimAudioInput",
            output_contract="TrimAudioOutput",
            side_effect_class=SideEffectClass.SUBPROCESS,
            required_permissions=["editor"],
            tenant_scope=TenantScope.WORKSPACE,
            execution_mode=ExecutionMode.LOCAL,
            timeout_seconds=30.0,
            retry_policy=RetryPolicy.SAFE_TRANSIENT,
            idempotency_policy=IdempotencyPolicy.IDEMPOTENT,
            cost_class=CostClass.LOW,
            latency_class=LatencyClass.SHORT,
            implementations=[descriptor],
            status=CapabilityLifecycleStatus.ACTIVE,
            owner="MediaProcessingService (Audio Subsystem)",
        )

        assert cap.capability_id == CapabilityType.TRIM_AUDIO
        assert cap.category == CapabilityCategory.TOOL
        assert len(cap.implementations) == 1
        assert cap.implementations[0].current_status == ImplementationStatus.WORKING

    def test_missing_capability_id_fails(self):
        with pytest.raises(ValidationError):
            CapabilityDefinition(  # type: ignore
                name="Incomplete Capability",
                description="Missing ID",
                category=CapabilityCategory.TOOL,
                family=CapabilityFamily.AUDIO_PROCESSING,
                input_contract="InputModel",
                output_contract="OutputModel",
                side_effect_class=SideEffectClass.NONE,
                owner="MediaProcessingService",
            )

    def test_invalid_category_fails(self):
        with pytest.raises(ValidationError):
            CapabilityDefinition(  # type: ignore
                capability_id=CapabilityType.TRIM_AUDIO,
                name="Invalid Category Test",
                description="Bad category",
                category="NOT_A_VALID_CATEGORY",  # Invalid
                family=CapabilityFamily.AUDIO_PROCESSING,
                input_contract="InputModel",
                output_contract="OutputModel",
                side_effect_class=SideEffectClass.NONE,
                owner="MediaProcessingService",
            )

    def test_missing_input_output_contract_fails(self):
        with pytest.raises(ValidationError):
            CapabilityDefinition(  # type: ignore
                capability_id=CapabilityType.TRIM_AUDIO,
                name="Empty Contracts Test",
                description="Bad contracts",
                category=CapabilityCategory.TOOL,
                family=CapabilityFamily.AUDIO_PROCESSING,
                input_contract="",  # Invalid min_length=1
                output_contract="OutputModel",
                side_effect_class=SideEffectClass.NONE,
                owner="MediaProcessingService",
            )

    def test_invalid_implementation_descriptor_fails(self):
        with pytest.raises(ValidationError):
            ImplementationDescriptor(  # type: ignore
                implementation_id="invalid id with spaces!!",  # Regex violation
                implementation_kind="LEGACY_MCP",
                current_status="UNKNOWN_STATUS",  # Invalid enum
                source="server.py",
                provider_or_engine="Engine",
            )


# ==============================================================================
# 2. ARCHITECTURAL GUARDS & PROVIDER NEUTRALITY
# ==============================================================================

class TestArchitecturalGuards:
    """Ensures architectural constraints: no provider/MCP names in canonical capability IDs."""

    @pytest.mark.parametrize("forbidden_token", [
        "PEXELS", "PIXABAY", "WHISPER", "FFMPEG", "MCP", "ICONIFY", "FREESOUND"
    ])
    def test_forbidden_provider_tokens_in_capability_id_rejected(self, forbidden_token):
        # Dynamically test validator on a constructed CapabilityDefinition
        cap_obj = CapabilityDefinition.model_construct(
            capability_id=f"TEST_{forbidden_token}_CAPABILITY",
            name="Bad Capability",
            description="Provider coupled name",
            category=CapabilityCategory.TOOL,
            family=CapabilityFamily.MEDIA_ACQUISITION,
            input_contract="Input",
            output_contract="Output",
            side_effect_class=SideEffectClass.NONE,
            owner="Service",
        )
        with pytest.raises(ValueError, match="forbidden provider/MCP token"):
            cap_obj.validate_provider_neutrality()

    def test_all_catalog_capability_ids_are_provider_neutral(self):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        forbidden = {"PEXELS", "PIXABAY", "WHISPER", "FFMPEG", "MCP", "ICONIFY", "FREESOUND"}
        for cap in catalog["capabilities"]:
            cap_id = cap["capability_id"]
            for token in forbidden:
                assert token not in cap_id, f"Canonical capability ID '{cap_id}' contains forbidden token '{token}'"


# ==============================================================================
# 3. MAPPING COMPLETENESS & INVARIANTS (34 TOOLS == 34 MAPPINGS)
# ==============================================================================

class TestMigrationMapCompleteness:
    """Verifies that all 34 active tools from M01 are mapped with 0 loss and exact 1:1 primary targets."""

    @pytest.fixture
    def m01_inventory(self):
        with open(M01_INVENTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def migration_map(self):
        with open(MIGRATION_MAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def capability_catalog(self):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_exactly_34_tools_discovered_in_m01(self, m01_inventory):
        total_tools = sum(len(s["tools"]) for s in m01_inventory["servers"])
        assert total_tools == 34, f"Expected 34 M01 tools, got {total_tools}"

    def test_migration_map_has_exactly_34_records(self, migration_map):
        mappings = migration_map["mappings"]
        assert len(mappings) == 34, f"Expected exactly 34 mappings, found {len(mappings)}"
        assert migration_map["mapping_metadata"]["summary"]["mapped_tools"] == 34
        assert migration_map["mapping_metadata"]["summary"]["unmapped_tools"] == 0
        assert migration_map["mapping_metadata"]["summary"]["duplicate_primary_mappings"] == 0

    def test_every_m01_tool_is_mapped_uniquely(self, m01_inventory, migration_map):
        m01_tool_keys = set()
        for server in m01_inventory["servers"]:
            mcp_id = server["mcp_id"]
            for tool_name in server["tools"]:
                m01_tool_keys.add(f"{mcp_id}::{tool_name}")

        map_tool_keys = set()
        for record in migration_map["mappings"]:
            key = f"{record['legacy_mcp_id']}::{record['legacy_tool_id']}"
            assert key not in map_tool_keys, f"Duplicate legacy tool record in map: {key}"
            map_tool_keys.add(key)

        assert m01_tool_keys == map_tool_keys, (
            f"Discrepancy between M01 inventory and Migration Map! "
            f"Missing: {m01_tool_keys - map_tool_keys}, Extra: {map_tool_keys - m01_tool_keys}"
        )

    def test_every_record_has_exactly_one_primary_target(self, migration_map):
        for record in migration_map["mappings"]:
            target = record["primary_target_capability_id"]
            assert target is not None, f"Tool {record['legacy_tool_id']} has null primary target"
            assert isinstance(target, str) and len(target) > 0, f"Tool {record['legacy_tool_id']} has empty primary target"

    def test_no_orphan_canonical_capabilities(self, capability_catalog, migration_map):
        catalog_cap_ids = {c["capability_id"] for c in capability_catalog["capabilities"]}
        mapped_cap_ids = {r["primary_target_capability_id"] for r in migration_map["mappings"]}

        orphan_capabilities = catalog_cap_ids - mapped_cap_ids
        assert len(orphan_capabilities) == 0, f"Found orphan capabilities in catalog: {orphan_capabilities}"

    def test_m01_statuses_preserved_accurately(self, migration_map):
        expected_status_counts = {
            "WORKING": 18,
            "PARTIALLY_WORKING": 10,
            "BROKEN": 1,
            "UNVERIFIED": 5,
        }

        actual_status_counts = {"WORKING": 0, "PARTIALLY_WORKING": 0, "BROKEN": 0, "UNVERIFIED": 0}
        for record in migration_map["mappings"]:
            status = record["m01_status"]
            assert status in actual_status_counts, f"Unknown status: {status}"
            actual_status_counts[status] += 1

        assert actual_status_counts == expected_status_counts, (
            f"Status distribution drift! Expected {expected_status_counts}, got {actual_status_counts}"
        )

    def test_quarantined_mcp_recorded_separately(self, migration_map):
        quarantined = migration_map["historical_or_quarantined_implementations"]
        assert len(quarantined) >= 1
        video_editor = next((q for q in quarantined if q["identity"] == "Video_Editor_MCP"), None)
        assert video_editor is not None
        assert video_editor["known_status"] == "QUARANTINED"
        assert video_editor["historical_mapping_incomplete"] is True


# ==============================================================================
# 4. CAPABILITY CATALOG VALIDATION
# ==============================================================================

class TestCapabilityCatalogValidation:
    """Verifies that all 32 entries in CAPABILITY_CATALOG.json strictly validate against CapabilityDefinition."""

    def test_all_catalog_entries_validate_against_pydantic(self):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        assert catalog["catalog_metadata"]["total_capabilities"] == 32
        capabilities = catalog["capabilities"]
        assert len(capabilities) == 32

        cap_ids = set()
        for raw_cap in capabilities:
            cap_obj = CapabilityDefinition.model_validate(raw_cap)
            assert cap_obj.capability_id.value not in cap_ids, f"Duplicate capability ID: {cap_obj.capability_id}"
            cap_ids.add(cap_obj.capability_id.value)
            assert cap_obj.category in [CapabilityCategory.MODEL, CapabilityCategory.TOOL, CapabilityCategory.DOMAIN_SERVICE]
            assert cap_obj.owner is not None and len(cap_obj.owner) > 0

    def test_catalog_category_breakdown(self):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        counts = {"MODEL": 0, "TOOL": 0, "DOMAIN_SERVICE": 0}
        for c in catalog["capabilities"]:
            counts[c["category"]] += 1

        assert counts["MODEL"] == 1, f"Expected 1 MODEL, got {counts['MODEL']}"
        assert counts["DOMAIN_SERVICE"] == 7, f"Expected 7 DOMAIN_SERVICE, got {counts['DOMAIN_SERVICE']}"
        assert counts["TOOL"] == 24, f"Expected 24 TOOL, got {counts['TOOL']}"
        assert sum(counts.values()) == 32


# ==============================================================================
# 5. S28-M02.1 CAPABILITY CONTRACT HARDENING TESTS
# ==============================================================================

class TestCapabilityHardeningM021:
    """Verifies all S28-M02.1 hardening gates."""

    def test_multi_side_effects_representation(self):
        """Verifies multi-effect representation, backward-compatibility sync, and deduplication."""
        # 1. Multi-effect declaration
        cap = CapabilityDefinition(
            capability_id=CapabilityType.TRIM_VIDEO,
            name="Trim Video",
            description="Trims video",
            category=CapabilityCategory.TOOL,
            family=CapabilityFamily.VIDEO_PROCESSING,
            input_contract="TrimVideoInput",
            output_contract="TrimVideoOutput",
            side_effects=[SideEffectClass.SUBPROCESS, SideEffectClass.PERSISTENT_WRITE],
            target_storage_boundary="StorageService / Project Video",
            required_permissions=["editor"],
            tenant_scope=TenantScope.PROJECT,
            owner="MediaProcessingService",
        )
        assert len(cap.side_effects) == 2
        assert SideEffectClass.SUBPROCESS in cap.side_effects
        assert SideEffectClass.PERSISTENT_WRITE in cap.side_effects
        assert cap.side_effect_class == SideEffectClass.SUBPROCESS

        # 2. Backward compatibility: providing only side_effect_class populates side_effects
        cap_legacy = CapabilityDefinition(
            capability_id=CapabilityType.CHECK_MEDIA_CACHE,
            name="Check Cache",
            description="Checks cache",
            category=CapabilityCategory.DOMAIN_SERVICE,
            family=CapabilityFamily.CACHE_MANAGEMENT,
            input_contract="CheckCacheInput",
            output_contract="CheckCacheOutput",
            side_effect_class=SideEffectClass.READ_ONLY,
            target_storage_boundary="AssetService / Managed Cache Hierarchy",
            required_permissions=["viewer"],
            tenant_scope=TenantScope.PROJECT,
            owner="AssetService",
        )
        assert cap_legacy.side_effects == [SideEffectClass.READ_ONLY]
        assert cap_legacy.side_effect_class == SideEffectClass.READ_ONLY

        # 3. Deduplication of side effects
        cap_dedup = CapabilityDefinition(
            capability_id=CapabilityType.TRIM_VIDEO,
            name="Trim Video",
            description="Trims video",
            category=CapabilityCategory.TOOL,
            family=CapabilityFamily.VIDEO_PROCESSING,
            input_contract="TrimVideoInput",
            output_contract="TrimVideoOutput",
            side_effects=[SideEffectClass.SUBPROCESS, SideEffectClass.PERSISTENT_WRITE, SideEffectClass.SUBPROCESS],
            target_storage_boundary="StorageService / Project Video",
            required_permissions=["editor"],
            tenant_scope=TenantScope.PROJECT,
            owner="MediaProcessingService",
        )
        assert cap_dedup.side_effects == [SideEffectClass.SUBPROCESS, SideEffectClass.PERSISTENT_WRITE]

    def test_tenant_scope_consistency_and_invariants(self):
        """Verifies architectural invariants between TenantScope, permissions, and side-effects."""
        # Mutating capability with TenantScope.NONE must be rejected
        with pytest.raises(ValueError, match="Contradictory TenantScope"):
            CapabilityDefinition(
                capability_id=CapabilityType.MUTATE_ASSET_STATUS,
                name="Mutate Status",
                description="Mutates status",
                category=CapabilityCategory.DOMAIN_SERVICE,
                family=CapabilityFamily.ASSET_DOMAIN_OPERATIONS,
                input_contract="MutateAssetStatusInput",
                output_contract="MutateAssetStatusOutput",
                side_effects=[SideEffectClass.DOMAIN_MUTATION, SideEffectClass.PERSISTENT_WRITE],
                target_storage_boundary="AssetService",
                required_permissions=["editor"],
                tenant_scope=TenantScope.NONE,
                owner="AssetService",
            )

        # Mutating capability lacking editor/admin permissions must be rejected
        with pytest.raises(ValueError, match="Insufficient permissions"):
            CapabilityDefinition(
                capability_id=CapabilityType.TRIM_VIDEO,
                name="Trim Video",
                description="Trims video",
                category=CapabilityCategory.TOOL,
                family=CapabilityFamily.VIDEO_PROCESSING,
                input_contract="TrimVideoInput",
                output_contract="TrimVideoOutput",
                side_effects=[SideEffectClass.PERSISTENT_WRITE],
                target_storage_boundary="StorageService",
                required_permissions=["viewer"],
                tenant_scope=TenantScope.PROJECT,
                owner="MediaProcessingService",
            )

        # TenantScope.NONE claiming tenant-specific editor/admin permissions must be rejected
        with pytest.raises(ValueError, match="Contradictory TenantScope"):
            CapabilityDefinition(
                capability_id=CapabilityType.SEARCH_ICONS,
                name="Search Icons",
                description="Search icons",
                category=CapabilityCategory.TOOL,
                family=CapabilityFamily.MEDIA_ACQUISITION,
                input_contract="SearchIconsInput",
                output_contract="SearchIconsOutput",
                side_effects=[SideEffectClass.READ_ONLY],
                target_storage_boundary="Stateless In-Memory API",
                required_permissions=["editor"],
                tenant_scope=TenantScope.NONE,
                owner="StockMediaService",
            )

    def test_all_catalog_capabilities_satisfy_hardening_invariants(self):
        """Verifies that all 32 capabilities in the catalog adhere to S28-M02.1 invariants."""
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for raw_cap in catalog["capabilities"]:
            cap = CapabilityDefinition.model_validate(raw_cap)
            # 1. Multi-effects present
            assert len(cap.side_effects) >= 1
            assert cap.side_effect_class in cap.side_effects

            # 2. Media processing capabilities operating on project assets must be PROJECT scoped
            if cap.family in [CapabilityFamily.AUDIO_PROCESSING, CapabilityFamily.VIDEO_PROCESSING, CapabilityFamily.IMAGE_PROCESSING]:
                assert cap.tenant_scope == TenantScope.PROJECT, (
                    f"Capability {cap.capability_id} in {cap.family} must have TenantScope.PROJECT"
                )

            # 3. Target storage boundary points to architectural authority
            assert not cap.target_storage_boundary.startswith(("/", "c:", "assets/", "projects/"))
            assert any(auth in cap.target_storage_boundary for auth in ["StorageService", "AssetService", "ArtifactService", "RunService", "Stateless In-Memory API", "In-Memory"])

    def test_all_input_and_output_contracts_resolve_with_zero_dangling(self):
        """Verifies 100% referential integrity: every capability resolves its input/output model."""
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for raw_cap in catalog["capabilities"]:
            cap = CapabilityDefinition.model_validate(raw_cap)
            input_model = cap.resolve_input_contract()
            output_model = cap.resolve_output_contract()

            assert issubclass(input_model, AIContractModel), (
                f"Resolved input contract {input_model} for {cap.capability_id} does not inherit from AIContractModel"
            )
            assert issubclass(output_model, AIContractModel), (
                f"Resolved output contract {output_model} for {cap.capability_id} does not inherit from AIContractModel"
            )

    def test_dangling_contract_reference_triggers_clear_failure(self):
        """Verifies that a nonexistent contract reference raises a clear referential integrity error."""
        cap = CapabilityDefinition(
            capability_id=CapabilityType.SEARCH_ICONS,
            name="Search Icons",
            description="Search icons",
            category=CapabilityCategory.TOOL,
            family=CapabilityFamily.MEDIA_ACQUISITION,
            input_contract="NonExistentInputModel",
            output_contract="SearchIconsOutput",
            side_effects=[SideEffectClass.READ_ONLY],
            target_storage_boundary="Stateless In-Memory API",
            required_permissions=["viewer"],
            tenant_scope=TenantScope.WORKSPACE,
            owner="StockMediaService",
        )
        with pytest.raises(ValueError, match="Referential integrity failure"):
            cap.resolve_input_contract()

    def test_storage_boundary_normalization_rejects_raw_paths(self):
        """Verifies that raw filesystem paths are rejected as target storage boundaries."""
        with pytest.raises(ValueError, match="Storage boundary violation"):
            CapabilityDefinition(
                capability_id=CapabilityType.TRIM_VIDEO,
                name="Trim Video",
                description="Trims video",
                category=CapabilityCategory.TOOL,
                family=CapabilityFamily.VIDEO_PROCESSING,
                input_contract="TrimVideoInput",
                output_contract="TrimVideoOutput",
                side_effects=[SideEffectClass.PERSISTENT_WRITE],
                target_storage_boundary="assets/ready/trimmed.mp4",
                required_permissions=["editor"],
                tenant_scope=TenantScope.PROJECT,
                owner="MediaProcessingService",
            )
