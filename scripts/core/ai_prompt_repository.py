"""
scripts/core/ai_prompt_repository.py
====================================
SQLite-backed persistent implementation of PromptRepository (S27.18).

Architectural Boundaries (ADR-004 DEC-01):
- Implemented in scripts/core/ to satisfy S27.0 architecture guards.
- DatabaseEngine handles connection management, SQLite WAL mode, and transactions.
- Enforces strict version immutability and multi-tenant isolation.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from ai.contracts.prompt import (
    PromptContract,
    PromptMetadata,
    PromptNotFoundError,
    PromptStatus,
    PromptVersionImmutableError,
    PromptVersionNotFoundError,
)
from ai.prompts.repository import PromptRepository
from scripts.core.database import DatabaseEngine, get_database_engine


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_prompts (
    prompt_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    hash TEXT NOT NULL,
    status TEXT NOT NULL,
    template TEXT NOT NULL,
    system_prompt TEXT,
    variables_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    workspace_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (prompt_id, version, workspace_id)
);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_lookup ON ai_prompts(prompt_id, workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_version ON ai_prompts(prompt_id, workspace_id, version);
"""


class SQLPromptRepository(PromptRepository):
    """Production-grade persistent repository for versioned prompt entities."""

    def __init__(self, engine: Optional[DatabaseEngine] = None):
        self.engine = engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.engine.transaction("IMMEDIATE") as conn:
            for statement in SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    @staticmethod
    def _row_to_contract(row: Any) -> PromptContract:
        data: Dict[str, Any] = dict(row)
        variables = json.loads(data["variables_json"]) if data.get("variables_json") else []
        meta = json.loads(data["metadata_json"]) if data.get("metadata_json") else {}
        ws_id = data.get("workspace_id")
        if ws_id == "__PLATFORM__":
            ws_id = None

        return PromptContract(
            prompt_id=data["prompt_id"],
            version=int(data["version"]),
            hash=data["hash"],
            status=PromptStatus(data["status"]),
            template=data["template"],
            system_prompt=data.get("system_prompt"),
            variables=variables,
            created_at=data["created_at"],
            workspace_id=ws_id,
            metadata=PromptMetadata.model_validate(meta),
        )

    def save_prompt(self, prompt: PromptContract) -> PromptContract:
        ws_key = prompt.workspace_id if prompt.workspace_id is not None else "__PLATFORM__"
        vars_json = json.dumps(prompt.variables)
        meta_json = json.dumps(prompt.metadata.model_dump(mode="json"))

        with self.engine.transaction("IMMEDIATE") as conn:
            # Check if this exact version already exists
            cur = conn.execute(
                "SELECT hash FROM ai_prompts WHERE prompt_id = ? AND version = ? AND workspace_id = ?",
                (prompt.prompt_id, prompt.version, ws_key),
            )
            existing = cur.fetchone()
            if existing:
                raise PromptVersionImmutableError(
                    f"Prompt '{prompt.prompt_id}' version {prompt.version} already exists and is immutable."
                )

            try:
                conn.execute(
                    """
                    INSERT INTO ai_prompts (
                        prompt_id, version, hash, status, template,
                        system_prompt, variables_json, created_at,
                        workspace_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prompt.prompt_id,
                        prompt.version,
                        prompt.hash,
                        prompt.status.value,
                        prompt.template,
                        prompt.system_prompt,
                        vars_json,
                        prompt.created_at.isoformat(),
                        ws_key,
                        meta_json,
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise PromptVersionImmutableError(
                    f"Integrity violation: prompt '{prompt.prompt_id}' version {prompt.version} is immutable ({e})."
                )
        return prompt

    def get_prompt(
        self,
        prompt_id: str,
        version: int,
        workspace_id: Optional[str] = None,
    ) -> Optional[PromptContract]:
        ws_key = workspace_id if workspace_id is not None else "__PLATFORM__"
        conn = self.engine.get_connection()
        try:
            # Tenant-scoped lookup first
            cur = conn.execute(
                "SELECT * FROM ai_prompts WHERE prompt_id = ? AND version = ? AND workspace_id = ?",
                (prompt_id, version, ws_key),
            )
            row = cur.fetchone()
            # If not found and workspace_id was specified, fall back to global platform prompt
            if not row and workspace_id is not None:
                cur = conn.execute(
                    "SELECT * FROM ai_prompts WHERE prompt_id = ? AND version = ? AND workspace_id = '__PLATFORM__'",
                    (prompt_id, version),
                )
                row = cur.fetchone()
            if not row:
                return None
            return self._row_to_contract(row)
        finally:
            conn.close()

    def get_active_production_prompt(
        self,
        prompt_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[PromptContract]:
        ws_key = workspace_id if workspace_id is not None else "__PLATFORM__"
        conn = self.engine.get_connection()
        try:
            # First look for active PRODUCTION in tenant scope
            cur = conn.execute(
                """
                SELECT * FROM ai_prompts
                WHERE prompt_id = ? AND workspace_id = ? AND status = 'PRODUCTION'
                ORDER BY version DESC LIMIT 1
                """,
                (prompt_id, ws_key),
            )
            row = cur.fetchone()
            if not row and workspace_id is not None:
                # Fallback to platform-level active PRODUCTION prompt
                cur = conn.execute(
                    """
                    SELECT * FROM ai_prompts
                    WHERE prompt_id = ? AND workspace_id = '__PLATFORM__' AND status = 'PRODUCTION'
                    ORDER BY version DESC LIMIT 1
                    """,
                    (prompt_id,),
                )
                row = cur.fetchone()
            if not row:
                return None
            return self._row_to_contract(row)
        finally:
            conn.close()

    def list_versions(
        self,
        prompt_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[PromptContract]:
        ws_key = workspace_id if workspace_id is not None else "__PLATFORM__"
        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                """
                SELECT * FROM ai_prompts
                WHERE prompt_id = ? AND workspace_id = ?
                ORDER BY version ASC
                """,
                (prompt_id, ws_key),
            )
            rows = cur.fetchall()
            return [self._row_to_contract(r) for r in rows]
        finally:
            conn.close()

    def update_status(
        self,
        prompt_id: str,
        version: int,
        new_status: PromptStatus,
        workspace_id: Optional[str] = None,
    ) -> PromptContract:
        ws_key = workspace_id if workspace_id is not None else "__PLATFORM__"
        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                "SELECT * FROM ai_prompts WHERE prompt_id = ? AND version = ? AND workspace_id = ?",
                (prompt_id, version, ws_key),
            )
            row = cur.fetchone()
            if not row:
                raise PromptVersionNotFoundError(
                    f"Prompt '{prompt_id}' version {version} not found in workspace '{workspace_id}'."
                )

            conn.execute(
                """
                UPDATE ai_prompts
                SET status = ?
                WHERE prompt_id = ? AND version = ? AND workspace_id = ?
                """,
                (new_status.value, prompt_id, version, ws_key),
            )

        updated = self.get_prompt(prompt_id, version, workspace_id)
        if not updated:
            raise PromptNotFoundError(f"Failed to retrieve updated prompt '{prompt_id}' v{version}")
        return updated
