"""
ai/cache/__init__.py
====================
AI Artifact Cache & Request Coalescing subsystem (S27.12).

Invariants:
- High-level domain cache service coordinating durable persistence and object storage.
- Request coalescing across workers and processes preventing duplicate expensive calls.
- Strict multi-tenant isolation and fail-closed security.
"""

from __future__ import annotations

from ai.contracts.cache import (
    AICacheEntry,
    AICacheKeyParams,
    CacheEntryStatus,
    CacheEntryStatusEnum,
)
from ai.cache.errors import (
    CacheError,
    CacheEntryNotFoundError,
    CachePoisoningError,
    CacheTimeoutError,
    InvalidArtifactError,
    StaleCacheLeaseError,
    TenantIsolationViolationError,
)
from ai.cache.key import (
    compute_input_hash,
    compute_settings_hash,
    derive_canonical_cache_key,
    normalize_canonical_json,
)
from ai.cache.policy import (
    is_capability_cacheable,
    should_evaluate_cache,
)
from ai.cache.repository import AICacheRepository
from ai.cache.service import AICacheService

__all__ = [
    # Contracts
    "AICacheEntry",
    "AICacheKeyParams",
    "CacheEntryStatus",
    "CacheEntryStatusEnum",
    # Service & Repository
    "AICacheService",
    "AICacheRepository",
    # Key & Normalization
    "derive_canonical_cache_key",
    "compute_input_hash",
    "compute_settings_hash",
    "normalize_canonical_json",
    # Policy
    "is_capability_cacheable",
    "should_evaluate_cache",
    # Errors
    "CacheError",
    "CacheEntryNotFoundError",
    "CachePoisoningError",
    "CacheTimeoutError",
    "InvalidArtifactError",
    "StaleCacheLeaseError",
    "TenantIsolationViolationError",
]
