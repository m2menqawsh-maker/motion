"""
Transactional Run Repository for S21.

Manages persistent storage, atomic CAS claims, leases, and migrations
for Pipeline Runs using SQLite with WAL mode.
"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from scripts.core.run_model import RunRecord, RunStatus, InvalidRunTransitionError, RunEvent


class RunRepositoryError(Exception):
    """Base exception for RunRepository errors."""
    pass


class LeaseAcquisitionError(RunRepositoryError):
    """Raised when an execution lease cannot be acquired."""
    pass


def get_default_db_path() -> Path:
    env_path = os.environ.get("MOTION_RUNS_DB_PATH") or os.environ.get("RUNS_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path("data/runs.db")


class RunRepository:
    """Canonical persistent authority for Pipeline Runs and Execution Leases."""

    CURRENT_SCHEMA_VERSION = 3

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_migrated()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=15.0,
            isolation_level=None  # Managed transactions
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 15000")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _transaction(self, mode: str = "IMMEDIATE"):
        conn = self._get_connection()
        try:
            conn.execute(f"BEGIN {mode}")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def _ensure_migrated(self) -> None:
        """Applies schema migrations up to CURRENT_SCHEMA_VERSION."""
        with self._transaction("IMMEDIATE") as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            cur = conn.execute("SELECT MAX(version) FROM _schema_migrations")
            row = cur.fetchone()
            current_v = row[0] if (row and row[0] is not None) else 0

            if current_v < 1:
                self._migrate_v1(conn)
                conn.execute(
                    "INSERT INTO _schema_migrations (version, applied_at) VALUES (1, ?)",
                    (datetime.now(timezone.utc).isoformat(),)
                )
            if current_v < 2:
                self._migrate_v2(conn)
                conn.execute(
                    "INSERT INTO _schema_migrations (version, applied_at) VALUES (2, ?)",
                    (datetime.now(timezone.utc).isoformat(),)
                )
            if current_v < 3:
                self._migrate_v3(conn)
                conn.execute(
                    "INSERT INTO _schema_migrations (version, applied_at) VALUES (3, ?)",
                    (datetime.now(timezone.utc).isoformat(),)
                )

    def _migrate_v3(self, conn: sqlite3.Connection) -> None:
        try:
            conn.execute("ALTER TABLE runs ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'ws_default'")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE project_execution_leases ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'ws_default'")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE run_events ADD COLUMN workspace_id TEXT NOT NULL DEFAULT 'ws_default'")
        except sqlite3.OperationalError:
            pass

        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_tenant_project ON runs(workspace_id, project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_tenant ON run_events(workspace_id, project_id, run_id)")

    def _migrate_v2(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS run_events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                stage TEXT,
                timestamp TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE (run_id, sequence)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_lookup ON run_events(run_id, sequence)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_run_events_project ON run_events(project_id)")

    def _migrate_v1(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                attempt INTEGER NOT NULL DEFAULT 1,
                worker_id TEXT,
                lease_expires_at TEXT,
                input_revision INTEGER,
                idempotency_key TEXT,
                request_payload_hash TEXT,
                failure_code TEXT,
                failure_detail TEXT,
                result_reference TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_execution_leases (
                project_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_idempotency ON runs(project_id, idempotency_key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_runs_workspace_project_idempotency ON runs(workspace_id, project_id, idempotency_key) WHERE idempotency_key IS NOT NULL")

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> RunRecord:
        data = dict(row)
        if data.get("failure_detail") and isinstance(data["failure_detail"], str):
            try:
                data["failure_detail"] = json.loads(data["failure_detail"])
            except Exception:
                pass
        if data.get("result_reference") and isinstance(data["result_reference"], str):
            try:
                data["result_reference"] = json.loads(data["result_reference"])
            except Exception:
                pass
        return RunRecord.model_validate(data)

    def create_run(self, run: RunRecord) -> RunRecord:
        """Atomically persists a new RunRecord with status QUEUED."""
        ws_id = getattr(run, "workspace_id", "ws_default") or "ws_default"
        with self._transaction("IMMEDIATE") as conn:
            # Atomic idempotency guard within the write transaction
            if run.idempotency_key:
                cur_existing = conn.execute(
                    "SELECT * FROM runs WHERE workspace_id = ? AND project_id = ? AND idempotency_key = ?",
                    (ws_id, run.project_id, run.idempotency_key)
                )
                row = cur_existing.fetchone()
                if row:
                    existing = self._row_to_record(row)
                    if (
                        run.request_payload_hash
                        and existing.request_payload_hash
                        and existing.request_payload_hash != run.request_payload_hash
                    ):
                        from api.core.errors import IdempotencyConflictError
                        raise IdempotencyConflictError(
                            idempotency_key=run.idempotency_key,
                            message=f"Idempotency conflict: Key '{run.idempotency_key}' was previously used with a different request payload."
                        )
                    return existing

            conn.execute(
                """
                INSERT INTO runs (
                    run_id, workspace_id, project_id, status, created_at, updated_at,
                    started_at, finished_at, attempt, worker_id, lease_expires_at,
                    input_revision, idempotency_key, request_payload_hash,
                    failure_code, failure_detail, result_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    ws_id,
                    run.project_id,
                    run.status.value,
                    run.created_at,
                    run.updated_at,
                    run.started_at,
                    run.finished_at,
                    run.attempt,
                    run.worker_id,
                    run.lease_expires_at,
                    run.input_revision,
                    run.idempotency_key,
                    run.request_payload_hash,
                    run.failure_code,
                    json.dumps(run.failure_detail) if run.failure_detail else None,
                    json.dumps(run.result_reference) if run.result_reference else None,
                )
            )
            return run

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Loads a RunRecord by its primary key."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)
        finally:
            conn.close()

    def list_runs(self, project_id: str, limit: int = 50, workspace_id: Optional[str] = None) -> List[RunRecord]:
        """Lists runs for a specific project, ordered by creation time descending."""
        conn = self._get_connection()
        try:
            if workspace_id:
                cur = conn.execute(
                    "SELECT * FROM runs WHERE project_id = ? AND workspace_id = ? ORDER BY created_at DESC LIMIT ?",
                    (project_id, workspace_id, limit)
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM runs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
                    (project_id, limit)
                )
            return [self._row_to_record(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def find_by_idempotency(self, project_id: str, idempotency_key: str, workspace_id: Optional[str] = None) -> Optional[RunRecord]:
        """Finds an existing run by project_id and idempotency_key, optionally scoped by workspace_id."""
        conn = self._get_connection()
        try:
            if workspace_id:
                cur = conn.execute(
                    "SELECT * FROM runs WHERE project_id = ? AND idempotency_key = ? AND workspace_id = ?",
                    (project_id, idempotency_key, workspace_id)
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM runs WHERE project_id = ? AND idempotency_key = ?",
                    (project_id, idempotency_key)
                )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)
        finally:
            conn.close()

    def claim_next_run(self, worker_id: str, lease_duration_seconds: float = 30.0) -> Optional[RunRecord]:
        """
        Atomically claims the oldest QUEUED run whose project is not currently locked.
        Uses transactional CAS and acquires a project-level execution lease.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        lease_expires = (now + timedelta(seconds=lease_duration_seconds)).isoformat()

        with self._transaction("IMMEDIATE") as conn:
            # 1. Clean up any expired project leases
            conn.execute("DELETE FROM project_execution_leases WHERE expires_at < ?", (now_iso,))

            # 2. Select oldest QUEUED run whose project is not locked
            query = """
                SELECT r.* FROM runs r
                WHERE r.status = 'QUEUED'
                  AND r.project_id NOT IN (SELECT project_id FROM project_execution_leases)
                ORDER BY r.created_at ASC
                LIMIT 1
            """
            cur = conn.execute(query)
            row = cur.fetchone()
            if not row:
                return None

            candidate = self._row_to_record(row)

            # 3. Atomically update run status to RUNNING (CAS on status=QUEUED)
            update_cur = conn.execute(
                """
                UPDATE runs
                SET status = 'RUNNING',
                    worker_id = ?,
                    lease_expires_at = ?,
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE run_id = ? AND status = 'QUEUED'
                """,
                (worker_id, lease_expires, now_iso, now_iso, candidate.run_id)
            )

            if update_cur.rowcount != 1:
                # Lost race to another worker
                return None

            # 4. Acquire project execution lease
            conn.execute(
                """
                INSERT INTO project_execution_leases (
                    project_id, workspace_id, run_id, worker_id, acquired_at, expires_at, heartbeat_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (candidate.project_id, getattr(candidate, "workspace_id", "ws_default") or "ws_default", candidate.run_id, worker_id, now_iso, lease_expires, now_iso)
            )

            # Return updated record
            cur_updated = conn.execute("SELECT * FROM runs WHERE run_id = ?", (candidate.run_id,))
            return self._row_to_record(cur_updated.fetchone())

    def renew_lease(self, run_id: str, worker_id: str, lease_duration_seconds: float = 30.0) -> bool:
        """Heartbeat to extend the lease for a running job and its project lease."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        new_expires = (now + timedelta(seconds=lease_duration_seconds)).isoformat()

        with self._transaction("IMMEDIATE") as conn:
            # Update run
            cur = conn.execute(
                """
                UPDATE runs
                SET lease_expires_at = ?,
                    updated_at = ?
                WHERE run_id = ? AND worker_id = ? AND status = 'RUNNING'
                """,
                (new_expires, now_iso, run_id, worker_id)
            )
            if cur.rowcount != 1:
                return False

            # Update project lease
            conn.execute(
                """
                UPDATE project_execution_leases
                SET expires_at = ?,
                    heartbeat_at = ?
                WHERE run_id = ? AND worker_id = ?
                """,
                (new_expires, now_iso, run_id, worker_id)
            )
            return True

    def finish_run(
        self,
        run_id: str,
        worker_id: str,
        status: RunStatus,
        result_reference: Optional[dict] = None,
        failure_code: Optional[str] = None,
        failure_detail: Optional[dict] = None,
    ) -> RunRecord:
        """Atomically transitions run to terminal status and releases project execution lease."""
        if status not in (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED):
            raise InvalidRunTransitionError(f"finish_run target must be a terminal status, got {status.value}")

        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()

        with self._transaction("IMMEDIATE") as conn:
            cur = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                raise RunRepositoryError(f"Run {run_id} not found")

            record = self._row_to_record(row)

            # Strict worker fencing: worker attempting to finish MUST match current worker_id
            if worker_id and record.worker_id and record.worker_id != worker_id:
                raise RunRepositoryError(
                    f"Stale worker fencing violation: Worker '{worker_id}' is not the current leaseholder of run '{run_id}' (owned by '{record.worker_id}')."
                )

            # Strict worker fencing: worker lease must not be expired
            if worker_id and record.lease_expires_at:
                try:
                    exp_dt = datetime.fromisoformat(record.lease_expires_at)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if exp_dt < now_dt:
                        raise RunRepositoryError(
                            f"Stale worker fencing violation: Worker '{worker_id}' lease expired at {record.lease_expires_at} (current time {now})."
                        )
                except ValueError:
                    if record.lease_expires_at < now:
                        raise RunRepositoryError(
                            f"Stale worker fencing violation: Worker '{worker_id}' lease expired at {record.lease_expires_at}."
                        )

            # Also check project_execution_leases if worker_id is provided
            if worker_id:
                cur_lease = conn.execute(
                    "SELECT worker_id, expires_at FROM project_execution_leases WHERE run_id = ?",
                    (run_id,)
                )
                lease_row = cur_lease.fetchone()
                if lease_row:
                    lease_worker, lease_exp = lease_row[0], lease_row[1]
                    if lease_worker != worker_id:
                        raise RunRepositoryError(
                            f"Stale worker fencing violation: Project execution lease held by '{lease_worker}', not '{worker_id}'."
                        )
                    if lease_exp and lease_exp < now:
                        raise RunRepositoryError(
                            f"Stale worker fencing violation: Project execution lease expired at {lease_exp}."
                        )

            record.assert_can_transition_to(status)

            cur_update = conn.execute(
                """
                UPDATE runs
                SET status = ?,
                    finished_at = ?,
                    updated_at = ?,
                    worker_id = ?,
                    lease_expires_at = NULL,
                    result_reference = ?,
                    failure_code = ?,
                    failure_detail = ?
                WHERE run_id = ? AND (worker_id = ? OR worker_id IS NULL)
                  AND (lease_expires_at IS NULL OR lease_expires_at >= ?)
                """,
                (
                    status.value,
                    now,
                    now,
                    worker_id,
                    json.dumps(result_reference) if result_reference else None,
                    failure_code,
                    json.dumps(failure_detail) if failure_detail else None,
                    run_id,
                    worker_id,
                    now,
                )
            )

            if cur_update.rowcount != 1:
                raise RunRepositoryError(
                    f"Stale worker fencing violation: Failed to atomically transition run '{run_id}'. Worker '{worker_id}' lost its lease."
                )

            # Release project execution lease
            conn.execute("DELETE FROM project_execution_leases WHERE run_id = ? AND worker_id = ?", (run_id, worker_id))

            cur_updated = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            return self._row_to_record(cur_updated.fetchone())

    def is_lease_active(self, run_id: str, worker_id: str) -> bool:
        """Checks if worker_id currently holds an active, unexpired lease for run_id."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                """
                SELECT 1 FROM runs
                WHERE run_id = ? AND worker_id = ? AND status = 'RUNNING'
                  AND (lease_expires_at IS NULL OR lease_expires_at > ?)
                """,
                (run_id, worker_id, now_iso)
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    def get_active_project_lease(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Returns active unexpired project lease if present."""
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM project_execution_leases WHERE project_id = ? AND expires_at > ?",
                (project_id, now_iso)
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()

    def acquire_direct_project_lease(
        self,
        project_id: str,
        owner_id: str,
        run_id: str,
        lease_duration_seconds: float = 60.0,
        workspace_id: str = "ws_default",
    ) -> bool:
        """Directly acquires a project lease (e.g. for CLI invocation)."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_iso = (now + timedelta(seconds=lease_duration_seconds)).isoformat()

        with self._transaction("IMMEDIATE") as conn:
            # Clean expired lease
            conn.execute("DELETE FROM project_execution_leases WHERE project_id = ? AND expires_at < ?", (project_id, now_iso))

            try:
                conn.execute(
                    """
                    INSERT INTO project_execution_leases (
                        project_id, workspace_id, run_id, worker_id, acquired_at, expires_at, heartbeat_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (project_id, workspace_id, run_id, owner_id, now_iso, expires_iso, now_iso)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def release_project_lease(self, project_id: str, run_id: Optional[str] = None) -> bool:
        """Releases the project lease."""
        with self._transaction("IMMEDIATE") as conn:
            if run_id:
                cur = conn.execute("DELETE FROM project_execution_leases WHERE project_id = ? AND run_id = ?", (project_id, run_id))
            else:
                cur = conn.execute("DELETE FROM project_execution_leases WHERE project_id = ?", (project_id,))
            return cur.rowcount > 0

    def recover_orphaned_runs(self, grace_seconds: float = 0.0) -> List[RunRecord]:
        """Identifies runs in RUNNING state whose lease has expired."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=grace_seconds)).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM runs WHERE status = 'RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at < ?",
                (cutoff,)
            )
            return [self._row_to_record(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def reset_run_to_queued(self, run_id: str, new_attempt: int) -> bool:
        """Resets an orphaned run back to QUEUED with an incremented attempt and clears leases."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                """
                UPDATE runs
                SET status = 'QUEUED',
                    attempt = ?,
                    worker_id = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE run_id = ? AND status = 'RUNNING'
                """,
                (new_attempt, now_iso, run_id)
            )
            conn.execute("DELETE FROM project_execution_leases WHERE run_id = ?", (run_id,))
            return cur.rowcount == 1

    def mark_run_failed(self, run_id: str, failure_code: str, failure_detail: dict) -> bool:
        """Marks an unrecoverable run as FAILED and clears leases."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                """
                UPDATE runs
                SET status = 'FAILED',
                    finished_at = ?,
                    updated_at = ?,
                    lease_expires_at = NULL,
                    failure_code = ?,
                    failure_detail = ?
                WHERE run_id = ?
                """,
                (now_iso, now_iso, failure_code, json.dumps(failure_detail), run_id)
            )
            conn.execute("DELETE FROM project_execution_leases WHERE run_id = ?", (run_id,))
            return cur.rowcount == 1

    def record_event(
        self,
        run_id: str,
        project_id: str,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        stage: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> RunEvent:
        """Atomically appends an event for a run with monotonic sequence number."""
        now = datetime.now(timezone.utc).isoformat()
        event_id = f"evt_{uuid.uuid4().hex}"
        payload_data = payload or {}

        with self._transaction("IMMEDIATE") as conn:
            actual_ws_id = workspace_id
            if not actual_ws_id:
                cur_ws = conn.execute("SELECT workspace_id FROM runs WHERE run_id = ?", (run_id,))
                row_ws = cur_ws.fetchone()
                if row_ws and row_ws[0]:
                    actual_ws_id = row_ws[0]
                else:
                    actual_ws_id = "ws_default"

            cur = conn.execute("SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_events WHERE run_id = ?", (run_id,))
            seq = cur.fetchone()[0]

            conn.execute(
                """
                INSERT INTO run_events (event_id, workspace_id, run_id, project_id, sequence, event_type, stage, timestamp, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, actual_ws_id, run_id, project_id, seq, event_type, stage, now, json.dumps(payload_data))
            )

        return RunEvent(
            event_id=event_id,
            workspace_id=actual_ws_id,
            run_id=run_id,
            project_id=project_id,
            sequence=seq,
            event_type=event_type,
            stage=stage,
            timestamp=now,
            payload=payload_data,
        )

    def get_events(
        self,
        run_id: str,
        project_id: Optional[str] = None,
        after_sequence: int = 0,
        limit: int = 500,
        workspace_id: Optional[str] = None,
    ) -> List[RunEvent]:
        """Retrieves persistent events for a run ordered by sequence."""
        conn = self._get_connection()
        try:
            params: List[Any] = [run_id]
            sql = "SELECT * FROM run_events WHERE run_id = ?"
            if workspace_id:
                sql += " AND workspace_id = ?"
                params.append(workspace_id)
            if project_id:
                sql += " AND project_id = ?"
                params.append(project_id)
            sql += " AND sequence > ? ORDER BY sequence ASC LIMIT ?"
            params.extend([after_sequence, limit])
            cur = conn.execute(sql, tuple(params))
            results = []
            for row in cur.fetchall():
                d = dict(row)
                payload = json.loads(d["payload_json"]) if d.get("payload_json") else {}
                results.append(RunEvent(
                    event_id=d["event_id"],
                    workspace_id=d.get("workspace_id", "ws_default"),
                    run_id=d["run_id"],
                    project_id=d["project_id"],
                    sequence=d["sequence"],
                    event_type=d["event_type"],
                    stage=d.get("stage"),
                    timestamp=d["timestamp"],
                    payload=payload,
                ))
            return results
        finally:
            conn.close()

    def request_cancel_run(
        self,
        run_id: str,
        project_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Tuple[RunRecord, bool]:
        """
        Atomically cancels a QUEUED run or requests cancellation for a RUNNING run.
        Returns: (RunRecord, changed: bool)
        Raises:
            RunRepositoryError if run not found.
            InvalidRunTransitionError if run is already in terminal state SUCCEEDED or FAILED.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._transaction("IMMEDIATE") as conn:
            cur = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                raise RunRepositoryError(f"Run '{run_id}' not found")
            rec = self._row_to_record(row)
            if workspace_id and rec.workspace_id != workspace_id:
                raise RunRepositoryError(f"Run '{run_id}' does not belong to workspace '{workspace_id}'")
            if project_id and rec.project_id != project_id:
                raise RunRepositoryError(f"Run '{run_id}' does not belong to project '{project_id}'")

            if rec.status == RunStatus.CANCELLED:
                return rec, False
            if rec.status == RunStatus.CANCEL_REQUESTED:
                return rec, False
            if rec.status in (RunStatus.SUCCEEDED, RunStatus.FAILED):
                raise InvalidRunTransitionError(
                    f"Cannot cancel run '{run_id}' because it is already in terminal state {rec.status.value}."
                )

            if rec.status == RunStatus.QUEUED:
                # Cancel immediately
                conn.execute(
                    """
                    UPDATE runs
                    SET status = 'CANCELLED',
                        finished_at = ?,
                        updated_at = ?,
                        failure_code = 'RUN_CANCELLED',
                        failure_detail = ?
                    WHERE run_id = ?
                    """,
                    (now, now, json.dumps({"reason": "Cancelled while queued"}), run_id)
                )
                conn.execute("DELETE FROM project_execution_leases WHERE run_id = ?", (run_id,))

                # Append RUN_CANCELLED event
                cur_seq = conn.execute("SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_events WHERE run_id = ?", (run_id,))
                seq = cur_seq.fetchone()[0]
                conn.execute(
                    """
                    INSERT INTO run_events (event_id, workspace_id, run_id, project_id, sequence, event_type, stage, timestamp, payload_json)
                    VALUES (?, ?, ?, ?, ?, 'RUN_CANCELLED', NULL, ?, ?)
                    """,
                    (f"evt_{uuid.uuid4().hex}", rec.workspace_id, run_id, rec.project_id, seq, now, json.dumps({"reason": "Cancelled while queued"}))
                )

                cur_updated = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
                return self._row_to_record(cur_updated.fetchone()), True

            elif rec.status == RunStatus.RUNNING:
                # Request cancellation
                conn.execute(
                    """
                    UPDATE runs
                    SET status = 'CANCEL_REQUESTED',
                        updated_at = ?
                    WHERE run_id = ? AND status = 'RUNNING'
                    """,
                    (now, run_id)
                )

                # Append CANCEL_REQUESTED event
                cur_seq = conn.execute("SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_events WHERE run_id = ?", (run_id,))
                seq = cur_seq.fetchone()[0]
                conn.execute(
                    """
                    INSERT INTO run_events (event_id, workspace_id, run_id, project_id, sequence, event_type, stage, timestamp, payload_json)
                    VALUES (?, ?, ?, ?, ?, 'CANCEL_REQUESTED', NULL, ?, ?)
                    """,
                    (f"evt_{uuid.uuid4().hex}", rec.workspace_id, run_id, rec.project_id, seq, now, json.dumps({"reason": "Cancellation requested"}))
                )

                cur_updated = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
                return self._row_to_record(cur_updated.fetchone()), True
