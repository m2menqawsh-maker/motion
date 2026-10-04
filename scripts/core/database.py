"""
scripts/core/database.py — Unified Multi-Tenant Database Engine & Repositories (S24.5 - ADR-003).

Provides:
- DatabaseEngine: connection management and schema migration supporting PostgreSQL and SQLite.
- Strict transactional consistency, foreign keys, and indexes.
- CAS state persistence: atomic revision check-and-swap.
- TenantRepository: Users, Workspaces, Memberships, and Projects.
- TenantStateRepository: ProjectState persistence in DB with CAS.
- UsageRepository: Metered consumption events.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Generator

from scripts.core.security.principal import Role, Principal
from scripts.core.tenant_model import (
    User,
    UserStatus,
    Workspace,
    WorkspaceMember,
    ProjectRecord,
    TenantContext,
    UsageEvent,
    UsageEventType,
)
from scripts.core.state_model import ProjectState, LifecycleState
from scripts.core.state_store import StateConflictError, StateNotFoundError


class DatabaseError(Exception):
    """Base exception for database failures."""
    pass


class TenantNotFoundError(DatabaseError):
    """Raised when user, workspace, or project does not exist."""
    pass


class TenantSecurityError(DatabaseError):
    """Raised on illegal cross-tenant access attempt."""
    pass


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS _schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
INSERT OR IGNORE INTO _schema_migrations (version, applied_at) VALUES (1, '2026-09-30T00:00:00Z');

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id);

CREATE TABLE IF NOT EXISTS project_states (
    project_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    lifecycle_state TEXT NOT NULL,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_project_states_workspace ON project_states(workspace_id);

CREATE TABLE IF NOT EXISTS project_artifact_versions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    artifact_kind TEXT NOT NULL,
    revision INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_artifact_versions_lookup ON project_artifact_versions(workspace_id, project_id, artifact_kind);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
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
    result_reference TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_runs_tenant_project ON runs(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_idempotency ON runs(workspace_id, project_id, idempotency_key);

CREATE TABLE IF NOT EXISTS project_execution_leases (
    project_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS run_events (
    event_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    stage TEXT,
    timestamp TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (run_id, sequence),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_run_events_tenant ON run_events(workspace_id, project_id, run_id);

CREATE TABLE IF NOT EXISTS review_bundles (
    bundle_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    hashes_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_review_bundles_proj ON review_bundles(workspace_id, project_id);

CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    bundle_id TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    revision INTEGER NOT NULL,
    decided_at TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY (bundle_id) REFERENCES review_bundles(bundle_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_review_decisions_proj ON review_decisions(workspace_id, project_id);

CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT,
    user_id TEXT,
    event_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_usage_events_ws ON usage_events(workspace_id, created_at);

CREATE TABLE IF NOT EXISTS canonical_assets (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    media_type TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE (project_id, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_canonical_assets_lookup ON canonical_assets(project_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_canonical_assets_project_asset ON canonical_assets(project_id, asset_id);

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


class DatabaseEngine:
    """Unified Database Engine managing SQLite and PostgreSQL connections."""

    def __init__(self, db_url: Optional[str] = None):
        if not db_url:
            db_url = os.environ.get("DATABASE_URL") or os.environ.get("MOTION_DATABASE_URL", "sqlite:///data/motion.db")
        self.db_url = db_url
        self.is_sqlite = db_url.startswith("sqlite://") or "://" not in db_url
        self.sqlite_path: Optional[Path] = None

        if self.is_sqlite:
            clean_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
            self.sqlite_path = Path(clean_path).resolve()
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_schema()

    def get_connection(self):
        if self.is_sqlite:
            conn = sqlite3.connect(
                str(self.sqlite_path),
                timeout=30.0,
                isolation_level=None  # Explicit managed transactions
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        else:
            # PostgreSQL connection via psycopg / psycopg2 if available
            try:
                import psycopg
                return psycopg.connect(self.db_url)
            except ImportError:
                import psycopg2
                return psycopg2.connect(self.db_url)

    @contextmanager
    def transaction(self, mode: str = "IMMEDIATE") -> Generator[Any, None, None]:
        conn = self.get_connection()
        try:
            if self.is_sqlite:
                conn.execute(f"BEGIN {mode}")
            else:
                conn.autocommit = False
            yield conn
            conn.execute("COMMIT") if self.is_sqlite else conn.commit()
        except Exception:
            conn.execute("ROLLBACK") if self.is_sqlite else conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Executes DDL statements to ensure all multi-tenant tables exist."""
        with self.transaction("IMMEDIATE") as conn:
            if self.is_sqlite:
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='canonical_assets'")
                if cur.fetchone():
                    col_cur = conn.execute("PRAGMA table_info(canonical_assets)")
                    cols = [r[1] for r in col_cur.fetchall()]
                    if "id" not in cols:
                        conn.execute("ALTER TABLE canonical_assets RENAME TO canonical_assets_old")
                        conn.execute("""
                            CREATE TABLE canonical_assets (
                                id TEXT PRIMARY KEY,
                                asset_id TEXT NOT NULL,
                                project_id TEXT NOT NULL,
                                workspace_id TEXT NOT NULL,
                                content_hash TEXT NOT NULL,
                                storage_key TEXT NOT NULL,
                                media_type TEXT NOT NULL,
                                mime_type TEXT NOT NULL,
                                file_size_bytes INTEGER NOT NULL,
                                provenance_json TEXT NOT NULL DEFAULT '{}',
                                created_at TEXT NOT NULL,
                                UNIQUE (project_id, content_hash)
                            )
                        """)
                        conn.execute("""
                            INSERT INTO canonical_assets (id, asset_id, project_id, workspace_id, content_hash, storage_key, media_type, mime_type, file_size_bytes, provenance_json, created_at)
                            SELECT project_id || ':' || content_hash, asset_id, project_id, workspace_id, content_hash, storage_key, media_type, mime_type, file_size_bytes, provenance_json, created_at
                            FROM canonical_assets_old
                        """)
                        conn.execute("DROP TABLE canonical_assets_old")

            for statement in SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)


class TenantRepository:
    """Repository authority for SaaS Identity, Workspaces, and Project Ownership."""

    def __init__(self, engine: DatabaseEngine):
        self.engine = engine

    def create_user(self, user_id: str, email: str, status: UserStatus = UserStatus.ACTIVE) -> User:
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.transaction() as conn:
            conn.execute(
                "INSERT INTO users (id, email, status, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email, status.value, now)
            )
            return User(id=user_id, email=email, status=status, created_at=now)

    def get_user(self, user_id: str) -> Optional[User]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute("SELECT id, email, status, created_at FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            return User(id=row[0], email=row[1], status=UserStatus(row[2]), created_at=row[3])
        finally:
            conn.close()

    def create_workspace(self, workspace_id: str, name: str, created_by: str) -> Workspace:
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.transaction() as conn:
            # 1. Insert Workspace
            conn.execute(
                "INSERT INTO workspaces (id, name, created_by, created_at) VALUES (?, ?, ?, ?)",
                (workspace_id, name, created_by, now)
            )
            # 2. Automatically bind creator as ADMIN
            conn.execute(
                "INSERT INTO workspace_members (workspace_id, user_id, role, created_at) VALUES (?, ?, ?, ?)",
                (workspace_id, created_by, Role.ADMIN.value, now)
            )
            return Workspace(id=workspace_id, name=name, created_by=created_by, created_at=now)

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT id, name, created_by, created_at FROM workspaces WHERE id = ?",
                (workspace_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return Workspace(id=row[0], name=row[1], created_by=row[2], created_at=row[3])
        finally:
            conn.close()

    def add_member(self, workspace_id: str, user_id: str, role: Role) -> WorkspaceMember:
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.transaction() as conn:
            conn.execute(
                """
                INSERT INTO workspace_members (workspace_id, user_id, role, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(workspace_id, user_id) DO UPDATE SET role = excluded.role
                """,
                (workspace_id, user_id, role.value, now)
            )
            return WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role, created_at=now)

    def get_membership(self, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT workspace_id, user_id, role, created_at FROM workspace_members WHERE workspace_id = ? AND user_id = ?",
                (workspace_id, user_id)
            )
            row = cur.fetchone()
            if not row:
                return None
            return WorkspaceMember(workspace_id=row[0], user_id=row[1], role=Role(row[2]), created_at=row[3])
        finally:
            conn.close()

    def list_user_workspaces(self, user_id: str) -> List[Tuple[Workspace, Role]]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                """
                SELECT w.id, w.name, w.created_by, w.created_at, m.role
                FROM workspaces w
                JOIN workspace_members m ON w.id = m.workspace_id
                WHERE m.user_id = ?
                ORDER BY w.created_at DESC
                """,
                (user_id,)
            )
            results = []
            for row in cur.fetchall():
                ws = Workspace(id=row[0], name=row[1], created_by=row[2], created_at=row[3])
                results.append((ws, Role(row[4])))
            return results
        finally:
            conn.close()

    def create_project(
        self,
        project_id: str,
        workspace_id: str,
        name: str,
        created_by: str,
        initial_lifecycle: LifecycleState = LifecycleState.DRAFT,
    ) -> ProjectRecord:
        """
        Creates a new project record.
        Invariant: Every project MUST have a valid, non-null workspace_id.
        """
        if not workspace_id:
            raise ValueError("workspace_id cannot be null or empty.")

        now = datetime.now(timezone.utc).isoformat()
        with self.engine.transaction() as conn:
            # Check workspace existence
            cur = conn.execute("SELECT id FROM workspaces WHERE id = ?", (workspace_id,))
            if not cur.fetchone():
                raise TenantNotFoundError(f"Workspace '{workspace_id}' does not exist.")

            conn.execute(
                """
                INSERT INTO projects (id, workspace_id, created_by, name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, workspace_id, created_by, name, now, now)
            )

            # Initialize project state record in DB with revision 1
            state = ProjectState(
                project_id=project_id,
                revision=1,
                lifecycle_state=initial_lifecycle,
                created_at=now,
                updated_at=now,
            )
            state_json = state.model_dump_json()
            conn.execute(
                """
                INSERT INTO project_states (project_id, workspace_id, revision, lifecycle_state, state_json, updated_at)
                VALUES (?, ?, 1, ?, ?, ?)
                """,
                (project_id, workspace_id, initial_lifecycle.value, state_json, now)
            )

            return ProjectRecord(
                id=project_id,
                workspace_id=workspace_id,
                created_by=created_by,
                name=name,
                created_at=now,
                updated_at=now,
            )

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT id, workspace_id, created_by, name, created_at, updated_at FROM projects WHERE id = ?",
                (project_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ProjectRecord(
                id=row[0],
                workspace_id=row[1],
                created_by=row[2],
                name=row[3],
                created_at=row[4],
                updated_at=row[5],
            )
        finally:
            conn.close()

    def list_projects_for_workspace(self, workspace_id: str) -> List[ProjectRecord]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT id, workspace_id, created_by, name, created_at, updated_at FROM projects WHERE workspace_id = ? ORDER BY created_at DESC",
                (workspace_id,)
            )
            return [
                ProjectRecord(
                    id=row[0],
                    workspace_id=row[1],
                    created_by=row[2],
                    name=row[3],
                    created_at=row[4],
                    updated_at=row[5],
                )
                for row in cur.fetchall()
            ]
        finally:
            conn.close()


class TenantStateRepository:
    """Authoritative repository for ProjectState with transactional CAS in SQL."""

    def __init__(self, engine: DatabaseEngine):
        self.engine = engine

    def load_state(self, project_id: str) -> Optional[ProjectState]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT state_json, revision FROM project_states WHERE project_id = ?",
                (project_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            data = json.loads(row[0])
            state = ProjectState.model_validate(data)
            state._loaded_revision = row[1]
            return state
        finally:
            conn.close()

    def get_state(self, project_id: str) -> Optional[ProjectState]:
        """Convenience alias for load_state."""
        return self.load_state(project_id)

    def atomic_update(
        self,
        project_id: str,
        expected_revision: int,
        new_state: ProjectState,
        workspace_id: Optional[str] = None,
    ) -> ProjectState:
        """Atomic CAS update resolving workspace_id automatically if omitted."""
        ws_id = workspace_id or getattr(new_state, "workspace_id", None)
        if not ws_id:
            conn = self.engine.get_connection()
            try:
                row = conn.execute("SELECT workspace_id FROM project_states WHERE project_id = ?", (project_id,)).fetchone()
                ws_id = row[0] if row else "ws_default"
            finally:
                conn.close()
        return self.update_state_cas(
            project_id=project_id,
            workspace_id=ws_id,
            expected_revision=expected_revision,
            new_state=new_state,
        )

    def update_state_cas(
        self,
        project_id: str,
        workspace_id: str,
        expected_revision: int,
        new_state: ProjectState,
    ) -> ProjectState:
        """
        Applies atomic CAS update to ProjectState.
        Increments revision monotonically.
        Raises StateConflictError if on-disk/DB revision != expected_revision.
        """
        now = datetime.now(timezone.utc).isoformat()
        next_revision = expected_revision + 1

        new_state.revision = next_revision
        new_state.updated_at = now
        state_json = new_state.model_dump_json()

        with self.engine.transaction() as conn:
            # Check current record
            cur = conn.execute(
                "SELECT revision, workspace_id FROM project_states WHERE project_id = ?",
                (project_id,)
            )
            row = cur.fetchone()
            if not row:
                raise StateNotFoundError(f"Project state '{project_id}' not found in database.")

            curr_rev, db_ws = row[0], row[1]
            if db_ws != workspace_id:
                raise TenantSecurityError(f"Cross-tenant mutation rejected: Project belongs to '{db_ws}', not '{workspace_id}'.")

            if curr_rev != expected_revision:
                raise StateConflictError(
                    expected_revision=expected_revision,
                    actual_revision=curr_rev,
                    message=f"State conflict on '{project_id}': expected revision {expected_revision}, found {curr_rev} in DB."
                )

            # Atomic CAS update
            cur = conn.execute(
                """
                UPDATE project_states
                SET revision = ?, lifecycle_state = ?, state_json = ?, updated_at = ?
                WHERE project_id = ? AND revision = ?
                """,
                (next_revision, new_state.lifecycle_state.value, state_json, now, project_id, expected_revision)
            )

            if cur.rowcount == 0:
                raise StateConflictError(
                    expected_revision=expected_revision,
                    actual_revision=None,
                    message=f"Concurrent CAS race on project '{project_id}'."
                )

            # Update projects table timestamp
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))

            new_state._loaded_revision = next_revision
            return new_state


class UsageRepository:
    """Repository for recording metered resource consumption events."""

    def __init__(self, engine: DatabaseEngine):
        self.engine = engine

    def record_usage(
        self,
        workspace_id: str,
        event_type: UsageEventType,
        quantity: float,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> UsageEvent:
        event_id = f"usg_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.transaction() as conn:
            conn.execute(
                """
                INSERT INTO usage_events (id, workspace_id, project_id, user_id, event_type, quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, workspace_id, project_id, user_id, event_type.value, quantity, now)
            )
            return UsageEvent(
                id=event_id,
                workspace_id=workspace_id,
                project_id=project_id,
                user_id=user_id,
                event_type=event_type,
                quantity=quantity,
                created_at=now,
            )

    def get_workspace_usage(self, workspace_id: str) -> Dict[str, float]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT event_type, SUM(quantity) FROM usage_events WHERE workspace_id = ? GROUP BY event_type",
                (workspace_id,)
            )
            return {row[0]: float(row[1]) for row in cur.fetchall()}
        finally:
            conn.close()


_global_engine: Optional[DatabaseEngine] = None


def get_database_engine(db_url: Optional[str] = None) -> DatabaseEngine:
    global _global_engine
    if _global_engine is not None and not db_url:
        return _global_engine
    engine = DatabaseEngine(db_url=db_url)
    if not db_url:
        _global_engine = engine
    return engine


def set_database_engine(engine: Optional[DatabaseEngine]) -> None:
    global _global_engine
    _global_engine = engine
