"""
ai/contracts/capability.py
==========================
Provider-neutral capability contracts for executing AI tasks.

Invariants:
- CapabilityType is strictly provider-neutral (no vendor-specific tokens).
- CapabilityResult enforces semantic coherence between status, output, and errors.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
import uuid
from typing_extensions import Self
from pydantic import Field, JsonValue, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import CapabilityType, CapabilityTypeEnum, ProvenanceRecord
from ai.contracts.errors import AIError
from ai.contracts.model import ModelRequirement
from ai.contracts.usage import UsageRecord


class CapabilityStatus(str, Enum):
    """Execution status of a capability request."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


CapabilityStatusEnum = strict_enum(CapabilityStatus)


# ==============================================================================
# S28-M02 Taxonomy Enums
# ==============================================================================

class CapabilityCategory(str, Enum):
    """Authoritative category classifying the fundamental nature of the capability."""
    MODEL = "MODEL"
    TOOL = "TOOL"
    DOMAIN_SERVICE = "DOMAIN_SERVICE"


class CapabilityFamily(str, Enum):
    """Functional clustering of related capabilities."""
    SPEECH_INTELLIGENCE = "SPEECH_INTELLIGENCE"
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    IMAGE_PROCESSING = "IMAGE_PROCESSING"
    MEDIA_ACQUISITION = "MEDIA_ACQUISITION"
    MEDIA_INSPECTION = "MEDIA_INSPECTION"
    ASSET_DOMAIN_OPERATIONS = "ASSET_DOMAIN_OPERATIONS"
    CACHE_MANAGEMENT = "CACHE_MANAGEMENT"
    JOB_MANAGEMENT = "JOB_MANAGEMENT"


class SideEffectClass(str, Enum):
    """Taxonomy of side-effects produced by executing a capability."""
    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    LOCAL_TEMP_WRITE = "LOCAL_TEMP_WRITE"
    PERSISTENT_WRITE = "PERSISTENT_WRITE"
    EXTERNAL_NETWORK = "EXTERNAL_NETWORK"
    DOMAIN_MUTATION = "DOMAIN_MUTATION"
    SUBPROCESS = "SUBPROCESS"
    BACKGROUND_JOB = "BACKGROUND_JOB"


class TenantScope(str, Enum):
    """Authoritative isolation boundary required for executing the capability."""
    NONE = "NONE"
    WORKSPACE = "WORKSPACE"
    PROJECT = "PROJECT"
    ASSET = "ASSET"
    SYSTEM = "SYSTEM"


class ExecutionMode(str, Enum):
    """Neutral descriptor of capability execution topology."""
    LOCAL = "LOCAL"
    WORKER = "WORKER"
    REMOTE = "REMOTE"
    MODEL = "MODEL"
    EXTERNAL_API = "EXTERNAL_API"
    COMPATIBILITY_MCP = "COMPATIBILITY_MCP"


class CostClass(str, Enum):
    """Coarse resource consumption and financial cost tier."""
    NEGLIGIBLE = "NEGLIGIBLE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTERNAL_BILLED = "EXTERNAL_BILLED"


class LatencyClass(str, Enum):
    """Coarse execution duration tier."""
    INTERACTIVE = "INTERACTIVE"
    SHORT = "SHORT"
    LONG_RUNNING = "LONG_RUNNING"
    BACKGROUND = "BACKGROUND"


class RetryPolicy(str, Enum):
    """Fault tolerance and retry semantics."""
    NEVER = "NEVER"
    SAFE_TRANSIENT = "SAFE_TRANSIENT"
    CONDITIONAL = "CONDITIONAL"


class IdempotencyPolicy(str, Enum):
    """Execution replay semantics."""
    READ_ONLY = "READ_ONLY"
    IDEMPOTENT = "IDEMPOTENT"
    IDEMPOTENT_WITH_KEY = "IDEMPOTENT_WITH_KEY"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"
    CONDITIONAL = "CONDITIONAL"


class ImplementationStatus(str, Enum):
    """Runtime verification status of an implementation from M01 baseline."""
    WORKING = "WORKING"
    PARTIALLY_WORKING = "PARTIALLY_WORKING"
    BROKEN = "BROKEN"
    UNVERIFIED = "UNVERIFIED"


class MigrationStrategy(str, Enum):
    """Strategic migration disposition for legacy tools."""
    PRESERVE_AS_IS = "PRESERVE_AS_IS"
    WRAP = "WRAP"
    REPAIR_THEN_WRAP = "REPAIR_THEN_WRAP"
    MOVE_TO_MODEL_SUBSYSTEM = "MOVE_TO_MODEL_SUBSYSTEM"
    MOVE_TO_DOMAIN_SERVICE = "MOVE_TO_DOMAIN_SERVICE"
    CONSOLIDATE = "CONSOLIDATE"
    NATIVE_REIMPLEMENT = "NATIVE_REIMPLEMENT"
    COMPATIBILITY_ONLY = "COMPATIBILITY_ONLY"


class CapabilityLifecycleStatus(str, Enum):
    """Lifecycle governance state of a capability definition."""
    ACTIVE = "ACTIVE"
    EXPERIMENTAL = "EXPERIMENTAL"
    DEPRECATED = "DEPRECATED"
    PROPOSED = "PROPOSED"


CapabilityCategoryEnum = strict_enum(CapabilityCategory)
CapabilityFamilyEnum = strict_enum(CapabilityFamily)
SideEffectClassEnum = strict_enum(SideEffectClass)
TenantScopeEnum = strict_enum(TenantScope)
ExecutionModeEnum = strict_enum(ExecutionMode)
CostClassEnum = strict_enum(CostClass)
LatencyClassEnum = strict_enum(LatencyClass)
RetryPolicyEnum = strict_enum(RetryPolicy)
IdempotencyPolicyEnum = strict_enum(IdempotencyPolicy)
ImplementationStatusEnum = strict_enum(ImplementationStatus)
MigrationStrategyEnum = strict_enum(MigrationStrategy)
CapabilityLifecycleStatusEnum = strict_enum(CapabilityLifecycleStatus)


# ==============================================================================
# S28-M02 Canonical Contracts
# ==============================================================================

# Disallowed provider and implementation substrings in canonical capability IDs
FORBIDDEN_CAPABILITY_PROVIDER_TOKENS = {
    "PEXELS",
    "PIXABAY",
    "WHISPER",
    "FFMPEG",
    "MCP",
    "ICONIFY",
    "FREESOUND",
}


class ImplementationDescriptor(AIContractModel):
    """
    Lightweight descriptor of a concrete runtime implementation providing a capability.
    Used for discovery, routing registry, and migration audit.
    """
    implementation_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$", description="Unique implementation identifier")
    implementation_kind: str = Field(description="Descriptor kind (e.g. LEGACY_MCP, EMBEDDED_MODEL, NATIVE_SERVICE, EXTERNAL_API)")
    current_status: ImplementationStatusEnum = Field(description="M01 verified runtime status")
    source: str = Field(min_length=1, description="Source path or module implementing this capability")
    provider_or_engine: str = Field(min_length=1, description="Underlying provider, library, or engine")
    constraints: list[str] = Field(default_factory=list, description="Runtime or environment constraints")
    known_issues: list[str] = Field(default_factory=list, description="Known defects, drifts, or security issues from M01 audit")
    legacy_storage_behavior: Optional[str] = Field(default=None, description="Observed legacy storage/filesystem behavior of this implementation")


class CapabilityDefinition(AIContractModel):
    """
    Authoritative canonical contract defining a product capability (S28-M02 / S28-M02.1).
    Provider-neutral, tenant-aware, and strictly decoupling capability semantics from implementation.
    """
    capability_id: CapabilityTypeEnum = Field(description="Canonical, provider-neutral capability identifier")
    version: str = Field(default="1.0.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", description="SemVer version of this capability contract")
    name: str = Field(min_length=1, description="Human-readable domain name")
    description: str = Field(min_length=1, description="Concise explanation of product capability")
    category: CapabilityCategoryEnum = Field(description="High-level category: MODEL, TOOL, or DOMAIN_SERVICE")
    family: CapabilityFamilyEnum = Field(description="Functional grouping family")
    input_contract: str = Field(min_length=1, description="Name or identifier of canonical input contract schema")
    output_contract: str = Field(min_length=1, description="Name or identifier of canonical output contract schema")
    side_effects: list[SideEffectClassEnum] = Field(
        default_factory=list,
        description="Canonical set of unique side-effects produced by executing this capability",
    )
    side_effect_class: SideEffectClassEnum = Field(
        description="Primary side-effect taxonomy classification",
    )
    target_storage_boundary: str = Field(
        default="StorageService",
        min_length=1,
        description="Canonical architectural owner governing storage boundary (e.g. 'StorageService', 'AssetService', 'ArtifactService', 'RunService', 'Stateless In-Memory API')",
    )
    required_permissions: list[str] = Field(default_factory=list, description="Required authorization permissions (e.g. viewer, editor, admin)")
    tenant_scope: TenantScopeEnum = Field(default=TenantScope.WORKSPACE, description="Authoritative tenant isolation boundary")
    execution_mode: ExecutionModeEnum = Field(default=ExecutionMode.LOCAL, description="Implementation execution topology")
    timeout_seconds: float = Field(default=30.0, gt=0.0, le=600.0, description="Execution timeout budget in seconds")
    retry_policy: RetryPolicyEnum = Field(default=RetryPolicy.NEVER, description="Fault tolerance and retry policy")
    idempotency_policy: IdempotencyPolicyEnum = Field(default=IdempotencyPolicy.NON_IDEMPOTENT, description="Idempotency guarantee")
    cost_class: CostClassEnum = Field(default=CostClass.NEGLIGIBLE, description="Coarse compute/resource cost tier")
    latency_class: LatencyClassEnum = Field(default=LatencyClass.SHORT, description="Execution latency tier")
    implementations: list[ImplementationDescriptor] = Field(default_factory=list, description="Registered runtime implementations")
    status: CapabilityLifecycleStatusEnum = Field(default=CapabilityLifecycleStatus.ACTIVE, description="Lifecycle status of capability")
    owner: str = Field(min_length=1, description="Semantic target architectural owner service")

    @model_validator(mode="before")
    @classmethod
    def sync_side_effects(cls, data: dict | Any) -> dict | Any:
        if isinstance(data, dict):
            effects = data.get("side_effects")
            effect_cls = data.get("side_effect_class")
            if not effects and effect_cls:
                effects = [effect_cls]
            elif effects and not effect_cls:
                effect_cls = effects[0]
            elif effects and effect_cls and effect_cls not in effects:
                effects = [effect_cls] + [e for e in effects if e != effect_cls]

            if effects:
                seen = set()
                deduped = []
                for e in effects:
                    val = e.value if hasattr(e, "value") else str(e)
                    if val not in seen:
                        seen.add(val)
                        deduped.append(e)
                data["side_effects"] = deduped
                data["side_effect_class"] = deduped[0]
            else:
                data["side_effects"] = []
        return data

    def validate_provider_neutrality(self) -> Self:
        cap_val = self.capability_id.value if hasattr(self.capability_id, "value") else str(self.capability_id)
        for token in FORBIDDEN_CAPABILITY_PROVIDER_TOKENS:
            if token in cap_val:
                raise ValueError(
                    f"Architectural guard violation: Capability identifier '{cap_val}' contains "
                    f"forbidden provider/MCP token '{token}'. Canonical capabilities must be provider-neutral."
                )
        return self

    @model_validator(mode="after")
    def validate_capability_invariants(self) -> Self:
        # 1. Provider neutrality
        self.validate_provider_neutrality()

        cap_val = self.capability_id.value if hasattr(self.capability_id, "value") else str(self.capability_id)

        # 2. Side effects must not be empty
        if not self.side_effects:
            raise ValueError(f"Capability '{cap_val}' must specify at least one side effect in side_effects")

        # 3. TenantScope consistency guards
        has_domain_mutation = SideEffectClass.DOMAIN_MUTATION in self.side_effects
        has_persistent_write = SideEffectClass.PERSISTENT_WRITE in self.side_effects

        if (has_domain_mutation or has_persistent_write) and self.tenant_scope == TenantScope.NONE:
            raise ValueError(
                f"Contradictory TenantScope: Capability '{cap_val}' produces persistent writes or domain mutations "
                f"but has tenant_scope=NONE. Mutating capabilities must be scoped to PROJECT or WORKSPACE."
            )

        if (has_domain_mutation or has_persistent_write) and not any(p in self.required_permissions for p in ["editor", "admin"]):
            raise ValueError(
                f"Insufficient permissions: Capability '{cap_val}' mutates domain or writes persistently "
                f"but required_permissions lacks 'editor' or 'admin'."
            )

        if self.tenant_scope == TenantScope.NONE and any(p in self.required_permissions for p in ["editor", "admin"]):
            raise ValueError(
                f"Contradictory TenantScope: Capability '{cap_val}' has tenant_scope=NONE but requires "
                f"tenant-specific permissions '{self.required_permissions}'."
            )

        # 4. Storage boundary normalization guard
        raw_prefixes = ("/", "c:", "d:", "assets/", "projects" + "/", "./", "../")
        lower_boundary = self.target_storage_boundary.lower()
        if any(lower_boundary.startswith(p) for p in raw_prefixes) or "raw" in lower_boundary:
            raise ValueError(
                f"Storage boundary violation: target_storage_boundary '{self.target_storage_boundary}' "
                f"must point to an architectural authority (e.g. StorageService, AssetService), not a raw path."
            )

        return self

    def resolve_input_contract(self) -> type[AIContractModel]:
        """Resolves the canonical Pydantic model for input_contract from ai.contracts."""
        import ai.contracts as contracts
        if hasattr(contracts, self.input_contract):
            cls_obj = getattr(contracts, self.input_contract)
            if isinstance(cls_obj, type) and issubclass(cls_obj, AIContractModel):
                return cls_obj
        raise ValueError(
            f"Referential integrity failure: input_contract '{self.input_contract}' for capability "
            f"'{self.capability_id}' cannot be resolved to an AIContractModel in ai.contracts."
        )

    def resolve_output_contract(self) -> type[AIContractModel]:
        """Resolves the canonical Pydantic model for output_contract from ai.contracts."""
        import ai.contracts as contracts
        if hasattr(contracts, self.output_contract):
            cls_obj = getattr(contracts, self.output_contract)
            if isinstance(cls_obj, type) and issubclass(cls_obj, AIContractModel):
                return cls_obj
        raise ValueError(
            f"Referential integrity failure: output_contract '{self.output_contract}' for capability "
            f"'{self.capability_id}' cannot be resolved to an AIContractModel in ai.contracts."
        )


# Disallowed caller keys that would attempt to select implementation or execute raw commands
FORBIDDEN_CALLER_REQUEST_KEYS = {
    "adapter_name",
    "mcp_server",
    "provider_name",
    "shell_command",
    "filesystem_path",
}


def _check_forbidden_keys(obj: Any, path: str = "") -> None:
    """Recursively validates that caller did not inject forbidden execution/implementation selectors."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in FORBIDDEN_CALLER_REQUEST_KEYS:
                loc = f"at {path}.{k}" if path else f"at '{k}'"
                raise ValueError(
                    f"Architectural guard violation: Caller cannot supply implementation selection "
                    f"or execution parameter '{k}' ({loc}). Caller may only request provider-neutral capabilities."
                )
            _check_forbidden_keys(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple, set)):
        for idx, item in enumerate(obj):
            _check_forbidden_keys(item, f"{path}[{idx}]")


class CapabilityRequest(AIContractModel):
    """
    Provider-neutral request contract to invoke a domain capability (S28-M03).
    Contains structured input arguments, tenant context, and execution constraints.
    Forbidden from accepting implementation selection tokens (mcp_server, adapter_name, etc.).
    """
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}",
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Unique request identifier",
    )
    capability_id: CapabilityTypeEnum = Field(description="Canonical, provider-neutral capability identifier")
    capability: Optional[CapabilityTypeEnum] = Field(default=None, description="Alias for capability_id")
    capability_version: str = Field(
        default="1.0.0",
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
        description="SemVer version of this capability contract",
    )
    workspace_id: Optional[str] = Field(default=None, description="Workspace tenant boundary identifier")
    project_id: Optional[str] = Field(default=None, description="Project context identifier")
    actor_id: Optional[str] = Field(default=None, description="Caller identity (user, service, or agent)")
    tenant_context: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Authoritative execution context reference or serializable claims",
    )
    input: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Structured typed input payload for the capability",
    )
    input_data: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Backward-compatible alias for input",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Client-supplied or caller idempotency key to prevent duplicate mutations",
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Tracing and observability correlation identifier",
    )
    requested_timeout: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=600.0,
        description="Caller-requested timeout ceiling in seconds",
    )
    metadata: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Safe caller metadata",
    )
    requirements: Optional[ModelRequirement] = Field(
        default=None,
        description="Optional selection constraints for routing to MODEL category",
    )
    contract_version: str = Field(default="1.0.0", description="SemVer version of this contract")

    @model_validator(mode="before")
    @classmethod
    def sync_and_validate_request(cls, data: dict | Any) -> dict | Any:
        if isinstance(data, dict):
            # Check forbidden keys anywhere in input payload, metadata, or top-level
            _check_forbidden_keys(data)

            # Sync capability <-> capability_id
            cap = data.get("capability")
            cap_id = data.get("capability_id")
            if cap and not cap_id:
                data["capability_id"] = cap
            elif cap_id and not cap:
                data["capability"] = cap_id

            # Sync input <-> input_data
            inp = data.get("input")
            inp_data = data.get("input_data")
            if inp is not None and inp_data is None:
                data["input_data"] = inp
            elif inp_data is not None and inp is None:
                data["input"] = inp_data
            elif inp is None and inp_data is None:
                data["input"] = {}
                data["input_data"] = {}
        return data


class CapabilityResult(AIContractModel):
    """
    Canonical output contract produced upon completion of a capability invocation (S28-M03).
    Guarantees strict audit provenance, safe error taxonomy, and compute telemetry.
    """
    request_id: Optional[str] = Field(default=None, description="Request identifier")
    capability_id: CapabilityTypeEnum = Field(description="Executed capability")
    capability: Optional[CapabilityTypeEnum] = Field(default=None, description="Alias for capability_id")
    status: CapabilityStatusEnum = Field(description="Outcome status")
    output: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Structured output payload on success or partial completion",
    )
    output_data: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Backward-compatible alias for output",
    )
    execution_metadata: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Safe telemetry and execution diagnostics (no secrets or host paths)",
    )
    implementation_id: Optional[str] = Field(
        default=None,
        description="Identifier of the concrete executing backend implementation",
    )
    started_at: Optional[TzAwareDatetime] = Field(
        default=None,
        description="Execution start timestamp UTC",
    )
    completed_at: Optional[TzAwareDatetime] = Field(
        default=None,
        description="Execution completion timestamp UTC",
    )
    duration_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Execution duration in milliseconds",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score bounded between 0.0 and 1.0",
    )
    provenance: Optional[ProvenanceRecord] = Field(
        default=None,
        description="Audit record tracking execution source and latency",
    )
    usage: UsageRecord = Field(default_factory=UsageRecord, description="Consumed compute resources")
    error: Optional[AIError] = Field(
        default=None,
        description="Structured error details if execution failed or encountered issues",
    )

    @model_validator(mode="before")
    @classmethod
    def sync_result_fields(cls, data: dict | Any) -> dict | Any:
        if isinstance(data, dict):
            cap = data.get("capability")
            cap_id = data.get("capability_id")
            if cap and not cap_id:
                data["capability_id"] = cap
            elif cap_id and not cap:
                data["capability"] = cap_id

            out = data.get("output")
            out_data = data.get("output_data")
            if out is not None and out_data is None:
                data["output_data"] = out
            elif out_data is not None and out is None:
                data["output"] = out_data

            # Auto-populate provenance if missing
            if data.get("provenance") is None:
                source = data.get("implementation_id") or "capability_router"
                ts = data.get("completed_at") or data.get("started_at")
                if ts is None:
                    from datetime import datetime, timezone
                    ts = datetime.now(timezone.utc)
                data["provenance"] = {
                    "source": str(source),
                    "timestamp": ts,
                    "latency_ms": data.get("duration_ms"),
                }
        return data

    @model_validator(mode="after")
    def validate_coherence(self) -> Self:
        has_output = (self.output is not None) or (self.output_data is not None)
        if self.status == CapabilityStatus.SUCCESS:
            if self.error is not None:
                raise ValueError("CapabilityResult with status SUCCESS cannot contain an error")
            if not has_output:
                raise ValueError("CapabilityResult with status SUCCESS must provide output or output_data")
        elif self.status == CapabilityStatus.FAILED:
            if self.error is None:
                raise ValueError("CapabilityResult with status FAILED must provide a structured error")
        return self
