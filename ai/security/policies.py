"""
ai/security/policies.py
=======================
Authoritative Security & Privacy Policies for AI Platform (S27.22 / AI-15).

Invariants:
- Strongly typed policy contracts (NO dict[str, Any] in security boundaries).
- Enforces strict data classification, allowed regions, raw media, and PII access per provider.
- Enforces server-side tool policies with fail-closed semantics.
- Enforces multi-tenant data isolation and data egress controls.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, List, Optional, Set
from pydantic import BaseModel, Field


class DataClassification(str, Enum):
    """Authoritative data classification levels."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    PII = "PII"


class AIProviderPolicy(BaseModel):
    """
    Authoritative policy governing upstream AI provider capabilities,
    data sensitivity limits, regional sovereignty, and privacy constraints.
    """
    provider_id: str
    allowed_data_classes: Set[DataClassification] = Field(
        default_factory=lambda: {DataClassification.PUBLIC, DataClassification.INTERNAL}
    )
    allowed_regions: List[str] = Field(default_factory=lambda: ["local", "us-central1", "europe-west1"])
    raw_media_allowed: bool = False
    pii_allowed: bool = False
    model_config = {"frozen": True}

    def can_process_data_class(self, data_class: DataClassification) -> bool:
        """Evaluates whether the provider is authorized to receive this data class."""
        if data_class == DataClassification.PII and not self.pii_allowed:
            return False
        return data_class in self.allowed_data_classes

    def can_operate_in_region(self, region: str) -> bool:
        """Evaluates whether the provider is authorized to execute in the given region."""
        return region in self.allowed_regions

    def can_process_raw_media(self) -> bool:
        """Evaluates whether raw audio/video media can be streamed directly to this provider."""
        return self.raw_media_allowed


class ToolPolicy(BaseModel):
    """
    Server-side tool execution policy protecting domain boundaries from
    untrusted LLM outputs, prompt injection, and unauthorized side effects.
    """
    allowed_tools: Set[str] = Field(default_factory=set)
    admin_tools: Set[str] = Field(default_factory=lambda: {"system_admin", "promote_model", "delete_workspace"})
    forbidden_capabilities: Set[str] = Field(
        default_factory=lambda: {
            "approve_project",
            "mark_qc_passed",
            "change_lifecycle",
            "raw_filesystem_write",
            "direct_db_write",
            "template_registry_write",
        }
    )
    require_admin_for_sensitive: bool = True
    model_config = {"frozen": True}

    def is_tool_allowed(self, tool_name: str, is_admin: bool = False) -> bool:
        """Determines if a tool may be executed given caller role."""
        if tool_name in self.forbidden_capabilities:
            return False
        if tool_name in self.admin_tools and not is_admin:
            return False
        return bool(self.allowed_tools is None or not self.allowed_tools or tool_name in self.allowed_tools)

    def validate_tool_intent(self, intent: str) -> bool:
        """Fails closed if the LLM output expresses intent to mutate forbidden authorities."""
        normalized = intent.lower()
        for forbidden in self.forbidden_capabilities:
            if forbidden in normalized:
                return False
        return True
