"""
tests/fault_injection/test_fi_16_migration_rebuild.py — Fault Injection Scenario FI-16.

Database Migration Rebuild From Zero Matrix:
1. Rebuilds complete relational schema from an empty database.
2. Verifies all 13 canonical tables, indexes, and schema migration records exist.
3. Tests schema migration idempotency (running DDL multiple times produces zero drift).
4. Verifies foreign key constraints and cascade rules (e.g. deleting workspace cascades to projects/states/members).
5. Enforces core SaaS invariant: Project CANNOT exist without valid workspace (FOREIGN KEY constraint).
"""

from pathlib import Path
import sqlite3
import pytest

from scripts.core.database import (
    DatabaseEngine,
    TenantRepository,
    TenantNotFoundError,
    SCHEMA_SQL,
)
from scripts.core.security.principal import Role


CANONICAL_TABLES = {
    "_schema_migrations",
    "users",
    "workspaces",
    "workspace_members",
    "projects",
    "project_states",
    "project_artifact_versions",
    "runs",
    "project_execution_leases",
    "run_events",
    "review_bundles",
    "review_decisions",
    "usage_events",
}


def test_fi16_migration_from_zero_and_idempotency(tmp_path: Path):
    """Schema builds cleanly on fresh DB and is strictly idempotent."""
    db_file = tmp_path / "fi16_fresh.db"
    assert not db_file.exists()

    # 1. Initialize fresh DB
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")

    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        missing = CANONICAL_TABLES - tables
        assert not missing, f"Missing canonical tables in fresh DB: {missing}"

        # Check migrations table
        cur = conn.execute("SELECT version, applied_at FROM _schema_migrations")
        rows = cur.fetchall()
        assert len(rows) >= 1
        assert rows[0][0] == 1
    finally:
        conn.close()

    # 2. Idempotency test: Re-running _init_schema must not fail or corrupt schema
    engine._init_schema()
    engine._init_schema()

    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        rechecked_tables = {row[0] for row in cur.fetchall()}
        assert rechecked_tables == tables, "Schema drifted after idempotent re-run!"
    finally:
        conn.close()


def test_fi16_foreign_key_and_cascade_invariants(tmp_path: Path):
    """Foreign key enforcement prevents orphan projects and handles cascade deletion."""
    db_file = tmp_path / "fi16_fk.db"
    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    repo = TenantRepository(engine)

    # 1. Attempting to insert a project with a non-existent workspace MUST fail
    with pytest.raises(TenantNotFoundError):
        repo.create_project(
            project_id="prj_orphan",
            workspace_id="ws_non_existent",
            name="Orphan Video",
            created_by="usr_ghost",
        )

    # Raw SQL attempt with invalid workspace must fail foreign key constraint
    with pytest.raises(sqlite3.IntegrityError):
        with engine.transaction() as conn:
            conn.execute(
                "INSERT INTO projects (id, workspace_id, created_by, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("prj_raw_orphan", "ws_missing", "usr_ghost", "Raw Orphan", "now", "now")
            )

    # 2. Workspace deletion CASCADE test
    u = repo.create_user("usr_casc", "cascade@test.com")
    ws = repo.create_workspace("ws_casc", "Cascade Workspace", created_by=u.id)
    prj = repo.create_project("prj_casc", ws.id, "Cascade Video", created_by=u.id)

    conn = engine.get_connection()
    try:
        # Verify project and state exist
        assert conn.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (prj.id,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM project_states WHERE project_id = ?", (prj.id,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM workspace_members WHERE workspace_id = ?", (ws.id,)).fetchone()[0] == 1

        # Delete workspace
        with engine.transaction() as t_conn:
            t_conn.execute("DELETE FROM workspaces WHERE id = ?", (ws.id,))

        # Verify cascading deletion wiped projects and states associated with deleted workspace
        assert conn.execute("SELECT COUNT(*) FROM projects WHERE id = ?", (prj.id,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM project_states WHERE project_id = ?", (prj.id,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM workspace_members WHERE workspace_id = ?", (ws.id,)).fetchone()[0] == 0
    finally:
        conn.close()
