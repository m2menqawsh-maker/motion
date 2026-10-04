"""
ai/cache/errors.py
==================
Exception taxonomy for the AI Artifact Cache subsystem (S27.12).

Invariants:
- Never leaks internal credentials or raw infrastructure connection strings.
- Structured, typed exceptions for stale leases, timeouts, poisoning, and tenant violations.
"""

from __future__ import annotations


class CacheError(Exception):
    """Base exception for all AI cache subsystem errors."""
    pass


class StaleCacheLeaseError(CacheError):
    """Raised when an in-flight worker's lease expired or was superseded by another worker."""
    pass


class CacheEntryNotFoundError(CacheError):
    """Raised when a required cache entry does not exist."""
    pass


class CacheTimeoutError(CacheError):
    """Raised when waiting for a coalesced in-flight operation exceeds the allowed deadline."""
    pass


class CachePoisoningError(CacheError):
    """Raised when an invalid, malformed, or unverified output attempts to enter the cache."""
    pass


class TenantIsolationViolationError(CacheError):
    """Raised when an unauthorized cross-workspace cache access or leak attempt is detected."""
    pass


class InvalidArtifactError(CacheError):
    """Raised when a cached output_ref cannot be retrieved or contains corrupt payload data."""
    pass
