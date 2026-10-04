"""
ai/contracts/request.py
=======================
Canonical request contract for invoking the AI subsystem.

Invariants:
- Provider-neutral: strictly forbids vendor-specific fields (e.g. openai_*, anthropic_*).
- Tenant-aware: workspace_id and actor_id are mandatory.
"""

from __future__ import annotations

from typing import Dict, Optional, Set
from pydantic import Field, JsonValue, field_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime
from ai.contracts.common import (
    CapabilityType,
    CapabilityTypeEnum,
    ExecutionClass,
    ExecutionClassEnum,
    PrivacyRequirement,
    PrivacyRequirementEnum,
    QualityTarget,
    QualityTargetEnum,
)

FORBIDDEN_VENDOR_PREFIXES: Set[str] = {
    "openai_",
    "anthropic_",
    "gemini_",
    "elevenlabs_",
    "fal_",
    "replicate_",
    "whisper_",
    "claude_",
    "chatgpt_",
}


class AIRequest(AIContractModel):
    """
    Canonical request contract for the AI subsystem.
    Standardized, provider-neutral representation of user or system intent.
    """
    request_id: str = Field(min_length=1, description="Unique client or system request identifier")
    workspace_id: str = Field(min_length=1, description="Mandatory tenant workspace identifier")
    actor_id: str = Field(min_length=1, description="Authenticated actor (user or service) identifier")
    project_id: Optional[str] = Field(default=None, description="Optional associated project identifier")
    session_id: Optional[str] = Field(default=None, description="Optional interactive session identifier")
    capability: CapabilityTypeEnum = Field(description="Requested domain capability")
    intent: Optional[str] = Field(default=None, description="Optional semantic intent or workflow action")
    input_data: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Structured typed payload providing inputs to the capability",
    )
    quality_target: QualityTargetEnum = Field(
        default=QualityTarget.STANDARD,
        description="Desired quality and resource allocation tier",
    )
    privacy_requirement: PrivacyRequirementEnum = Field(
        default=PrivacyRequirement.PUBLIC_ALLOWED,
        description="Data retention and isolation policy constraint",
    )
    execution_class: ExecutionClassEnum = Field(
        default=ExecutionClass.INTERACTIVE,
        description="Execution latency and scheduling tier",
    )
    metadata: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Constrained key-value metadata associated with the request",
    )
    created_at: TzAwareDatetime = Field(description="Timezone-aware request creation timestamp")
    contract_version: str = Field(default="1.0.0", description="SemVer version of this contract")

    @field_validator("input_data", "metadata")
    @classmethod
    def validate_provider_neutrality(cls, data: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
        for key in data.keys():
            lower_k = key.lower()
            for prefix in FORBIDDEN_VENDOR_PREFIXES:
                if lower_k.startswith(prefix):
                    raise ValueError(
                        f"Provider-specific field '{key}' violates provider neutrality in AIRequest. "
                        f"Vendor-specific arguments must not appear in canonical business contracts."
                    )
        return data
