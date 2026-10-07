"""
scripts/core/idempotency_repository.py
======================================
Durable CAS-backed repository for ToolGateway capability idempotency (S28-M05 C04).

Architectural Invariants:
- Uses DatabaseEngine with transactional consistency (PostgreSQL / SQLite WAL mode).
- Guarantees cross-process and cross-worker idempotency:
  Two racing requests with identical idempotency_key hitting distinct workers/processes
  execute side-effects strictly once.
- Same key + same payload:
  First caller becomes LEADER and executes; concurrent/subsequent callers await/replay without re-executing.
- Same key + different payload:
  Strictly rejected with IdempotencyConflictError (POLICY_DENIED).
- Crash recovery / retry:
  If side-effect was committed, retries recover and replay the cached result without duplicate side-effects.
  If leader crashed during execution (lease expired), a retry can safely assume leadership.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any, Dict, Optional, Tuple

from ai.tools.errors import IdempotencyConflictError
from scripts.core.database import DatabaseEngine, get_database_engine

logger = logging.getLogger("clean_video.scripts.core.idempotency_repository")

TOOL_IDEMPOTENCY_SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    lease_expires_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tool_idempotency_status ON tool_idempotency_records(status);
"""


class SQLIdempotencyRepository:
    """
    Production durable persistence authority for tool execution idempotency.
    Operates at the database transaction / CAS boundary across multiple worker processes.
    """

    def __init__(self, db_engine: Optional[DatabaseEngine] = None) -> None:
        self.db = db_engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.db.transaction("IMMEDIATE") as conn:
            for statement in TOOL_IDEMPOTENCY_SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    def get_record(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Queries the current durable idempotency record by key."""
        conn = self.db.get_connection()
        try:
            cur = conn.execute(
                "SELECT idempotency_key, payload_hash, status, result_json, error_json, "
                "created_at, updated_at, lease_expires_at "
                "FROM tool_idempotency_records WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "idempotency_key": row[0],
                "payload_hash": row[1],
                "status": row[2],
                "result_json": row[3],
                "error_json": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "lease_expires_at": row[7],
            }
        finally:
            conn.close()

    def try_claim_leader(
        self,
        idempotency_key: str,
        payload_hash: str,
        lease_seconds: float = 60.0,
    ) -> Tuple[str, Optional[str]]:
        """
        Atomically attempts to claim leadership for an idempotency key using DB IMMEDIATE transaction.

        Returns:
            (status, result_json):
            - ("LEADER", None): Caller won leadership race and must execute the side-effect.
            - ("COMPLETED", result_json): Already finished; caller must replay result.
            - ("IN_PROGRESS", None): Another worker is executing; caller should await leader completion.
        Raises:
            IdempotencyConflictError: If the key was used with a different input payload_hash.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        lease_exp = (now + timedelta(seconds=lease_seconds)).isoformat()

        with self.db.transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                "SELECT payload_hash, status, result_json, error_json, lease_expires_at "
                "FROM tool_idempotency_records WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = cur.fetchone()

            if not row:
                # 1. No existing record: atomically claim leadership
                conn.execute(
                    "INSERT INTO tool_idempotency_records ("
                    "idempotency_key, payload_hash, status, result_json, error_json, "
                    "created_at, updated_at, lease_expires_at"
                    ") VALUES (?, ?, 'IN_PROGRESS', NULL, NULL, ?, ?, ?)",
                    (idempotency_key, payload_hash, now_iso, now_iso, lease_exp),
                )
                return ("LEADER", None)

            existing_hash, existing_status, existing_result, existing_error, existing_lease = row

            # 2. Conflict check: different payload for same key
            if existing_hash != payload_hash:
                raise IdempotencyConflictError(
                    idempotency_key,
                    f"Idempotency conflict: key '{idempotency_key}' was previously executed or is currently executing with a different input payload.",
                )

            # 3. Already completed: return replayed payload
            if existing_status == "COMPLETED":
                return ("COMPLETED", existing_result)

            # 4. Currently executing: check for expired worker lease (crash recovery)
            if existing_status == "IN_PROGRESS":
                if existing_lease and existing_lease < now_iso:
                    logger.warning(
                        f"Idempotency lease expired for key '{idempotency_key}'. Assuming leadership via crash recovery."
                    )
                    conn.execute(
                        "UPDATE tool_idempotency_records SET status = 'IN_PROGRESS', updated_at = ?, lease_expires_at = ? "
                        "WHERE idempotency_key = ? AND status = 'IN_PROGRESS'",
                        (now_iso, lease_exp, idempotency_key),
                    )
                    return ("LEADER", None)
                return ("IN_PROGRESS", None)

            # 5. Previously failed: allow retry to become leader
            if existing_status == "FAILED":
                conn.execute(
                    "UPDATE tool_idempotency_records SET status = 'IN_PROGRESS', error_json = NULL, updated_at = ?, lease_expires_at = ? "
                    "WHERE idempotency_key = ?",
                    (now_iso, lease_exp, idempotency_key),
                )
                return ("LEADER", None)

            return ("IN_PROGRESS", None)

    def mark_completed(self, idempotency_key: str, payload_hash: str, result_json: str) -> None:
        """Atomically transitions an in-progress record to COMPLETED with stored result JSON."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.transaction("IMMEDIATE") as conn:
            conn.execute(
                "UPDATE tool_idempotency_records SET status = 'COMPLETED', result_json = ?, updated_at = ? "
                "WHERE idempotency_key = ? AND payload_hash = ?",
                (result_json, now_iso, idempotency_key, payload_hash),
            )

    def mark_failed(self, idempotency_key: str, payload_hash: str, error_json: str) -> None:
        """Atomically transitions an in-progress record to FAILED with error context."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.transaction("IMMEDIATE") as conn:
            conn.execute(
                "UPDATE tool_idempotency_records SET status = 'FAILED', error_json = ?, updated_at = ? "
                "WHERE idempotency_key = ? AND payload_hash = ?",
                (error_json, now_iso, idempotency_key, payload_hash),
            )

    async def poll_completion(
        self,
        idempotency_key: str,
        payload_hash: str,
        poll_interval: float = 0.05,
        timeout: float = 30.0,
    ) -> Optional[str]:
        """
        Asynchronously polls the durable database until leader finishes execution or timeout expires.
        Returns serialized result JSON on success, or raises on failure/conflict/timeout.
        """
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            rec = self.get_record(idempotency_key)
            if rec:
                if rec["payload_hash"] != payload_hash:
                    raise IdempotencyConflictError(
                        idempotency_key,
                        f"Idempotency conflict: key '{idempotency_key}' payload mismatch during poll.",
                    )
                if rec["status"] == "COMPLETED":
                    return rec["result_json"]
                if rec["status"] == "FAILED":
                    raise RuntimeError(f"Leader execution failed for idempotency_key '{idempotency_key}': {rec.get('error_json')}")
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Timed out waiting for leader execution on idempotency_key '{idempotency_key}'")
