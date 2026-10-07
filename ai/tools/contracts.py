"""
ai/tools/contracts.py
=====================
Strongly-typed contracts for tool definitions, inputs, and outputs (S27.9).

Invariants:
- Strict validation policy: unexpected fields forbidden (extra="forbid").
- Strict type checking: coercion of mismatched primitives disabled (strict=True).
- Immutability: models are frozen value objects (frozen=True).
- No dict[str, Any] at boundaries; typed via concrete models or JsonValue.
- Absolute isolation: Tool inputs specify WHAT to operate on; WHO is operating
  comes solely from TrustedToolExecutionContext.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type
from pydantic import Field, JsonValue, model_validator

from ai.contracts.base import AIContractModel, strict_enum
from scripts.core.security.permissions import Action
from scripts.core.blueprint_model import BlueprintV2

from ai.tools.types import (
    IdempotencyPolicy,
    IdempotencyPolicyEnum,
    SideEffectClass,
    SideEffectClassEnum,
    ToolAuditPolicy,
    ToolAuditPolicyEnum,
)

ActionEnum = strict_enum(Action)


class ToolDefinition(AIContractModel):
    """
    Authoritative definition and contract metadata for a registered tool.
    """
    name: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$", description="Canonical unique identifier for tool")
    description: str = Field(min_length=1, description="Concise description of tool functionality")
    input_contract: Type[AIContractModel] = Field(description="Strongly-typed input contract class")
    output_contract: Type[AIContractModel] = Field(description="Strongly-typed output contract class")
    side_effect_class: SideEffectClassEnum = Field(description="Side effect taxonomy for safety enforcement")
    required_permission: ActionEnum = Field(description="Canonical system Action required to execute")
    timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
        description="Bounded execution timeout in seconds"
    )
    idempotency_policy: IdempotencyPolicyEnum = Field(
        default=IdempotencyPolicy.NON_IDEMPOTENT,
        description="Execution idempotency semantics"
    )
    audit_policy: ToolAuditPolicyEnum = Field(
        default=ToolAuditPolicy.SUMMARY,
        description="Audit logging level for invocations"
    )
    enabled: bool = Field(default=True, description="Whether tool is enabled in current runtime")
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="SemVer version")

    def get_input_schema(self) -> Dict[str, JsonValue]:
        """Generates deterministic JSON Schema for tool input arguments."""
        schema = self.input_contract.model_json_schema()
        # Remove volatile or title keys for canonical stability if needed
        return {k: v for k, v in schema.items() if k not in ("title", "$schema")}

    def get_tool_metadata(self) -> Dict[str, JsonValue]:
        """Generates public schema metadata exposed to Context Builder / LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "side_effect_class": self.side_effect_class.value if hasattr(self.side_effect_class, "value") else str(self.side_effect_class),
            "input_schema": self.get_input_schema(),
        }


# ==============================================================================
# Domain Tool 1: get_project_status
# ==============================================================================

class GetProjectStatusInput(AIContractModel):
    """Input payload to query canonical project lifecycle state."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")


class GetProjectStatusOutput(AIContractModel):
    """Canonical lifecycle state and permitted actions for a project."""
    project_id: str = Field(description="Project identifier")
    lifecycle_state: str = Field(description="Canonical lifecycle state string")
    revision: int = Field(ge=0, description="Project state revision number")
    allowed_actions: List[str] = Field(description="List of system actions permitted in current state")
    blocked_reason: Optional[str] = Field(default=None, description="Explanation if project advancement is blocked")
    review_status: Optional[str] = Field(default=None, description="Review bundle state if applicable")
    latest_run_id: Optional[str] = Field(default=None, description="Identifier of the most recent pipeline run")


# ==============================================================================
# Domain Tool 2: list_assets
# ==============================================================================

class ListAssetsInput(AIContractModel):
    """Input payload to query registered project media assets."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")


class AssetSummaryItem(AIContractModel):
    """Summary of an individual project media asset."""
    asset_id: str = Field(description="Canonical asset identifier")
    kind: str = Field(description="Asset kind (image, audio, video, font)")
    status: str = Field(description="Asset readiness status")
    filename: Optional[str] = Field(default=None, description="Original filename if available")
    size_bytes: Optional[int] = Field(default=None, ge=0, description="Asset file size in bytes")
    location: Optional[str] = Field(default=None, description="Relative storage path or safe URI")


class ListAssetsOutput(AIContractModel):
    """Listing of verified assets registered to the project."""
    project_id: str = Field(description="Project identifier")
    total_count: int = Field(ge=0, description="Total count of registered assets")
    assets: List[AssetSummaryItem] = Field(description="List of asset summaries")


# ==============================================================================
# Domain Tool 3: read_blueprint
# ==============================================================================

class ReadBlueprintInput(AIContractModel):
    """Input payload to inspect current project blueprint."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")


class ReadBlueprintOutput(AIContractModel):
    """Authoritative structural blueprint of the project."""
    project_id: str = Field(description="Project identifier")
    revision: int = Field(ge=0, description="State revision at which blueprint was read")
    fps: int = Field(ge=1, le=120, description="Frames per second")
    aspect_ratio: str = Field(description="Aspect ratio (e.g. 9:16, 16:9)")
    scene_count: int = Field(ge=0, description="Number of scenes in the composition")
    scenes: List[Dict[str, JsonValue]] = Field(description="Structured scene specifications")
    audio: Optional[Dict[str, JsonValue]] = Field(default=None, description="Audio plan configuration")


# ==============================================================================
# Domain Tool 4: patch_blueprint
# ==============================================================================

class PatchBlueprintInput(AIContractModel):
    """Input payload to update or modify project blueprint."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")
    expected_revision: Optional[int] = Field(default=None, ge=0, description="Expected state revision for optimistic locking")
    blueprint: BlueprintV2 = Field(description="Canonical BlueprintV2 payload to validate and apply")

    @model_validator(mode="after")
    def validate_project_identity_alignment(self) -> PatchBlueprintInput:
        if self.blueprint.project_id != self.project_id:
            raise ValueError(
                f"Blueprint payload project_id '{self.blueprint.project_id}' does not match target project_id '{self.project_id}'."
            )
        return self


class PatchBlueprintOutput(AIContractModel):
    """Outcome of blueprint mutation operation."""
    project_id: str = Field(description="Project identifier")
    revision: int = Field(ge=0, description="New state revision resulting from the mutation")
    success: bool = Field(description="Whether the patch was validated and persisted")
    message: str = Field(description="Human-readable outcome or validation summary")


# ==============================================================================
# Domain Tool 5: start_run
# ==============================================================================

class StartRunInput(AIContractModel):
    """Input payload to initiate an asynchronous pipeline execution run."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")
    idempotency_key: Optional[str] = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Optional client idempotency key to prevent duplicate runs"
    )


class StartRunOutput(AIContractModel):
    """Outcome of initiating a pipeline run."""
    project_id: str = Field(description="Project identifier")
    run_id: str = Field(description="Unique identifier for the initiated or existing run")
    status: str = Field(description="Current status of the run (e.g. QUEUED, RUNNING)")
    is_created: bool = Field(description="True if a new run was created; False if deduplicated via idempotency")
    input_revision: int = Field(ge=0, description="Project revision on which run was based")


# ==============================================================================
# Domain Tool 6: cancel_run
# ==============================================================================

class CancelRunInput(AIContractModel):
    """Input payload to request cancellation of an active pipeline run."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")
    run_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Identifier of the run to cancel")


class CancelRunOutput(AIContractModel):
    """Outcome of run cancellation request."""
    project_id: str = Field(description="Project identifier")
    run_id: str = Field(description="Cancelled run identifier")
    status: str = Field(description="Updated status of the run (e.g. CANCELLED)")


# ==============================================================================
# Domain Tool 7: get_qc_report
# ==============================================================================

class GetQcReportInput(AIContractModel):
    """Input payload to retrieve quality control / probe report for a project."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")


class GetQcReportOutput(AIContractModel):
    """Quality control verification results for the project."""
    project_id: str = Field(description="Project identifier")
    has_report: bool = Field(description="Whether a QC report has been generated for the project")
    status: str = Field(description="QC report status (PASSED, FAILED, PENDING, NOT_FOUND)")
    summary: Optional[Dict[str, JsonValue]] = Field(default=None, description="Structured QC findings and metrics")
    verdict: Optional[str] = Field(default=None, description="Authoritative gate verdict if evaluated")
    review_state: Optional[str] = Field(default=None, description="Human review status if applicable")


# ==============================================================================
# Domain Tool 8: update_asset_status (Canonical Domain Service)
# ==============================================================================

class UpdateAssetStatusInput(AIContractModel):
    """Input payload to update asset lifecycle status (S27.10 Domain Migration)."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")
    asset_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target asset identifier")
    new_status: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="New lifecycle status (e.g. ready, incoming, processing, cache)")


class UpdateAssetStatusOutput(AIContractModel):
    """Result of asset status transition."""
    project_id: str = Field(description="Project identifier")
    asset_id: str = Field(description="Target asset identifier")
    status: str = Field(description="Updated asset status")
    kind: str = Field(description="Asset kind")


# ==============================================================================
# Domain Tool 9: check_asset_cache (Canonical Domain Service)
# ==============================================================================

class CheckAssetCacheInput(AIContractModel):
    """Input payload to check asset cache status (S27.10 Domain Migration)."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")
    asset_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target asset identifier")
    specs_hash: Optional[str] = Field(default=None, description="Optional specifications hash")


class CheckAssetCacheOutput(AIContractModel):
    """Result of asset cache check."""
    project_id: str = Field(description="Project identifier")
    asset_id: str = Field(description="Target asset identifier")
    hit: bool = Field(description="True if asset exists in cache or ready storage")
    cached_location: Optional[str] = Field(default=None, description="Location of cached asset if found")


# ==============================================================================
# Domain Tool 10: save_asset_cache (Canonical Domain Service)
# ==============================================================================

class SaveAssetCacheInput(AIContractModel):
    """Input payload to save a processed asset variant to cache (S27.10 Domain Migration)."""
    project_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target project identifier")
    asset_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Target asset identifier")
    file_path: str = Field(min_length=1, description="Path to the processed file to cache")
    specs_hash: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Variant specifications hash")


class SaveAssetCacheOutput(AIContractModel):
    """Result of saving asset variant to cache."""
    project_id: str = Field(description="Project identifier")
    asset_id: str = Field(description="Target asset identifier")
    cached_location: str = Field(description="Absolute path to newly cached variant file")


