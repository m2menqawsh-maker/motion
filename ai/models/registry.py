"""
ai/models/registry.py
=====================
Authoritative Model Registry for S27.

Invariants:
- All models must reference a valid registered provider in ProviderRegistry.
- All capabilities declared by a model must exist in CapabilityRegistry.
- Duplicate model registrations trigger DuplicateModelError.
- Unknown model lookups trigger UnknownModelError.
- Pricing is strictly Decimal-backed and versioned.
- Registry can be frozen to guarantee runtime immutability.
- No router logic lives in this registry (ADR-004 DEC-06.3).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from ai.contracts.common import CapabilityType
from ai.contracts.errors import UnknownProviderError
from ai.contracts.model import CANONICAL_PROVIDER_IDS
from ai.capabilities.registry import (
    CapabilityRegistry,
    UnknownCapabilityError,
    get_capability_registry,
)
from ai.models.types import ModelDefinition


class ModelRegistryError(Exception):
    """Base exception for model registry errors."""
    pass


class DuplicateModelError(ModelRegistryError):
    """Raised when registering an already registered model ID."""
    def __init__(self, model_id: str):
        super().__init__(f"Duplicate model registration rejected: '{model_id}' is already registered.")
        self.model_id = model_id


class UnknownModelError(ModelRegistryError):
    """Raised when querying a model ID that is not registered."""
    def __init__(self, model_id: str):
        super().__init__(f"Unknown model '{model_id}'. Must be registered in ModelRegistry.")
        self.model_id = model_id


class ModelRegistry:
    """
    Registry maintaining authoritative ModelDefinition objects.
    Validates references against CapabilityRegistry and ProviderRegistry.
    """

    def __init__(
        self,
        capability_registry: Optional[CapabilityRegistry] = None,
        provider_registry: Optional[Any] = None,
        provider_validator: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self._capability_registry = capability_registry or get_capability_registry()
        self._provider_registry = provider_registry
        self._provider_validator = provider_validator
        self._models: Dict[str, ModelDefinition] = {}
        self._frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        self._frozen = True

    def register(self, definition: ModelDefinition) -> None:
        if self._frozen:
            raise RuntimeError("Cannot register model: ModelRegistry is frozen.")

        mid = definition.model_id.strip()
        if mid in self._models:
            raise DuplicateModelError(mid)

        # Invariant: Provider must be registered or recognized
        pid = definition.provider_id.strip()
        if self._provider_validator is not None:
            valid_provider = self._provider_validator(pid)
        elif self._provider_registry is not None:
            valid_provider = self._provider_registry.exists(pid)
        else:
            valid_provider = pid.lower() in CANONICAL_PROVIDER_IDS

        if not valid_provider:
            raise UnknownProviderError(
                f"Model '{mid}' references unknown provider '{definition.provider_id}'."
            )

        # Invariant: All capabilities must be registered in CapabilityRegistry
        for cap in definition.capabilities:
            if not self._capability_registry.exists(cap):
                raw_cap = cap.value if hasattr(cap, "value") else str(cap)
                raise UnknownCapabilityError(
                    f"Model '{mid}' references unknown capability '{raw_cap}'."
                )

        self._models[mid] = definition

    def get(self, model_id: str) -> ModelDefinition:
        mid = model_id.strip()
        if mid not in self._models:
            raise UnknownModelError(model_id)
        return self._models[mid]

    def exists(self, model_id: str) -> bool:
        return model_id.strip() in self._models

    def list(
        self,
        provider_id: Optional[str] = None,
        capability: Optional[CapabilityType] = None,
        enabled_only: bool = False,
    ) -> List[ModelDefinition]:
        """
        Lists models filtered by optional criteria, sorted deterministically by model_id.
        """
        results: List[ModelDefinition] = []
        for m in self._models.values():
            if enabled_only and not m.enabled:
                continue
            if provider_id and m.provider_id.lower() != provider_id.lower():
                continue
            if capability and capability not in m.capabilities:
                continue
            results.append(m)
        return sorted(results, key=lambda m: m.model_id)

    def __len__(self) -> int:
        return len(self._models)

    def __contains__(self, model_id: str) -> bool:
        return self.exists(model_id)


_CANONICAL_MODEL_REGISTRY: Optional[ModelRegistry] = None


def create_empty_model_registry(
    capability_registry: Optional[CapabilityRegistry] = None,
    provider_registry: Optional[Any] = None,
    provider_validator: Optional[Callable[[str], bool]] = None,
) -> ModelRegistry:
    """Creates a new unfrozen ModelRegistry for isolated testing."""
    return ModelRegistry(
        capability_registry=capability_registry,
        provider_registry=provider_registry,
        provider_validator=provider_validator,
    )


def get_model_registry() -> ModelRegistry:
    """Returns the singleton canonical ModelRegistry, populated and frozen."""
    global _CANONICAL_MODEL_REGISTRY
    if _CANONICAL_MODEL_REGISTRY is None:
        from ai.models.definitions import CANONICAL_MODELS_LIST
        reg = ModelRegistry()
        for m in CANONICAL_MODELS_LIST:
            reg.register(m)
        reg.freeze()
        _CANONICAL_MODEL_REGISTRY = reg
    return _CANONICAL_MODEL_REGISTRY
