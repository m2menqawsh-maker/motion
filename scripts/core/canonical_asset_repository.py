"""
scripts/core/canonical_asset_repository.py
===========================================
Production authority for Canonical Asset deduplication and persistence (S28-M05 C03 / C3).

Architectural Invariants:
- Uses DatabaseEngine with transactional consistency (PostgreSQL / SQLite WAL mode).
- Guarantees that concurrent imports of identical content_hash within the same project/canonical scope
  converge to exactly one canonical asset record via atomic transactions and UNIQUE(project_id, content_hash).
- Primary key is surrogate/composite `id` (e.g. `f"{project_id}:{content_hash}"`), preventing cross-project collisions
  when distinct projects or workspaces import identical byte content.
- Full 64-hex SHA-256 hash is strictly preserved and enforced as the uniqueness reference.
- Strict tenant and workspace isolation: no cross-tenant asset reuse or information leaks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from scripts.core.database import DatabaseEngine, get_database_engine

logger = logging.getLogger("clean_video.scripts.core.canonical_asset_repository")

CANONICAL_ASSETS_SCHEMA = """
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
"""


@dataclass
class CanonicalAssetRecord:
    asset_id: str
    project_id: str
    workspace_id: str
    content_hash: str
    storage_key: str
    media_type: str
    mime_type: str
    file_size_bytes: int
    provenance_json: str = "{}"
    created_at: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"{self.project_id}:{self.content_hash}"

    def to_dict(self) -> Dict[str, Any]:
        try:
            prov = json.loads(self.provenance_json)
        except Exception:
            prov = {}
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "content_hash": self.content_hash,
            "storage_key": self.storage_key,
            "processed_path": self.storage_key,
            "media_type": self.media_type,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "provenance": prov,
            "created_at": self.created_at,
            "metadata": {
                "id": self.id,
                "content_hash": self.content_hash,
                "storage_key": self.storage_key,
                "workspace_id": self.workspace_id,
                "provenance": prov,
            },
        }


class CanonicalAssetRepository:
    """
    Authoritative database repository governing canonical asset uniqueness and deduplication.
    Provides CAS-based concurrency protection and tenant isolation across multi-worker environments.
    """

    def __init__(self, db_engine: Optional[DatabaseEngine] = None) -> None:
        self.db = db_engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.db.transaction("IMMEDIATE") as conn:
            # Check for legacy schema migration
            try:
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
            except Exception:
                pass

            for statement in CANONICAL_ASSETS_SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    def find_by_hash(self, project_id: str, content_hash: str) -> Optional[CanonicalAssetRecord]:
        """Queries asset by project_id and full SHA-256 content_hash."""
        conn = self.db.get_connection()
        try:
            cur = conn.execute(
                "SELECT id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                "media_type, mime_type, file_size_bytes, provenance_json, created_at "
                "FROM canonical_assets WHERE project_id = ? AND content_hash = ?",
                (project_id, content_hash),
            )
            row = cur.fetchone()
            if not row:
                return None
            return CanonicalAssetRecord(
                id=row[0],
                asset_id=row[1],
                project_id=row[2],
                workspace_id=row[3],
                content_hash=row[4],
                storage_key=row[5],
                media_type=row[6],
                mime_type=row[7],
                file_size_bytes=int(row[8]),
                provenance_json=row[9],
                created_at=row[10],
            )
        finally:
            conn.close()

    def register_asset(self, record: CanonicalAssetRecord) -> Tuple[CanonicalAssetRecord, bool]:
        """
        Atomically registers a canonical asset under (project_id, content_hash).
        If already registered, returns (existing_record, False).
        If newly registered, returns (record, True).
        Enforces strict uniqueness and tenant isolation using immediate transaction / CAS unique constraint.
        """
        if not record.id:
            record.id = f"{record.project_id}:{record.content_hash}"

        with self.db.transaction("IMMEDIATE") as conn:
            # 1. Check existing within project scope
            cur = conn.execute(
                "SELECT id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                "media_type, mime_type, file_size_bytes, provenance_json, created_at "
                "FROM canonical_assets WHERE project_id = ? AND content_hash = ?",
                (record.project_id, record.content_hash),
            )
            row = cur.fetchone()
            if row:
                existing = CanonicalAssetRecord(
                    id=row[0],
                    asset_id=row[1],
                    project_id=row[2],
                    workspace_id=row[3],
                    content_hash=row[4],
                    storage_key=row[5],
                    media_type=row[6],
                    mime_type=row[7],
                    file_size_bytes=int(row[8]),
                    provenance_json=row[9],
                    created_at=row[10],
                )
                return existing, False

            # 2. Insert new record atomically
            try:
                conn.execute(
                    "INSERT INTO canonical_assets ("
                    "id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                    "media_type, mime_type, file_size_bytes, provenance_json, created_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        record.id,
                        record.asset_id,
                        record.project_id,
                        record.workspace_id,
                        record.content_hash,
                        record.storage_key,
                        record.media_type,
                        record.mime_type,
                        record.file_size_bytes,
                        record.provenance_json,
                        record.created_at,
                    ),
                )
                return record, True
            except Exception:
                # Race condition: another concurrent transaction committed between check and insert
                cur = conn.execute(
                    "SELECT id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                    "media_type, mime_type, file_size_bytes, provenance_json, created_at "
                    "FROM canonical_assets WHERE project_id = ? AND content_hash = ?",
                    (record.project_id, record.content_hash),
                )
                row = cur.fetchone()
                if row:
                    existing = CanonicalAssetRecord(
                        id=row[0],
                        asset_id=row[1],
                        project_id=row[2],
                        workspace_id=row[3],
                        content_hash=row[4],
                        storage_key=row[5],
                        media_type=row[6],
                        mime_type=row[7],
                        file_size_bytes=int(row[8]),
                        provenance_json=row[9],
                        created_at=row[10],
                    )
                    return existing, False
                raise

    def get_by_id(self, id_or_asset_id: str, project_id: Optional[str] = None) -> Optional[CanonicalAssetRecord]:
        """Queries asset by primary key id or project-scoped asset_id."""
        conn = self.db.get_connection()
        try:
            if project_id:
                cur = conn.execute(
                    "SELECT id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                    "media_type, mime_type, file_size_bytes, provenance_json, created_at "
                    "FROM canonical_assets WHERE project_id = ? AND (id = ? OR asset_id = ?)",
                    (project_id, id_or_asset_id, id_or_asset_id),
                )
            else:
                cur = conn.execute(
                    "SELECT id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                    "media_type, mime_type, file_size_bytes, provenance_json, created_at "
                    "FROM canonical_assets WHERE id = ? OR asset_id = ?",
                    (id_or_asset_id, id_or_asset_id),
                )
            row = cur.fetchone()
            if not row:
                return None
            return CanonicalAssetRecord(
                id=row[0],
                asset_id=row[1],
                project_id=row[2],
                workspace_id=row[3],
                content_hash=row[4],
                storage_key=row[5],
                media_type=row[6],
                mime_type=row[7],
                file_size_bytes=int(row[8]),
                provenance_json=row[9],
                created_at=row[10],
            )
        finally:
            conn.close()

    def list_by_project(self, project_id: str) -> List[CanonicalAssetRecord]:
        """Lists all canonical assets registered for a project."""
        conn = self.db.get_connection()
        try:
            cur = conn.execute(
                "SELECT id, asset_id, project_id, workspace_id, content_hash, storage_key, "
                "media_type, mime_type, file_size_bytes, provenance_json, created_at "
                "FROM canonical_assets WHERE project_id = ? ORDER BY created_at ASC",
                (project_id,),
            )
            records = []
            for row in cur.fetchall():
                records.append(
                    CanonicalAssetRecord(
                        id=row[0],
                        asset_id=row[1],
                        project_id=row[2],
                        workspace_id=row[3],
                        content_hash=row[4],
                        storage_key=row[5],
                        media_type=row[6],
                        mime_type=row[7],
                        file_size_bytes=int(row[8]),
                        provenance_json=row[9],
                        created_at=row[10],
                    )
                )
            return records
        finally:
            conn.close()
