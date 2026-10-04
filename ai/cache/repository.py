"""
ai/cache/repository.py
======================
Abstract repository boundary for AI Artifact Cache persistence (S27.12).

Invariants:
- Abstract interface only; never imports raw DB drivers or executes SQL in ai/* (ADR-004 DEC-01).
- Concrete implementations in scripts/core/ handle SQL transactions, row locking, and atomic CAS.
- Guarantees multi-tenant isolation across all cache operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Tuple

from ai.contracts.cache import AICacheEntry, AICacheKeyParams
from ai.contracts.errors import AIError


class AICacheRepository(ABC):
    """
    Authoritative persistence boundary for AI Artifact Cache records,
    atomic worker execution claims, and lease fencing.
    """

    @abstractmethod
    def get_entry(self, workspace_id: str, cache_key: str) -> Optional[AICacheEntry]:
        """
        Retrieves a cache entry by key, strictly scoped to workspace_id.
        Returns None if not found or belongs to a different workspace.
        """
        raise NotImplementedError

    @abstractmethod
    def claim_execution_ownership(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        lease_duration_seconds: float,
        params: AICacheKeyParams,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[AICacheEntry]]:
        """
        Atomically attempts to acquire execution ownership for a cache miss:
        - If no entry exists: creates IN_FLIGHT entry leased to owner_id. Returns (True, new_entry).
        - If entry is READY and fresh: returns (False, existing_entry).
        - If entry is READY but expired (TTL): atomically re-claims IN_FLIGHT. Returns (True, updated_entry).
        - If entry is IN_FLIGHT with active lease: returns (False, existing_entry) [waiter].
        - If entry is IN_FLIGHT with expired lease (crashed owner): atomically steals lease. Returns (True, updated_entry).
        - If entry is FAILED: atomically retries IN_FLIGHT. Returns (True, updated_entry).
        """
        raise NotImplementedError

    @abstractmethod
    def renew_lease(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        lease_duration_seconds: float,
    ) -> bool:
        """
        Renews an active in-flight execution lease.
        Returns True if heartbeat succeeded, False if lease expired or was superseded.
        """
        raise NotImplementedError

    @abstractmethod
    def link_activity(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        activity_id: str,
        activity_idempotency_key: str,
    ) -> bool:
        """
        Links an in-flight durable activity to the leased cache entry.
        Fenced by owner_id and lease_token.
        """
        raise NotImplementedError

    @abstractmethod
    def complete_entry(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        output_ref: str,
        producer: Optional[str] = None,
        model: Optional[str] = None,
        model_version: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        activity_id: Optional[str] = None,
    ) -> AICacheEntry:
        """
        Atomically commits a completed cache entry with status READY.
        Must be fenced by owner_id and lease_token: raises StaleCacheLeaseError
        if the worker lost ownership due to expiry or takeover.
        """
        raise NotImplementedError

    @abstractmethod
    def mark_entry_failed(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        error: AIError,
    ) -> bool:
        """
        Marks an in-flight entry as FAILED with structured error details,
        releasing the lease token so waiting requests can fail fast or retry.
        """
        raise NotImplementedError

    @abstractmethod
    def invalidate_entry(self, workspace_id: str, cache_key: str) -> bool:
        """
        Permanently removes a cache entry within a workspace boundary.
        Returns True if deleted, False if entry did not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def invalidate_workspace(self, workspace_id: str) -> int:
        """
        Invalidates all cached entries belonging to the specified workspace.
        Returns count of purged records.
        """
        raise NotImplementedError
