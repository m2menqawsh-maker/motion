"""
scripts/core/media_intelligence_repository.py
=============================================
SQL-backed persistent implementation of MediaIntelligenceRepository (S27.13 / S27.14).

Architectural Boundaries (ADR-004 DEC-01):
- Implemented in scripts/core/ (approved persistence layer) to satisfy S27.0 architecture guards.
- DatabaseEngine handles connection management, SQLite WAL mode, and transactions.
- Enforces strict multi-tenant isolation (workspace_id).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ai.media.repository import MediaIntelligenceIndexRecord, MediaIntelligenceRepository
from scripts.core.database import DatabaseEngine, get_database_engine

logger = logging.getLogger("scripts.core.media_intelligence_repository")

MEDIA_INTELLIGENCE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS media_intelligence_index (
    workspace_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    analysis_version TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    report_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, asset_id, content_hash, analysis_version)
);
CREATE INDEX IF NOT EXISTS idx_media_intel_ws_asset ON media_intelligence_index(workspace_id, asset_id);
"""


class SQLiteMediaIntelligenceRepository(MediaIntelligenceRepository):
    """
    SQLite-backed implementation of MediaIntelligenceRepository.
    Persists lightweight indexing metadata while StorageService handles heavy reports.
    """

    def __init__(self, db_engine: Optional[DatabaseEngine] = None):
        self.db = db_engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.db.transaction() as conn:
            for statement in MEDIA_INTELLIGENCE_SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    def save_index(self, record: MediaIntelligenceIndexRecord) -> None:
        created_at_iso = record.created_at.isoformat()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO media_intelligence_index (
                    workspace_id, asset_id, content_hash, analysis_version,
                    storage_key, report_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, asset_id, content_hash, analysis_version) DO UPDATE SET
                    storage_key = excluded.storage_key,
                    report_hash = excluded.report_hash,
                    created_at = excluded.created_at;
                """,
                (
                    record.workspace_id,
                    record.asset_id,
                    record.content_hash,
                    record.analysis_version,
                    record.storage_key,
                    record.report_hash,
                    created_at_iso,
                ),
            )

    def get_index(
        self,
        workspace_id: str,
        asset_id: str,
        content_hash: str,
        analysis_version: str,
    ) -> Optional[MediaIntelligenceIndexRecord]:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT workspace_id, asset_id, content_hash, analysis_version,
                       storage_key, report_hash, created_at
                FROM media_intelligence_index
                WHERE workspace_id = ? AND asset_id = ? AND content_hash = ? AND analysis_version = ?;
                """,
                (workspace_id, asset_id, content_hash, analysis_version),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return MediaIntelligenceIndexRecord(
                workspace_id=row[0],
                asset_id=row[1],
                content_hash=row[2],
                analysis_version=row[3],
                storage_key=row[4],
                report_hash=row[5],
                created_at=datetime.fromisoformat(row[6]),
            )

    def list_indices(
        self,
        workspace_id: str,
        asset_id: str,
    ) -> List[MediaIntelligenceIndexRecord]:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT workspace_id, asset_id, content_hash, analysis_version,
                       storage_key, report_hash, created_at
                FROM media_intelligence_index
                WHERE workspace_id = ? AND asset_id = ?
                ORDER BY created_at DESC;
                """,
                (workspace_id, asset_id),
            )
            rows = cursor.fetchall()
            return [
                MediaIntelligenceIndexRecord(
                    workspace_id=row[0],
                    asset_id=row[1],
                    content_hash=row[2],
                    analysis_version=row[3],
                    storage_key=row[4],
                    report_hash=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                )
                for row in rows
            ]

    def delete_index(
        self,
        workspace_id: str,
        asset_id: str,
        analysis_version: str,
    ) -> bool:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                DELETE FROM media_intelligence_index
                WHERE workspace_id = ? AND asset_id = ? AND analysis_version = ?;
                """,
                (workspace_id, asset_id, analysis_version),
            )
            return cursor.rowcount > 0


class InMemoryMediaIntelligenceRepository(MediaIntelligenceRepository):
    """
    Deterministic in-memory implementation of MediaIntelligenceRepository for testing.
    """

    def __init__(self) -> None:
        # Key: (workspace_id, asset_id, content_hash, analysis_version)
        self._store: Dict[Tuple[str, str, str, str], MediaIntelligenceIndexRecord] = {}

    def save_index(self, record: MediaIntelligenceIndexRecord) -> None:
        key = (record.workspace_id, record.asset_id, record.content_hash, record.analysis_version)
        self._store[key] = record

    def get_index(
        self,
        workspace_id: str,
        asset_id: str,
        content_hash: str,
        analysis_version: str,
    ) -> Optional[MediaIntelligenceIndexRecord]:
        key = (workspace_id, asset_id, content_hash, analysis_version)
        return self._store.get(key)

    def list_indices(
        self,
        workspace_id: str,
        asset_id: str,
    ) -> List[MediaIntelligenceIndexRecord]:
        return [
            rec for ((ws, aid, _, _), rec) in self._store.items()
            if ws == workspace_id and aid == asset_id
        ]

    def delete_index(
        self,
        workspace_id: str,
        asset_id: str,
        analysis_version: str,
    ) -> bool:
        keys_to_delete = [
            k for k in self._store
            if k[0] == workspace_id and k[1] == asset_id and k[3] == analysis_version
        ]
        if not keys_to_delete:
            return False
        for k in keys_to_delete:
            del self._store[k]
        return True
