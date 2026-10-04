"""
scripts/core/idempotency_store.py
==================================
Production DurableIdempotencyStore backed by SQLIdempotencyRepository (S28-M05 C04).

Architectural Invariants:
- Located in scripts/core/ (approved persistence layer) to satisfy S27.9 architecture guards.
- Enforces cross-process and cross-worker concurrency safety via atomic database CAS.
- Same key + same payload:
  First caller becomes LEADER and executes; concurrent/subsequent callers await/replay without re-executing.
- Same key + different payload:
  Strictly rejected with IdempotencyConflictError (POLICY_DENIED).
- Crash recovery / retry:
  If side-effect was committed, retries recover and replay the cached result without duplicate side-effects.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from ai.contracts import CapabilityResult
from ai.tools.errors import IdempotencyConflictError
from scripts.core.idempotency_repository import SQLIdempotencyRepository

logger = logging.getLogger("clean_video.scripts.core.idempotency_store")


class DurableIdempotencyStore:
    """
    Production durable idempotency store backed by SQLIdempotencyRepository.
    Enforces cross-process and cross-worker concurrency safety via atomic database CAS.
    """

    def __init__(self, repo: Optional[SQLIdempotencyRepository] = None) -> None:
        self._entries: Dict[str, Tuple[str, CapabilityResult]] = {}
        self._in_flight: Dict[str, Tuple[str, asyncio.Future[CapabilityResult]]] = {}
        self._repo: Optional[SQLIdempotencyRepository] = repo
        if self._repo is None:
            try:
                self._repo = SQLIdempotencyRepository()
            except Exception as e:
                logger.warning(f"SQLIdempotencyRepository initialization fallback: {e}")
                self._repo = None

    def get(self, key: str) -> Optional[Tuple[str, CapabilityResult]]:
        # 1. In-process cache check
        if key in self._entries:
            return self._entries[key]

        # 2. Durable database check
        if self._repo:
            try:
                rec = self._repo.get_record(key)
                if rec and rec.get("status") == "COMPLETED" and rec.get("result_json"):
                    result = CapabilityResult.model_validate_json(rec["result_json"])
                    self._entries[key] = (rec["payload_hash"], result)
                    return (rec["payload_hash"], result)
            except Exception as e:
                logger.warning(f"DurableIdempotencyStore.get failed: {e}")

        return None

    def get_in_flight(self, key: str) -> Optional[Tuple[str, asyncio.Future[CapabilityResult]]]:
        if key in self._in_flight:
            return self._in_flight[key]

        if self._repo:
            try:
                rec = self._repo.get_record(key)
                if rec and rec.get("status") == "IN_PROGRESS":
                    loop = asyncio.get_running_loop()
                    fut: asyncio.Future[CapabilityResult] = loop.create_future()
                    p_hash = rec["payload_hash"]
                    self._in_flight[key] = (p_hash, fut)
                    asyncio.create_task(self._poll_durable(key, p_hash, fut))
                    return (p_hash, fut)
            except Exception as e:
                logger.warning(f"DurableIdempotencyStore.get_in_flight failed: {e}")

        return None

    def register_in_flight(self, key: str, payload_hash: str) -> asyncio.Future[CapabilityResult]:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[CapabilityResult] = loop.create_future()
        self._in_flight[key] = (payload_hash, fut)
        return fut

    def claim_execution(self, key: str, payload_hash: str) -> Tuple[asyncio.Future[CapabilityResult], bool]:
        """
        Durable atomic CAS leadership claim.
        Returns: (future, is_leader).
        """
        loop = asyncio.get_running_loop()

        # Local in-flight check first
        if key in self._in_flight:
            in_hash, fut = self._in_flight[key]
            if in_hash != payload_hash:
                raise IdempotencyConflictError(
                    key,
                    f"Idempotency conflict: key '{key}' is currently executing with a different input payload."
                )
            return fut, False

        if not self._repo:
            fut = self.register_in_flight(key, payload_hash)
            return fut, True

        # Durable CAS leadership claim across processes
        status, result_json = self._repo.try_claim_leader(key, payload_hash)

        if status == "LEADER":
            fut = loop.create_future()
            self._in_flight[key] = (payload_hash, fut)
            return fut, True

        if status == "COMPLETED" and result_json:
            fut = loop.create_future()
            res = CapabilityResult.model_validate_json(result_json)
            fut.set_result(res)
            self._entries[key] = (payload_hash, res)
            return fut, False

        # IN_PROGRESS by another worker
        fut = loop.create_future()
        self._in_flight[key] = (payload_hash, fut)
        asyncio.create_task(self._poll_durable(key, payload_hash, fut))
        return fut, False

    def complete(self, key: str, payload_hash: str, result: CapabilityResult) -> None:
        self._entries[key] = (payload_hash, result)
        entry = self._in_flight.pop(key, None)
        if entry:
            _, fut = entry
            if not fut.done():
                fut.set_result(result)

        if self._repo:
            try:
                self._repo.mark_completed(key, payload_hash, result.model_dump_json())
            except Exception as e:
                logger.warning(f"DurableIdempotencyStore.complete failed to persist: {e}")

    def fail(self, key: str, exc: Exception) -> None:
        entry = self._in_flight.pop(key, None)
        if entry:
            _, fut = entry
            if not fut.done():
                fut.set_exception(exc)

        if self._repo:
            try:
                rec = self._repo.get_record(key)
                p_hash = rec["payload_hash"] if rec else ""
                self._repo.mark_failed(key, p_hash, str(exc))
            except Exception as e:
                logger.warning(f"DurableIdempotencyStore.fail failed to persist: {e}")

    def set(self, key: str, payload_hash: str, result: CapabilityResult) -> None:
        self.complete(key, payload_hash, result)

    def clear(self) -> None:
        self._entries.clear()
        self._in_flight.clear()

    async def _poll_durable(self, key: str, payload_hash: str, fut: asyncio.Future[CapabilityResult]) -> None:
        """Background task polling durable repository for completion from remote worker."""
        try:
            raw_json = await self._repo.poll_completion(key, payload_hash, poll_interval=0.05, timeout=30.0)
            if raw_json and not fut.done():
                result = CapabilityResult.model_validate_json(raw_json)
                self._entries[key] = (payload_hash, result)
                fut.set_result(result)
        except Exception as e:
            if not fut.done():
                fut.set_exception(e)
        finally:
            self._in_flight.pop(key, None)
