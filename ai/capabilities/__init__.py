"""
ai/capabilities
===============
Authoritative Capability Registry package for S27.
"""

from ai.capabilities.types import (
    CachePolicy,
    CapabilityDefinition,
    CapabilityPrivacyClass,
    ContractBindingRef,
    CostUnit,
)
from ai.capabilities.definitions import (
    CANONICAL_CAPABILITY_DEFINITIONS,
    CANONICAL_CAPABILITY_MAP,
)
from ai.capabilities.registry import (
    CapabilityRegistry,
    CapabilityRegistryError,
    DuplicateCapabilityError,
    InvalidCapabilityError,
    UnknownCapabilityError,
    create_empty_capability_registry,
    get_capability_registry,
)

__all__ = [
    "CachePolicy",
    "CapabilityDefinition",
    "CapabilityPrivacyClass",
    "ContractBindingRef",
    "CostUnit",
    "CANONICAL_CAPABILITY_DEFINITIONS",
    "CANONICAL_CAPABILITY_MAP",
    "CapabilityRegistry",
    "CapabilityRegistryError",
    "DuplicateCapabilityError",
    "InvalidCapabilityError",
    "UnknownCapabilityError",
    "create_empty_capability_registry",
    "get_capability_registry",
]
