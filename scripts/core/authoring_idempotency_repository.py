"""
scripts/core/authoring_idempotency_repository.py — Durable CAS-backed Authoring Idempotency Repository.
S28-R14: Enforces cross-process and cross-worker authoring idempotency.

Invariants:
- Scoped strictly by (workspace_id, project_id, operation_id).
- Same key + identical semantic payload -> returns original cached result without mutating twice.
- Same key + materially different payload -> fail-closed with structured IdempotencyConflictError.
- Recovers safely from aborted/expired leases via crash recovery.
- Operates within database immediate transactions across PostgreSQL / SQLite.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from scripts.core.database import DatabaseEngine, get_database_engine

logger = logging.getLogger("clean_video.authoring_idempotency")


class IdempotencyConflictError(Exception):
    """Raised when an operation_id is reused with materially different input payload."""

    def __init__(self, operation_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.operation_id = operation_id
        self.details = details or {}


class AuthoringIdempotencyRepository:
    """Authoritative repository for durable authoring operation idempotency."""

    def __init__(self, db_engine: Optional[DatabaseEngine] = None) -> None:
        self._db = db_engine

    @property
    def db(self) -> DatabaseEngine:
        return self._db or get_database_engine()

    def get_record(
        self,
        workspace_id: str,
        project_id: str,
        operation_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Queries the current durable idempotency record."""
        conn = self.db.get_connection()
        try:
            cur = conn.execute(
                """
                SELECT workspace_id, project_id, operation_id, operation_type,
                       base_revision, payload_hash, status, result_revision,
                       result_json, error_json, lease_expires_at, created_at, updated_at
                FROM authoring_idempotency_records
                WHERE workspace_id = ? AND project_id = ? AND operation_id = ?
                """,
                (workspace_id, project_id, operation_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "workspace_id": row[0],
                "project_id": row[1],
                "operation_id": row[2],
                "operation_type": row[3],
                "base_revision": row[4],
                "payload_hash": row[5],
                "status": row[6],
                "result_revision": row[7],
                "result_json": json.loads(row[8]) if row[8] else None,
                "error_json": json.loads(row[9]) if row[9] else None,
                "lease_expires_at": row[10],
                "created_at": row[11],
                "updated_at": row[12],
            }
        finally:
            conn.close()

    def try_claim_leader(
        self,
        workspace_id: str,
        project_id: str,
        operation_id: str,
        operation_type: str,
        base_revision: int,
        payload_hash: str,
        lease_seconds: float = 60.0,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Atomically attempts to claim leadership for an authoring operation.

        Returns:
            (status, cached_result):
            - ("LEADER", None): Won leadership race; caller must execute mutation.
            - ("COMPLETED", result_dict): Already completed; caller must replay result.
            - ("IN_PROGRESS", None): Another worker is executing; caller should await/retry.
        Raises:
            IdempotencyConflictError: If operation_id was used with a different input payload.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        lease_exp = (now + timedelta(seconds=lease_seconds)).isoformat()

        with self.db.transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                """
                SELECT payload_hash, status, result_json, error_json, lease_expires_at, base_revision, operation_type
                FROM authoring_idempotency_records
                WHERE workspace_id = ? AND project_id = ? AND operation_id = ?
                """,
                (workspace_id, project_id, operation_id),
            )
            row = cur.fetchone()

            if not row:
                # 1. No existing record: atomically insert as IN_PROGRESS
                conn.execute(
                    """
                    INSERT INTO authoring_idempotency_records (
                        workspace_id, project_id, operation_id, operation_type,
                        base_revision, payload_hash, status, result_revision,
                        result_json, error_json, lease_expires_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'IN_PROGRESS', NULL, NULL, NULL, ?, ?, ?)
                    """,
                    (
                        workspace_id,
                        project_id,
                        operation_id,
                        operation_type,
                        base_revision,
                        payload_hash,
                        lease_exp,
                        now_iso,
                        now_iso,
                    ),
                )
                return ("LEADER", None)

            existing_hash, existing_status, existing_result, existing_error, existing_lease, existing_base_rev, existing_type = row

            # 2. Material difference conflict check
            if existing_hash != payload_hash or existing_type != operation_type:
                raise IdempotencyConflictError(
                    operation_id=operation_id,
                    message=(
                        f"Idempotency conflict: operation_id '{operation_id}' was previously submitted "
                        f"with a different operation type or payload."
                    ),
                    details={
                        "workspace_id": workspace_id,
                        "project_id": project_id,
                        "existing_operation_type": existing_type,
                        "requested_operation_type": operation_type,
                        "existing_base_revision": existing_base_rev,
                        "requested_base_revision": base_revision,
                    },
                )

            # 3. Already completed -> replay cached result
            if existing_status == "COMPLETED":
                parsed = json.loads(existing_result) if existing_result else {}
                return ("COMPLETED", parsed)

            # 4. Currently IN_PROGRESS -> check lease expiration for crash recovery
            if existing_status == "IN_PROGRESS":
                if existing_lease and existing_lease < now_iso:
                    logger.warning(
                        f"Authoring idempotency lease expired for '{operation_id}'. Claiming via crash recovery."
                    )
                    conn.execute(
                        """
                        UPDATE authoring_idempotency_records
                        SET lease_expires_at = ?, updated_at = ?
                        WHERE workspace_id = ? AND project_id = ? AND operation_id = ?
                        """,
                        (lease_exp, now_iso, workspace_id, project_id, operation_id),
                    )
                    return ("LEADER", None)
                return ("IN_PROGRESS", None)

            # 5. Failed record -> allow retry as leader
            if existing_status == "FAILED":
                conn.execute(
                    """
                    UPDATE authoring_idempotency_records
                    SET status = 'IN_PROGRESS', lease_expires_at = ?, updated_at = ?, error_json = NULL
                    WHERE workspace_id = ? AND project_id = ? AND operation_id = ?
                    """,
                    (lease_exp, now_iso, workspace_id, project_id, operation_id),
                )
                return ("LEADER", None)

            return ("IN_PROGRESS", None)

    def mark_completed(
        self,
        workspace_id: str,
        project_id: str,
        operation_id: str,
        result_revision: int,
        result_payload: Dict[str, Any],
    ) -> None:
        """Atomically marks operation as COMPLETED and persists cached result."""
        now_iso = datetime.now(timezone.utc).isoformat()
        res_json = json.dumps(result_payload, ensure_ascii=False)

        with self.db.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                UPDATE authoring_idempotency_records
                SET status = 'COMPLETED', result_revision = ?, result_json = ?,
                    lease_expires_at = NULL, updated_at = ?
                WHERE workspace_id = ? AND project_id = ? AND operation_id = ?
                """,
                (result_revision, res_json, now_iso, workspace_id, project_id, operation_id),
            )

    def mark_failed(
        self,
        workspace_id: str,
        project_id: str,
        operation_id: str,
        error_payload: Dict[str, Any],
    ) -> None:
        """Marks operation as FAILED with error detail."""
        now_iso = datetime.now(timezone.utc).isoformat()
        err_json = json.dumps(error_payload, ensure_ascii=False)

        with self.db.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                UPDATE authoring_idempotency_records
                SET status = 'FAILED', error_json = ?,
                    lease_expires_at = NULL, updated_at = ?
                WHERE workspace_id = ? AND project_id = ? AND operation_id = ?
                """,
                (err_json, now_iso, workspace_id, project_id, operation_id),
            )
