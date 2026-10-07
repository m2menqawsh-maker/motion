"""
ai/cache/service.py
===================
Authoritative Application-Level AI Artifact Cache & Request Coalescing Service (S27.12).

Invariants:
- Cache policy is capability-driven (governed by Capability Registry).
- Request coalescing coordinates across workers and processes via durable persistence.
- Output artifacts are durably stored in StorageService; cache records store output_ref.
- Cache publish is strictly atomic: artifact persistence precedes READY DB commit.
- Cache hits bypass provider calls, duplicate budget reservations, and duplicate provider costs.
- Malformed outputs and failed executions are never published as successful cache entries.
- Strict multi-tenant isolation across all cache keys, storage paths, and DB operations.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Optional, Tuple

from ai.cache.errors import (
    CacheError,
    CachePoisoningError,
    CacheTimeoutError,
    InvalidArtifactError,
    TenantIsolationViolationError,
)
from ai.cache.key import derive_canonical_cache_key
from ai.cache.policy import should_evaluate_cache
from ai.cache.repository import AICacheRepository
from ai.capabilities.registry import CapabilityRegistry, get_capability_registry
from ai.contracts.activity import (
    AIActivityRecord,
    ActivityStatus,
    IdempotencySemantics,
)
from ai.contracts.cache import (
    AICacheEntry,
    AICacheKeyParams,
    CacheEntryStatus,
)
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.errors import AIError
from ai.contracts.run import AIStep
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.activity import DurableActivityExecutor, settle_activity_cost
from scripts.core.storage.storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageService,
)

logger = logging.getLogger("ai.cache.service")


class AICacheService:
    """
    Authoritative coordinator for Application-Level AI Artifact Caching
    and Cross-Worker Request Coalescing.
    """

    def __init__(
        self,
        repository: AICacheRepository,
        storage_service: StorageService,
        capability_registry: Optional[CapabilityRegistry] = None,
        default_lease_duration_seconds: float = 30.0,
    ):
        self.repository = repository
        self.storage_service = storage_service
        self.capability_registry = capability_registry or get_capability_registry()
        self.default_lease_duration_seconds = default_lease_duration_seconds

    # -------------------------------------------------------------------------
    # Storage Artifact Helpers
    # -------------------------------------------------------------------------

    def _build_storage_key(
        self,
        workspace_id: str,
        capability: CapabilityTypeEnum,
        cache_key: str,
    ) -> str:
        return f"workspaces/{workspace_id}/cache/{capability.value.lower()}/{cache_key}.json"

    def _save_artifact(
        self,
        workspace_id: str,
        capability: CapabilityTypeEnum,
        cache_key: str,
        data: bytes,
    ) -> str:
        storage_key = self._build_storage_key(workspace_id, capability, cache_key)
        self.storage_service.put(
            key=storage_key,
            data=data,
            content_type="application/json",
        )
        return storage_key

    def _load_artifact(self, output_ref: str) -> bytes:
        try:
            return self.storage_service.get(output_ref)
        except (StorageNotFoundError, StorageError) as exc:
            raise InvalidArtifactError(f"Failed to load cached artifact from '{output_ref}': {exc}") from exc

    # -------------------------------------------------------------------------
    # Direct Cache Access & Publication
    # -------------------------------------------------------------------------

    def get(self, workspace_id: str, cache_key: str) -> Optional[AICacheEntry]:
        """
        Direct read-through lookup for an authoritative cached entry scoped to workspace_id.
        Returns entry if status is READY and not expired; otherwise None.
        """
        entry = self.repository.get_entry(workspace_id, cache_key)
        if entry and entry.status == CacheEntryStatus.READY:
            now_dt = datetime.now(timezone.utc)
            if entry.expires_at is None or entry.expires_at > now_dt:
                return entry
        return None

    def publish(
        self,
        workspace_id: str,
        cache_key: str,
        output_ref: str,
        content_hash: Optional[str] = None,
        confidence: Optional[float] = None,
        producer: Optional[str] = None,
        model: Optional[str] = None,
        model_version: Optional[str] = None,
        capability: CapabilityTypeEnum = CapabilityTypeEnum.VISION,
        ttl_seconds: Optional[int] = None,
    ) -> Optional[AICacheEntry]:
        """
        Direct publication of an already durably stored artifact into the authoritative cache.
        """
        now_dt = datetime.now(timezone.utc)
        expires_at = now_dt + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        owner_id = f"direct_{uuid.uuid4().hex[:8]}"
        lease_token = f"lease_{uuid.uuid4().hex[:12]}"
        params = AICacheKeyParams(
            workspace_id=workspace_id,
            capability=capability,
            content_hash=content_hash,
            model=model,
            model_version=model_version,
        )
        won, entry = self.repository.claim_execution_ownership(
            workspace_id=workspace_id,
            cache_key=cache_key,
            owner_id=owner_id,
            lease_token=lease_token,
            lease_duration_seconds=self.default_lease_duration_seconds,
            params=params,
            expires_at=expires_at,
        )
        if won or (entry and entry.status != CacheEntryStatus.READY):
            return self.repository.complete_entry(
                workspace_id=workspace_id,
                cache_key=cache_key,
                owner_id=owner_id,
                lease_token=lease_token,
                output_ref=output_ref,
                producer=producer,
                model=model,
                model_version=model_version,
                expires_at=expires_at,
            )
        return entry

    # -------------------------------------------------------------------------
    # High-Level Capability Cache Flow
    # -------------------------------------------------------------------------

    def get_or_compute(
        self,
        params: AICacheKeyParams,
        compute_fn: Callable[[], Tuple[CapabilityResult, bytes]],
        ttl_seconds: Optional[int] = None,
        wait_timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.05,
        bypass_cache: bool = False,
        worker_id: Optional[str] = None,
    ) -> Tuple[CapabilityResult, bool]:
        """
        Retrieves a cached CapabilityResult or coordinates a single-flight execution.

        Returns:
            Tuple of (CapabilityResult, was_cache_hit: bool)
        """
        # 1. Capability Cache Policy Guard
        if not should_evaluate_cache(params.capability, bypass_cache=bypass_cache, registry=self.capability_registry):
            result, _ = compute_fn()
            return result, False

        # 2. Derive canonical deterministic cache key
        cache_key = derive_canonical_cache_key(params)
        workspace_id = params.workspace_id

        # 3. Fast-path lookup for existing valid HIT
        existing_entry = self.repository.get_entry(workspace_id, cache_key)
        now_dt = datetime.now(timezone.utc)

        if existing_entry and existing_entry.status == CacheEntryStatus.READY:
            if existing_entry.expires_at is None or existing_entry.expires_at > now_dt:
                try:
                    artifact_bytes = self._load_artifact(existing_entry.output_ref or "")
                    cached_result = CapabilityResult.model_validate_json(artifact_bytes)
                    logger.debug("Cache HIT for key '%s' in workspace '%s'", cache_key, workspace_id)
                    return cached_result, True
                except (InvalidArtifactError, Exception) as exc:
                    logger.warning(
                        "Cached artifact at '%s' is missing or corrupted: %s. Invalidating stale entry.",
                        existing_entry.output_ref,
                        exc,
                    )
                    self.repository.invalidate_entry(workspace_id, cache_key)

        # 4. Request Coalescing (Atomic Execution Claim)
        owner_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        lease_token = f"lease_{uuid.uuid4().hex[:12]}"
        expires_at = now_dt + timedelta(seconds=ttl_seconds) if ttl_seconds else None

        won, entry = self.repository.claim_execution_ownership(
            workspace_id=workspace_id,
            cache_key=cache_key,
            owner_id=owner_id,
            lease_token=lease_token,
            lease_duration_seconds=self.default_lease_duration_seconds,
            params=params,
            expires_at=expires_at,
        )

        if won:
            # -----------------------------------------------------------------
            # OWNER PATH: Executes provider, durably stores artifact, commits READY
            # -----------------------------------------------------------------
            try:
                result, artifact_bytes = compute_fn()

                # Cache poisoning protection: verify outcome and output coherence
                if result.status != CapabilityStatus.SUCCESS:
                    err = result.error or AIError.internal_error(
                        message=f"Capability execution resulted in status {result.status.value}; not cacheable."
                    )
                    self.repository.mark_entry_failed(workspace_id, cache_key, owner_id, lease_token, err)
                    return result, False

                if result.output_data is None:
                    err = AIError.internal_error(
                        message="CapabilityResult has SUCCESS status but missing output_data; rejected from cache."
                    )
                    self.repository.mark_entry_failed(workspace_id, cache_key, owner_id, lease_token, err)
                    raise CachePoisoningError("Cannot cache CapabilityResult with empty output_data")

                # Atomic Publish:
                # Step A: Durably persist artifact to StorageService
                output_ref = self._save_artifact(workspace_id, params.capability, cache_key, artifact_bytes)

                # Step B: Commit cache entry as READY
                self.repository.complete_entry(
                    workspace_id=workspace_id,
                    cache_key=cache_key,
                    owner_id=owner_id,
                    lease_token=lease_token,
                    output_ref=output_ref,
                    producer=result.provenance.provider_id if result.provenance else None,
                    model=result.provenance.model_id if result.provenance else None,
                    model_version=params.model_version,
                    expires_at=expires_at,
                )
                return result, False

            except Exception as exc:
                if isinstance(exc, AIError):
                    ai_err = exc
                else:
                    ai_err = AIError.internal_error(message=f"Computation failed: {str(exc)}")
                self.repository.mark_entry_failed(workspace_id, cache_key, owner_id, lease_token, ai_err)
                raise

        else:
            # -----------------------------------------------------------------
            # WAITER PATH: Shares in-flight execution, polls durable state
            # -----------------------------------------------------------------
            deadline = time.time() + wait_timeout_seconds
            while time.time() < deadline:
                time.sleep(poll_interval_seconds)
                current = self.repository.get_entry(workspace_id, cache_key)
                if not current:
                    # Invalidation occurred; retry claim
                    return self.get_or_compute(
                        params,
                        compute_fn,
                        ttl_seconds=ttl_seconds,
                        wait_timeout_seconds=max(0.5, deadline - time.time()),
                        poll_interval_seconds=poll_interval_seconds,
                        bypass_cache=bypass_cache,
                        worker_id=worker_id,
                    )

                if current.status == CacheEntryStatus.READY:
                    try:
                        artifact_bytes = self._load_artifact(current.output_ref or "")
                        cached_result = CapabilityResult.model_validate_json(artifact_bytes)
                        return cached_result, True
                    except Exception:
                        self.repository.invalidate_entry(workspace_id, cache_key)
                        return self.get_or_compute(
                            params,
                            compute_fn,
                            ttl_seconds=ttl_seconds,
                            wait_timeout_seconds=max(0.5, deadline - time.time()),
                            poll_interval_seconds=poll_interval_seconds,
                            bypass_cache=bypass_cache,
                            worker_id=worker_id,
                        )

                elif current.status == CacheEntryStatus.FAILED:
                    err_msg = current.error.message if current.error else "Coalesced execution failed"
                    raise CacheError(f"Coalesced execution failed for cache key '{cache_key}': {err_msg}")

                elif current.status == CacheEntryStatus.IN_FLIGHT:
                    curr_dt = datetime.now(timezone.utc)
                    if current.lease_expires_at and current.lease_expires_at < curr_dt:
                        # Owner crashed! Re-enter get_or_compute to steal lease and recover
                        return self.get_or_compute(
                            params,
                            compute_fn,
                            ttl_seconds=ttl_seconds,
                            wait_timeout_seconds=max(0.5, deadline - time.time()),
                            poll_interval_seconds=poll_interval_seconds,
                            bypass_cache=bypass_cache,
                            worker_id=worker_id,
                        )

            raise CacheTimeoutError(
                f"Timed out waiting ({wait_timeout_seconds}s) for coalesced cache result for '{cache_key}'"
            )

    # -------------------------------------------------------------------------
    # Durable Activity Integration (AI-10)
    # -------------------------------------------------------------------------

    def execute_cached_activity(
        self,
        step: AIStep,
        workspace_id: str,
        params: AICacheKeyParams,
        activity_executor: DurableActivityExecutor,
        fn: Callable[[str], Tuple[str, UsageRecord, CostEstimate, Optional[str]]],
        semantics: IdempotencySemantics = IdempotencySemantics.EFFECTIVELY_ONCE,
        reservation_id: Optional[str] = None,
        native_idempotency_supported: bool = False,
        crash_injector: Optional[Callable[[str], None]] = None,
        ttl_seconds: Optional[int] = None,
        wait_timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.05,
        worker_id: Optional[str] = None,
    ) -> Tuple[AIActivityRecord, bool]:
        """
        Executes an external activity via DurableActivityExecutor, with full
        Application-Level Caching and Cross-Worker Request Coalescing.

        Invariants:
        - If cache HIT: zero provider execution, zero budget reservation, zero provider cost.
        - If cache MISS: one worker acquires claim, executes durable activity, publishes cache.
        - Waiters share the logical result and receive SUCCEEDED AIActivityRecord without duplicate cost.
        """
        # 1. Capability Cache Policy Guard
        if not should_evaluate_cache(params.capability, registry=self.capability_registry):
            record = activity_executor.execute_activity(
                step=step,
                workspace_id=workspace_id,
                fn=fn,
                semantics=semantics,
                reservation_id=reservation_id,
                native_idempotency_supported=native_idempotency_supported,
                crash_injector=crash_injector,
            )
            return record, False

        # 2. Canonical cache key
        cache_key = derive_canonical_cache_key(params)
        now_dt = datetime.now(timezone.utc)

        # 3. Fast-path lookup for existing READY entry
        existing_entry = self.repository.get_entry(workspace_id, cache_key)
        if existing_entry and existing_entry.status == CacheEntryStatus.READY:
            if existing_entry.expires_at is None or existing_entry.expires_at > now_dt:
                if existing_entry.output_ref and self.storage_service.exists(existing_entry.output_ref):
                    # Cache HIT! Construct activity record with ZERO provider cost
                    cached_record = AIActivityRecord(
                        activity_id=f"act_cached_{uuid.uuid4().hex[:12]}",
                        run_id=step.run_id,
                        step_id=step.step_id,
                        idempotency_key=activity_executor.derive_idempotency_key(step),
                        status=ActivityStatus.SUCCEEDED,
                        semantics=semantics,
                        started_at=existing_entry.created_at,
                        completed_at=existing_entry.created_at,
                        provider=existing_entry.producer,
                        model=existing_entry.model,
                        remote_operation_ref=None,
                        output_ref=existing_entry.output_ref,
                        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.00"),
                        usage=UsageRecord(),
                        cost_settled=True,
                        reservation_id=None,
                        created_at=existing_entry.created_at,
                    )
                    return cached_record, True
                else:
                    self.repository.invalidate_entry(workspace_id, cache_key)

        # 4. Request Coalescing (Claim Execution Ownership)
        owner_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        lease_token = f"lease_{uuid.uuid4().hex[:12]}"
        expires_at = now_dt + timedelta(seconds=ttl_seconds) if ttl_seconds else None

        won, entry = self.repository.claim_execution_ownership(
            workspace_id=workspace_id,
            cache_key=cache_key,
            owner_id=owner_id,
            lease_token=lease_token,
            lease_duration_seconds=self.default_lease_duration_seconds,
            params=params,
            expires_at=expires_at,
        )

        if won:
            # OWNER PATH: Executes Durable Activity (reserves budget, calls provider, settles cost)
            shared_generation = entry.generation if entry and entry.generation is not None else 1
            shared_idempotency_key = (
                entry.activity_idempotency_key
                if entry and entry.activity_idempotency_key
                else f"cache_idem_{workspace_id}_{cache_key}_g{shared_generation}"
            )

            # RECONCILIATION: Check if prior worker already succeeded this activity before crashing
            reconciled_activity = None
            if entry and entry.activity_id:
                reconciled_activity = activity_executor.repository.get_activity(
                    activity_id=entry.activity_id,
                    workspace_id=workspace_id,
                )
            if not reconciled_activity:
                reconciled_activity = activity_executor.repository.get_activity_by_idempotency_key(
                    workspace_id=workspace_id,
                    idempotency_key=shared_idempotency_key,
                )

            if (
                reconciled_activity
                and reconciled_activity.status == ActivityStatus.SUCCEEDED
                and reconciled_activity.output_ref
                and self.storage_service.exists(reconciled_activity.output_ref)
            ):
                logger.info(
                    "Reconciled existing completed durable activity '%s' for cache key '%s'",
                    reconciled_activity.activity_id,
                    cache_key,
                )
                if not reconciled_activity.cost_settled:
                    settle_activity_cost(
                        reconciled_activity,
                        activity_executor.repository,
                        activity_executor.budget_service,
                    )

                self.repository.complete_entry(
                    workspace_id=workspace_id,
                    cache_key=cache_key,
                    owner_id=owner_id,
                    lease_token=lease_token,
                    output_ref=reconciled_activity.output_ref,
                    producer=reconciled_activity.provider,
                    model=reconciled_activity.model,
                    model_version=params.model_version,
                    expires_at=expires_at,
                    activity_id=reconciled_activity.activity_id,
                )

                reconciled_record = AIActivityRecord(
                    activity_id=f"act_reconciled_{uuid.uuid4().hex[:12]}",
                    run_id=step.run_id,
                    step_id=step.step_id,
                    idempotency_key=shared_idempotency_key,
                    status=ActivityStatus.SUCCEEDED,
                    semantics=semantics,
                    started_at=reconciled_activity.started_at,
                    completed_at=reconciled_activity.completed_at,
                    provider=reconciled_activity.provider,
                    model=reconciled_activity.model,
                    remote_operation_ref=reconciled_activity.remote_operation_ref,
                    output_ref=reconciled_activity.output_ref,
                    cost=CostEstimate(estimated_cost="0.00", actual_cost="0.00"),
                    usage=UsageRecord(),
                    cost_settled=True,
                    reservation_id=None,
                    created_at=reconciled_activity.created_at,
                )
                return reconciled_record, False

            try:
                # Use shared_idempotency_key so logical activity survives across run/step changes
                shared_step = step.model_copy(update={"idempotency_key": shared_idempotency_key})

                record = activity_executor.execute_activity(
                    step=shared_step,
                    workspace_id=workspace_id,
                    fn=fn,
                    semantics=semantics,
                    reservation_id=reservation_id,
                    native_idempotency_supported=native_idempotency_supported,
                    crash_injector=crash_injector,
                )

                # Link activity_id to cache entry
                self.repository.link_activity(
                    workspace_id=workspace_id,
                    cache_key=cache_key,
                    owner_id=owner_id,
                    lease_token=lease_token,
                    activity_id=record.activity_id,
                    activity_idempotency_key=shared_idempotency_key,
                )

                if record.status != ActivityStatus.SUCCEEDED or not record.output_ref:
                    err = record.error or AIError.internal_error(
                        message="Durable activity failed; cannot commit to cache."
                    )
                    self.repository.mark_entry_failed(workspace_id, cache_key, owner_id, lease_token, err)
                    return record, False

                # Atomic publish: output is already durable at record.output_ref
                self.repository.complete_entry(
                    workspace_id=workspace_id,
                    cache_key=cache_key,
                    owner_id=owner_id,
                    lease_token=lease_token,
                    output_ref=record.output_ref,
                    producer=record.provider,
                    model=record.model,
                    model_version=params.model_version,
                    expires_at=expires_at,
                    activity_id=record.activity_id,
                )
                return record, False

            except Exception as exc:
                if isinstance(exc, AIError):
                    ai_err = exc
                else:
                    ai_err = AIError.internal_error(message=f"Durable activity execution failed: {str(exc)}")
                self.repository.mark_entry_failed(workspace_id, cache_key, owner_id, lease_token, ai_err)
                raise

        else:
            # WAITER PATH: Waits for owner to complete durable activity
            deadline = time.time() + wait_timeout_seconds
            while time.time() < deadline:
                time.sleep(poll_interval_seconds)
                current = self.repository.get_entry(workspace_id, cache_key)
                if not current:
                    return self.execute_cached_activity(
                        step=step,
                        workspace_id=workspace_id,
                        params=params,
                        activity_executor=activity_executor,
                        fn=fn,
                        semantics=semantics,
                        reservation_id=reservation_id,
                        native_idempotency_supported=native_idempotency_supported,
                        crash_injector=crash_injector,
                        ttl_seconds=ttl_seconds,
                        wait_timeout_seconds=max(0.5, deadline - time.time()),
                        poll_interval_seconds=poll_interval_seconds,
                        worker_id=worker_id,
                    )

                if current.status == CacheEntryStatus.READY:
                    if current.output_ref and self.storage_service.exists(current.output_ref):
                        cached_record = AIActivityRecord(
                            activity_id=f"act_cached_{uuid.uuid4().hex[:12]}",
                            run_id=step.run_id,
                            step_id=step.step_id,
                            idempotency_key=activity_executor.derive_idempotency_key(step),
                            status=ActivityStatus.SUCCEEDED,
                            semantics=semantics,
                            started_at=current.created_at,
                            completed_at=current.created_at,
                            provider=current.producer,
                            model=current.model,
                            remote_operation_ref=None,
                            output_ref=current.output_ref,
                            cost=CostEstimate(estimated_cost="0.00", actual_cost="0.00"),
                            usage=UsageRecord(),
                            cost_settled=True,
                            reservation_id=None,
                            created_at=current.created_at,
                        )
                        return cached_record, True
                    else:
                        self.repository.invalidate_entry(workspace_id, cache_key)
                        return self.execute_cached_activity(
                            step=step,
                            workspace_id=workspace_id,
                            params=params,
                            activity_executor=activity_executor,
                            fn=fn,
                            semantics=semantics,
                            reservation_id=reservation_id,
                            native_idempotency_supported=native_idempotency_supported,
                            crash_injector=crash_injector,
                            ttl_seconds=ttl_seconds,
                            wait_timeout_seconds=max(0.5, deadline - time.time()),
                            poll_interval_seconds=poll_interval_seconds,
                            worker_id=worker_id,
                        )

                elif current.status == CacheEntryStatus.FAILED:
                    err_msg = current.error.message if current.error else "Coalesced execution failed"
                    raise CacheError(f"Coalesced execution failed for cache key '{cache_key}': {err_msg}")

                elif current.status == CacheEntryStatus.IN_FLIGHT:
                    curr_dt = datetime.now(timezone.utc)
                    if current.lease_expires_at and current.lease_expires_at < curr_dt:
                        # Owner crashed! Re-enter to steal lease
                        return self.execute_cached_activity(
                            step=step,
                            workspace_id=workspace_id,
                            params=params,
                            activity_executor=activity_executor,
                            fn=fn,
                            semantics=semantics,
                            reservation_id=reservation_id,
                            native_idempotency_supported=native_idempotency_supported,
                            crash_injector=crash_injector,
                            ttl_seconds=ttl_seconds,
                            wait_timeout_seconds=max(0.5, deadline - time.time()),
                            poll_interval_seconds=poll_interval_seconds,
                            worker_id=worker_id,
                        )

            raise CacheTimeoutError(
                f"Timed out waiting ({wait_timeout_seconds}s) for coalesced durable activity result for '{cache_key}'"
            )
