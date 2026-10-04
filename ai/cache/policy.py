"""
ai/cache/policy.py
==================
Capability-driven cache policy evaluation engine (S27.12).

Invariants:
- Cache eligibility is governed strictly by the Capability Registry.
- Never invents ad-hoc caching rules outside capability definitions.
- Non-cacheable capabilities (CachePolicy.NEVER) strictly bypass cache.
- Coalescing respects capability cache policy: non-cacheable workloads do not force caching.
"""

from __future__ import annotations

from typing import Optional

from ai.capabilities.registry import CapabilityRegistry, get_capability_registry
from ai.capabilities.types import CachePolicy
from ai.contracts.common import CapabilityTypeEnum


def is_capability_cacheable(
    capability: CapabilityTypeEnum,
    registry: Optional[CapabilityRegistry] = None,
) -> bool:
    """
    Checks whether a capability allows invocation result caching based on
    its authoritative definition in the Capability Registry.
    """
    reg = registry or get_capability_registry()
    definition = reg.get(capability)
    if not definition:
        # Fail closed: unknown capability is never cached
        return False

    return definition.cache_policy != CachePolicy.NEVER


def should_evaluate_cache(
    capability: CapabilityTypeEnum,
    bypass_cache: bool = False,
    registry: Optional[CapabilityRegistry] = None,
) -> bool:
    """
    Determines whether a request should consult or populate the cache.
    Returns False if bypass_cache is requested or capability policy is NEVER.
    """
    if bypass_cache:
        return False
    return is_capability_cacheable(capability, registry=registry)
