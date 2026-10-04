"""
ai/capabilities/registry.py
===========================
Authoritative Capability Registry for S27 Media & Video Platform.

Invariants:
- Canonical registry is provider-neutral, deterministic, and immutable once frozen.
- Duplicate registrations fail explicitly (no silent overwrite).
- Unknown capability lookup raises structured UnknownCapabilityError.
- Provider-specific capability names are strictly forbidden and rejected at registration.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Union
from ai.contracts.common import CapabilityType
from ai.capabilities.types import CapabilityDefinition

FORBIDDEN_VENDOR_PATTERNS: Set[str] = {
    "openai",
    "anthropic",
    "gemini",
    "elevenlabs",
    "replicate",
    "whisper",
    "fal",
    "heygen",
    "chatgpt",
    "claude",
    "suno",
    "runway",
    "midjourney",
    "deepseek",
    "cohere",
    "stability",
}


class CapabilityRegistryError(Exception):
    """Base exception for capability registry errors."""
    pass


class UnknownCapabilityError(CapabilityRegistryError):
    """Raised when an unregistered capability identifier is requested."""
    def __init__(self, capability_id: str):
        super().__init__(f"Unknown capability '{capability_id}'. Must be one of the registered canonical capabilities.")
        self.capability_id = capability_id


class DuplicateCapabilityError(CapabilityRegistryError):
    """Raised when attempting to register a capability that already exists."""
    def __init__(self, capability_id: str):
        super().__init__(f"Duplicate capability registration rejected: '{capability_id}' is already registered.")
        self.capability_id = capability_id


class InvalidCapabilityError(CapabilityRegistryError):
    """Raised when a capability definition violates architectural invariants (e.g. vendor branding)."""
    def __init__(self, reason: str):
        super().__init__(f"Invalid capability definition: {reason}")
        self.reason = reason


class CapabilityRegistry:
    """
    Registry managing authoritative domain capabilities.
    Can be frozen to guarantee runtime immutability.
    """

    def __init__(self) -> None:
        self._capabilities: Dict[CapabilityType, CapabilityDefinition] = {}
        self._frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        """Freezes registry to prevent further registrations or mutations."""
        self._frozen = True

    def register(self, definition: CapabilityDefinition) -> None:
        """
        Registers a new capability definition.
        
        Raises:
            RuntimeError: If registry is frozen.
            InvalidCapabilityError: If capability violates architectural constraints (e.g. vendor names).
            DuplicateCapabilityError: If capability is already registered.
        """
        if self._frozen:
            raise RuntimeError("Cannot register capability: Capability registry is frozen and immutable.")

        # Guard: Check provider neutrality
        raw_val = str(definition.id.value if hasattr(definition.id, "value") else definition.id).lower()
        for vendor in FORBIDDEN_VENDOR_PATTERNS:
            if vendor in raw_val:
                raise InvalidCapabilityError(
                    f"Capability identifier '{definition.id}' violates provider neutrality: contains forbidden vendor token '{vendor}'."
                )

        cap_key = definition.id if isinstance(definition.id, CapabilityType) else CapabilityType(definition.id)
        if cap_key in self._capabilities:
            raise DuplicateCapabilityError(str(cap_key.value))

        self._capabilities[cap_key] = definition

    def get(self, capability: Union[CapabilityType, str]) -> CapabilityDefinition:
        """
        Retrieves definition for given capability.
        
        Raises:
            UnknownCapabilityError: If capability is not registered.
        """
        cap_key = self._resolve_key(capability)
        if cap_key not in self._capabilities:
            raw_str = capability.value if hasattr(capability, "value") else str(capability)
            raise UnknownCapabilityError(raw_str)
        return self._capabilities[cap_key]

    def exists(self, capability: Union[CapabilityType, str]) -> bool:
        """Returns True if capability is registered, False otherwise."""
        try:
            cap_key = self._resolve_key(capability)
            return cap_key in self._capabilities
        except (ValueError, KeyError, UnknownCapabilityError):
            return False

    def list(self) -> List[CapabilityDefinition]:
        """Returns deterministic list of all registered capabilities sorted by identifier value."""
        return sorted(self._capabilities.values(), key=lambda d: d.id.value)

    def validate(self, capability: Union[CapabilityType, str]) -> bool:
        """Validates that a capability is registered and compliant. Raises UnknownCapabilityError if not."""
        self.get(capability)
        return True

    def __len__(self) -> int:
        return len(self._capabilities)

    def __contains__(self, capability: Union[CapabilityType, str]) -> bool:
        return self.exists(capability)

    def _resolve_key(self, capability: Union[CapabilityType, str]) -> CapabilityType:
        if isinstance(capability, CapabilityType):
            return capability
        try:
            return CapabilityType(str(capability))
        except ValueError:
            raise UnknownCapabilityError(str(capability))


_CANONICAL_REGISTRY: Optional[CapabilityRegistry] = None


def create_empty_capability_registry() -> CapabilityRegistry:
    """Creates a new unfrozen, empty CapabilityRegistry for isolated testing."""
    return CapabilityRegistry()


def get_capability_registry() -> CapabilityRegistry:
    """Returns the singleton canonical CapabilityRegistry, initialized and frozen."""
    global _CANONICAL_REGISTRY
    if _CANONICAL_REGISTRY is None:
        from ai.capabilities.definitions import CANONICAL_CAPABILITY_DEFINITIONS
        reg = CapabilityRegistry()
        for defn in CANONICAL_CAPABILITY_DEFINITIONS:
            reg.register(defn)
        reg.freeze()
        _CANONICAL_REGISTRY = reg
    return _CANONICAL_REGISTRY
