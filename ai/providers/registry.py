"""
ai/providers/registry.py
========================
Authoritative Provider Registry for S27.

Invariants:
- Provider registrations are unique and deterministic.
- Duplicate registrations trigger DuplicateProviderError.
- Unknown provider lookups trigger UnknownProviderError.
- Registry can be frozen to prevent runtime mutation.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from ai.contracts.errors import UnknownProviderError
from ai.providers.base import ProviderDefinition


class ProviderRegistryError(Exception):
    """Base exception for provider registry errors."""
    pass


class DuplicateProviderError(ProviderRegistryError):
    """Raised when registering an already registered provider ID."""
    def __init__(self, provider_id: str):
        super().__init__(f"Duplicate provider registration rejected: '{provider_id}' is already registered.")
        self.provider_id = provider_id


class ProviderRegistry:
    """
    Registry maintaining authoritative AIProvider definitions.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderDefinition] = {}
        self._frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        self._frozen = True

    def register(self, definition: ProviderDefinition) -> None:
        if self._frozen:
            raise RuntimeError("Cannot register provider: ProviderRegistry is frozen.")
        pid = definition.provider_id.strip().lower()
        if pid in self._providers:
            raise DuplicateProviderError(pid)
        self._providers[pid] = definition

    def get(self, provider_id: str) -> ProviderDefinition:
        pid = provider_id.strip().lower()
        if pid not in self._providers:
            raise UnknownProviderError(provider_id)
        return self._providers[pid]

    def exists(self, provider_id: str) -> bool:
        return provider_id.strip().lower() in self._providers

    def list(self) -> List[ProviderDefinition]:
        return sorted(self._providers.values(), key=lambda p: p.provider_id)

    def __len__(self) -> int:
        return len(self._providers)

    def __contains__(self, provider_id: str) -> bool:
        return self.exists(provider_id)


_CANONICAL_PROVIDER_REGISTRY: Optional[ProviderRegistry] = None


def create_empty_provider_registry() -> ProviderRegistry:
    """Creates a fresh, empty ProviderRegistry for testing."""
    return ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """Returns the singleton canonical ProviderRegistry, initialized and frozen."""
    global _CANONICAL_PROVIDER_REGISTRY
    if _CANONICAL_PROVIDER_REGISTRY is None:
        from ai.providers.definitions import CANONICAL_PROVIDERS
        reg = ProviderRegistry()
        for p in CANONICAL_PROVIDERS:
            reg.register(p)
        reg.freeze()
        _CANONICAL_PROVIDER_REGISTRY = reg
    return _CANONICAL_PROVIDER_REGISTRY
