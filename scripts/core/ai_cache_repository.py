"""
scripts/core/ai_cache_repository.py
====================================
SQL-backed persistent implementation of AICacheRepository (S27.12).

Architectural Boundaries (ADR-004 DEC-01):
- Implemented in scripts/core/ (approved persistence layer) to satisfy S27.0 architecture guards.
- DatabaseEngine handles connection management, SQLite WAL mode, and transactions.
- Implements atomic CAS worker claims, monotonic lease fencing, and multi-tenant isolation.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from ai.cache.errors import StaleCacheLeaseError, TenantIsolationViolationError
from ai.cache.key import compute_input_hash
from ai.cache.repository import AICacheRepository
from ai.contracts.cache import AICacheEntry, AICacheKeyParams, CacheEntryStatus
from ai.contracts.common import CapabilityType
from ai.contracts.errors import AIError
from scripts.core.database import DatabaseEngine, get_database_engine

logger = logging.getLogger("scripts.core.ai_cache_repository")

CACHE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_cache_entries (
    cache_key TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    output_ref TEXT,
    producer TEXT,
    model TEXT,
    model_version TEXT,
    contract_version TEXT NOT NULL DEFAULT '1.0.0',
    prompt_version TEXT NOT NULL DEFAULT '1.0.0',
    analysis_version TEXT NOT NULL DEFAULT '1.0.0',
    created_at TEXT NOT NULL,
    expires_at TEXT,
    owner_id TEXT,
    lease_token TEXT,
    lease_acquired_at TEXT,
    lease_expires_at TEXT,
    activity_id TEXT,
    activity_idempotency_key TEXT,
    generation INTEGER NOT NULL DEFAULT 1,
    error_json TEXT,
    PRIMARY KEY (workspace_id, cache_key)
);
CREATE INDEX IF NOT EXISTS idx_ai_cache_ws_status ON ai_cache_entries(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_cache_expires ON ai_cache_entries(expires_at);
"""


def _iso_to_dt(iso_str: Optional[str]) -> Optional[datetime]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class SQLAICacheRepository(AICacheRepository):
    """
    Production-grade persistent repository for AI Artifact Cache.
    Supports atomic CAS worker claims, lease fencing, and tenant boundary enforcement.
    """

    def __init__(self, engine: Optional[DatabaseEngine] = None):
        self.engine = engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.engine.transaction("IMMEDIATE") as conn:
            for statement in CACHE_SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

            # Defensive migration for existing SQLite tables
            cursor = conn.execute("PRAGMA table_info(ai_cache_entries)")
            cols = {row["name"] for row in cursor.fetchall()}
            if "activity_id" not in cols:
                conn.execute("ALTER TABLE ai_cache_entries ADD COLUMN activity_id TEXT")
            if "activity_idempotency_key" not in cols:
                conn.execute("ALTER TABLE ai_cache_entries ADD COLUMN activity_idempotency_key TEXT")
            if "generation" not in cols:
                conn.execute("ALTER TABLE ai_cache_entries ADD COLUMN generation INTEGER NOT NULL DEFAULT 1")

    def _row_to_entry(self, row: Any) -> AICacheEntry:
        error_obj: Optional[AIError] = None
        if row["error_json"]:
            try:
                error_obj = AIError.model_validate_json(row["error_json"])
            except Exception:
                pass

        keys = row.keys()
        activity_id = row["activity_id"] if "activity_id" in keys else None
        activity_idempotency_key = row["activity_idempotency_key"] if "activity_idempotency_key" in keys else None
        generation = row["generation"] if "generation" in keys and row["generation"] is not None else 1

        return AICacheEntry(
            cache_key=row["cache_key"],
            workspace_id=row["workspace_id"],
            capability=CapabilityType(row["capability"]),
            input_hash=row["input_hash"],
            status=CacheEntryStatus(row["status"]),
            output_ref=row["output_ref"],
            producer=row["producer"],
            model=row["model"],
            model_version=row["model_version"],
            contract_version=row["contract_version"],
            prompt_version=row["prompt_version"],
            analysis_version=row["analysis_version"],
            created_at=_iso_to_dt(row["created_at"]) or datetime.now(timezone.utc),
            expires_at=_iso_to_dt(row["expires_at"]),
            owner_id=row["owner_id"],
            lease_token=row["lease_token"],
            lease_expires_at=_iso_to_dt(row["lease_expires_at"]),
            activity_id=activity_id,
            activity_idempotency_key=activity_idempotency_key,
            generation=generation,
            error=error_obj,
        )

    def get_entry(self, workspace_id: str, cache_key: str) -> Optional[AICacheEntry]:
        if not workspace_id:
            raise TenantIsolationViolationError("workspace_id cannot be empty")

        with self.engine.transaction("DEFERRED") as conn:
            cursor = conn.execute(
                "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                (workspace_id, cache_key),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_entry(row)

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
        if not workspace_id or workspace_id != params.workspace_id:
            raise TenantIsolationViolationError(
                f"Workspace mismatch: caller '{workspace_id}' vs params '{params.workspace_id}'"
            )

        now_dt = datetime.now(timezone.utc)
        now_iso = _dt_to_iso(now_dt)
        lease_deadline_dt = now_dt + timedelta(seconds=lease_duration_seconds)
        lease_deadline_iso = _dt_to_iso(lease_deadline_dt)
        expires_iso = _dt_to_iso(expires_at)
        input_hash = compute_input_hash(params.input_data, params.content_hash)

        # Retry loop for concurrency under high load
        max_retries = 10
        for attempt in range(max_retries):
            try:
                with self.engine.transaction("IMMEDIATE") as conn:
                    cursor = conn.execute(
                        "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                        (workspace_id, cache_key),
                    )
                    row = cursor.fetchone()

                    # Case 1: No entry exists -> Atomically insert new IN_FLIGHT entry
                    if not row:
                        initial_gen = 1
                        initial_idem = f"cache_idem_{workspace_id}_{cache_key}_g{initial_gen}"
                        conn.execute(
                            """
                            INSERT INTO ai_cache_entries (
                                cache_key, workspace_id, capability, input_hash,
                                status, output_ref, producer, model, model_version,
                                contract_version, prompt_version, analysis_version,
                                created_at, expires_at, owner_id, lease_token,
                                lease_acquired_at, lease_expires_at, activity_id,
                                activity_idempotency_key, generation, error_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                cache_key,
                                workspace_id,
                                params.capability.value,
                                input_hash,
                                CacheEntryStatus.IN_FLIGHT.value,
                                None,
                                None,
                                params.model,
                                params.model_version,
                                params.contract_version,
                                params.prompt_version,
                                params.analysis_version,
                                now_iso,
                                expires_iso,
                                owner_id,
                                lease_token,
                                now_iso,
                                lease_deadline_iso,
                                None,
                                initial_idem,
                                initial_gen,
                                None,
                            ),
                        )
                        cursor = conn.execute(
                            "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                            (workspace_id, cache_key),
                        )
                        new_row = cursor.fetchone()
                        return True, self._row_to_entry(new_row)

                    # Case 2: Existing READY entry
                    if row["status"] == CacheEntryStatus.READY.value:
                        entry_expires = _iso_to_dt(row["expires_at"])
                        if entry_expires is not None and entry_expires < now_dt:
                            # Entry is stale/expired -> Re-claim execution ownership with incremented generation
                            curr_gen = row["generation"] if "generation" in row.keys() and row["generation"] is not None else 1
                            next_gen = curr_gen + 1
                            next_idem = f"cache_idem_{workspace_id}_{cache_key}_g{next_gen}"
                            conn.execute(
                                """
                                UPDATE ai_cache_entries
                                SET status = ?, output_ref = NULL, error_json = NULL,
                                    owner_id = ?, lease_token = ?, lease_acquired_at = ?,
                                    lease_expires_at = ?, expires_at = ?,
                                    activity_id = NULL, activity_idempotency_key = ?,
                                    generation = ?
                                WHERE workspace_id = ? AND cache_key = ?
                                """,
                                (
                                    CacheEntryStatus.IN_FLIGHT.value,
                                    owner_id,
                                    lease_token,
                                    now_iso,
                                    lease_deadline_iso,
                                    expires_iso,
                                    next_idem,
                                    next_gen,
                                    workspace_id,
                                    cache_key,
                                ),
                            )
                            cursor = conn.execute(
                                "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                                (workspace_id, cache_key),
                            )
                            updated_row = cursor.fetchone()
                            return True, self._row_to_entry(updated_row)
                        else:
                            # Fresh valid hit ready
                            return False, self._row_to_entry(row)

                    # Case 3: Existing IN_FLIGHT entry
                    if row["status"] == CacheEntryStatus.IN_FLIGHT.value:
                        active_deadline = _iso_to_dt(row["lease_expires_at"])
                        if active_deadline is not None and active_deadline < now_dt:
                            # Owner crashed or lease expired -> Atomically steal lease while PRESERVING generation & shared identity
                            conn.execute(
                                """
                                UPDATE ai_cache_entries
                                SET owner_id = ?, lease_token = ?, lease_acquired_at = ?,
                                    lease_expires_at = ?
                                WHERE workspace_id = ? AND cache_key = ?
                                """,
                                (
                                    owner_id,
                                    lease_token,
                                    now_iso,
                                    lease_deadline_iso,
                                    workspace_id,
                                    cache_key,
                                ),
                            )
                            cursor = conn.execute(
                                "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                                (workspace_id, cache_key),
                            )
                            updated_row = cursor.fetchone()
                            return True, self._row_to_entry(updated_row)
                        else:
                            # Active lease held by another worker -> Waiter
                            return False, self._row_to_entry(row)

                    # Case 4: Existing FAILED entry -> Allow fresh retry with incremented generation
                    if row["status"] == CacheEntryStatus.FAILED.value:
                        curr_gen = row["generation"] if "generation" in row.keys() and row["generation"] is not None else 1
                        next_gen = curr_gen + 1
                        next_idem = f"cache_idem_{workspace_id}_{cache_key}_g{next_gen}"
                        conn.execute(
                            """
                            UPDATE ai_cache_entries
                            SET status = ?, error_json = NULL, output_ref = NULL,
                                owner_id = ?, lease_token = ?, lease_acquired_at = ?,
                                lease_expires_at = ?, expires_at = ?,
                                activity_id = NULL, activity_idempotency_key = ?,
                                generation = ?
                            WHERE workspace_id = ? AND cache_key = ?
                            """,
                            (
                                CacheEntryStatus.IN_FLIGHT.value,
                                owner_id,
                                lease_token,
                                now_iso,
                                lease_deadline_iso,
                                expires_iso,
                                next_idem,
                                next_gen,
                                workspace_id,
                                cache_key,
                            ),
                        )
                        cursor = conn.execute(
                            "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                            (workspace_id, cache_key),
                        )
                        updated_row = cursor.fetchone()
                        return True, self._row_to_entry(updated_row)

            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < max_retries - 1:
                    time.sleep(0.01 * (attempt + 1))
                    continue
                raise

        return False, None

    def link_activity(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        activity_id: str,
        activity_idempotency_key: str,
    ) -> bool:
        with self.engine.transaction("IMMEDIATE") as conn:
            cursor = conn.execute(
                """
                UPDATE ai_cache_entries
                SET activity_id = ?, activity_idempotency_key = ?
                WHERE workspace_id = ? AND cache_key = ?
                  AND owner_id = ? AND lease_token = ?
                  AND status = ?
                """,
                (
                    activity_id,
                    activity_idempotency_key,
                    workspace_id,
                    cache_key,
                    owner_id,
                    lease_token,
                    CacheEntryStatus.IN_FLIGHT.value,
                ),
            )
            return cursor.rowcount > 0

    def renew_lease(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        lease_duration_seconds: float,
    ) -> bool:
        now_dt = datetime.now(timezone.utc)
        new_deadline_iso = _dt_to_iso(now_dt + timedelta(seconds=lease_duration_seconds))

        with self.engine.transaction("IMMEDIATE") as conn:
            cursor = conn.execute(
                """
                UPDATE ai_cache_entries
                SET lease_expires_at = ?
                WHERE workspace_id = ? AND cache_key = ?
                  AND owner_id = ? AND lease_token = ?
                  AND status = ?
                """,
                (
                    new_deadline_iso,
                    workspace_id,
                    cache_key,
                    owner_id,
                    lease_token,
                    CacheEntryStatus.IN_FLIGHT.value,
                ),
            )
            return cursor.rowcount > 0

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
        if not output_ref:
            raise ValueError("output_ref cannot be empty when completing cache entry")

        expires_iso = _dt_to_iso(expires_at)

        with self.engine.transaction("IMMEDIATE") as conn:
            cursor = conn.execute(
                """
                UPDATE ai_cache_entries
                SET status = ?, output_ref = ?, producer = ?,
                    model = COALESCE(?, model),
                    model_version = COALESCE(?, model_version),
                    expires_at = COALESCE(?, expires_at),
                    activity_id = COALESCE(?, activity_id),
                    error_json = NULL,
                    owner_id = NULL,
                    lease_token = NULL,
                    lease_expires_at = NULL
                WHERE workspace_id = ? AND cache_key = ?
                  AND owner_id = ? AND lease_token = ?
                """,
                (
                    CacheEntryStatus.READY.value,
                    output_ref,
                    producer,
                    model,
                    model_version,
                    expires_iso,
                    activity_id,
                    workspace_id,
                    cache_key,
                    owner_id,
                    lease_token,
                ),
            )

            if cursor.rowcount == 0:
                raise StaleCacheLeaseError(
                    f"Worker '{owner_id}' lost lease token '{lease_token}' for cache_key '{cache_key}'. "
                    f"Fencing prevented committing results to cache."
                )

            cursor = conn.execute(
                "SELECT * FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                (workspace_id, cache_key),
            )
            row = cursor.fetchone()
            return self._row_to_entry(row)

    def mark_entry_failed(
        self,
        workspace_id: str,
        cache_key: str,
        owner_id: str,
        lease_token: str,
        error: AIError,
    ) -> bool:
        error_json = error.model_dump_json()

        with self.engine.transaction("IMMEDIATE") as conn:
            cursor = conn.execute(
                """
                UPDATE ai_cache_entries
                SET status = ?, error_json = ?,
                    output_ref = NULL,
                    owner_id = NULL,
                    lease_token = NULL,
                    lease_expires_at = NULL
                WHERE workspace_id = ? AND cache_key = ?
                  AND owner_id = ? AND lease_token = ?
                """,
                (
                    CacheEntryStatus.FAILED.value,
                    error_json,
                    workspace_id,
                    cache_key,
                    owner_id,
                    lease_token,
                ),
            )
            return cursor.rowcount > 0

    def invalidate_entry(self, workspace_id: str, cache_key: str) -> bool:
        with self.engine.transaction("IMMEDIATE") as conn:
            cursor = conn.execute(
                "DELETE FROM ai_cache_entries WHERE workspace_id = ? AND cache_key = ?",
                (workspace_id, cache_key),
            )
            return cursor.rowcount > 0

    def invalidate_workspace(self, workspace_id: str) -> int:
        with self.engine.transaction("IMMEDIATE") as conn:
            cursor = conn.execute(
                "DELETE FROM ai_cache_entries WHERE workspace_id = ?",
                (workspace_id,),
            )
            return cursor.rowcount
