"""
ai/providers/base.py
====================
Provider abstractions and metadata contracts for S27.3.

Invariants:
- Providers are abstract integration adapters mediating between Canonical Requests
  and provider-specific wire APIs.
- Domain Services must never import concrete provider implementations directly.
- All provider errors normalize into canonical AIError taxonomy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel
from ai.contracts.capability import CapabilityRequest, CapabilityResult
from ai.contracts.common import (
    ExecutionClassEnum,
    PrivacyRequirement,
    PrivacyRequirementEnum,
)


class ProviderDefinition(AIContractModel):
    """
    Metadata describing an external or local AI provider service.
    """
    provider_id: str = Field(min_length=1, description="Unique machine-readable identifier (e.g. openai, gemini)")
    display_name: str = Field(min_length=1, description="Human-readable provider name")
    supported_execution_modes: List[ExecutionClassEnum] = Field(min_length=1, description="Supported latency classes")
    privacy_compliance: PrivacyRequirementEnum = Field(
        default=PrivacyRequirement.PUBLIC_ALLOWED,
        description="Baseline data privacy profile guaranteed by provider",
    )
    enabled: bool = Field(default=True, description="Whether this provider is currently available")
    adapter_class: Optional[str] = Field(default=None, description="Fully qualified Python class path to adapter")
    description: Optional[str] = Field(default=None, description="Operational notes and capabilities overview")
    environment: str = Field(default="all", description="Operational environment scope (e.g. development, production, all)")
    production_default: bool = Field(default=False, description="Whether this provider can serve as default in production")


class AIProvider(ABC):
    """
    Abstract base class for all AI provider adapters.
    Normalizes domain CapabilityRequest into provider wire calls,
    and returns canonical CapabilityResult with zero secret or raw payload leakage.
    """

    def __init__(self, definition: ProviderDefinition):
        self._definition = definition

    @property
    def definition(self) -> ProviderDefinition:
        return self._definition

    @property
    def provider_id(self) -> str:
        return self._definition.provider_id

    @property
    def is_enabled(self) -> bool:
        return self._definition.enabled

    @abstractmethod
    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """
        Executes a canonical capability request.
        Must normalize execution output into CapabilityResult and convert any upstream
        errors into structured AIError taxonomy (ADR-004 DEC-06.3).
        """
        ...
