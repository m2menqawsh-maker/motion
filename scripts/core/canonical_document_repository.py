"""
scripts/core/canonical_document_repository.py — Authoritative Production Persistence for Canonical VideoDocument.
S28-R14: Enforces atomic CAS revision updates, immutable generation storage, and tenant isolation.

Architectural Authority:
- PostgreSQL / SQLite (via DatabaseEngine) is the authoritative transaction and revision CAS authority.
- StorageService is the authoritative byte persistence authority for heavy canonical documents.
- Logical commit protocol:
  1. Write candidate generation to StorageService under immutable key:
     workspaces/{workspace_id}/projects/{project_id}/blueprints/rev_{next_revision}_{hash[:16]}/blueprint.json
  2. Validate document against Canonical BlueprintV2 schema.
  3. Transactional CAS:
     Verify expected_revision == current_revision in project_states.
     Increment revision monotonically to next_revision.
     Insert pointer record in project_artifact_versions.
     Record audit/provenance event in run_events.
  4. If CAS fails: candidate generation is never referenced and remains uncommitted/abandoned.
  5. Sync local disk 05_blueprint.json if project directory exists on worker/disk.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from scripts.core.database import DatabaseEngine, get_database_engine, TenantSecurityError
from scripts.core.state_store import StateConflictError, StateNotFoundError
from scripts.core.storage.storage_service import (
    StorageService,
    get_storage_service,
    build_storage_key,
    StorageNotFoundError,
)
from scripts.core.blueprint_model import BlueprintV2
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.blueprint_loader import load_blueprint

logger = logging.getLogger("clean_video.canonical_document_repo")


class RevisionConflictError(StateConflictError):
    """Raised when an operation's expected base revision does not match current persistent revision."""
    pass


class DocumentValidationError(ValueError):
    """Raised when a candidate document fails semantic validation."""
    pass


class CanonicalDocumentRepository:
    """Production persistent authority for Canonical VideoDocument (BlueprintV2)."""

    def __init__(
        self,
        db_engine: Optional[DatabaseEngine] = None,
        storage_service: Optional[StorageService] = None,
    ) -> None:
        self._db = db_engine
        self._storage = storage_service

    @property
    def db(self) -> DatabaseEngine:
        return self._db or get_database_engine()

    @property
    def storage(self) -> StorageService:
        return self._storage or get_storage_service()

    def get_document(
        self,
        workspace_id: str,
        project_id: str,
        revision: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Loads the authoritative Canonical VideoDocument for a project.

        Returns:
            (document_dict, revision: int)
        """
        conn = self.db.get_connection()
        try:
            # 1. Fetch project state and verify tenant
            cur = conn.execute(
                "SELECT revision, workspace_id FROM project_states WHERE project_id = ?",
                (project_id,),
            )
            state_row = cur.fetchone()
            if not state_row:
                raise StateNotFoundError(f"Project '{project_id}' not found in database.")

            curr_rev, db_ws = state_row[0], state_row[1]
            if db_ws != workspace_id:
                raise TenantSecurityError(
                    f"Cross-tenant access rejected: Project belongs to '{db_ws}', not '{workspace_id}'."
                )

            if revision is None:
                cur = conn.execute(
                    """
                    SELECT revision FROM project_artifact_versions
                    WHERE workspace_id = ? AND project_id = ? AND artifact_kind = 'blueprint'
                    ORDER BY revision DESC LIMIT 1
                    """,
                    (workspace_id, project_id),
                )
                latest_art = cur.fetchone()
                target_rev = latest_art[0] if latest_art else curr_rev
            else:
                target_rev = revision

            is_managed = os.environ.get("AGY_IS_MANAGED") == "1" or os.environ.get("MOTION_ENV") == "production"

            # 2. Lookup pointer in project_artifact_versions
            cur = conn.execute(
                """
                SELECT storage_key, content_hash
                FROM project_artifact_versions
                WHERE workspace_id = ? AND project_id = ? AND artifact_kind = 'blueprint' AND revision = ?
                """,
                (workspace_id, project_id, target_rev),
            )
            art_row = cur.fetchone()

            if art_row:
                storage_key, expected_hash = art_row[0], art_row[1]
                if self.storage.exists(storage_key):
                    raw_bytes = self.storage.get(storage_key)
                    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
                    if expected_hash and actual_hash != expected_hash:
                        raise StateNotFoundError(
                            f"Canonical document integrity error: hash mismatch for revision {target_rev}. "
                            f"Expected {expected_hash}, got {actual_hash}"
                        )
                    doc = json.loads(raw_bytes.decode("utf-8"))
                    return doc, target_rev
                elif is_managed:
                    raise StateNotFoundError(
                        f"Canonical document object for revision {target_rev} not found in storage (key: '{storage_key}')."
                    )
            elif is_managed and revision is not None:
                raise StateNotFoundError(
                    f"Canonical document revision {revision} not found in repository for project '{project_id}'."
                )

            # 3. Fallback: check local disk if exists (dev / migration fallback)
            disk_path = Path("projects") / project_id / "05_blueprint.json"
            if not disk_path.exists():
                disk_path = Path("projects") / project_id / "blueprint.json"

            if disk_path.exists():
                disk_bytes = disk_path.read_bytes()
                doc = json.loads(disk_bytes.decode("utf-8"))
                disk_rev = doc.get("revision", 1)
                if revision is not None and disk_rev != revision:
                    raise StateNotFoundError(
                        f"Local disk document revision {disk_rev} does not match requested revision {revision}."
                    )
                if art_row and art_row[1]:
                    disk_hash = hashlib.sha256(disk_bytes).hexdigest()
                    if disk_hash != art_row[1]:
                        raise StateNotFoundError(
                            f"Local disk document hash {disk_hash} does not match expected hash {art_row[1]}."
                        )
                return doc, disk_rev

            raise StateNotFoundError(
                f"Canonical document not found for project '{project_id}' at revision {target_rev}."
            )
        finally:
            conn.close()

    def commit_candidate(
        self,
        workspace_id: str,
        project_id: str,
        expected_revision: int,
        candidate_doc: Union[Dict[str, Any], BlueprintV2],
        actor_id: str,
        operation_id: str,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], int, str]:
        """
        Atomically commits an updated Canonical VideoDocument using CAS.

        Returns:
            (committed_doc_dict, next_revision, storage_key)
        Raises:
            RevisionConflictError: If expected_revision != current_revision.
            TenantSecurityError: If workspace_id mismatch.
            DocumentValidationError: If candidate_doc is semantically invalid.
        """
        if isinstance(candidate_doc, BlueprintV2):
            doc_dict = candidate_doc.model_dump(mode="json")
        else:
            doc_dict = dict(candidate_doc)

        # 1. Validate candidate document
        val_res = validate_blueprint_v2(doc_dict, expected_project_id=project_id)
        if not val_res.ok:
            raise DocumentValidationError(
                f"Candidate BlueprintV2 validation failed: {'; '.join(val_res.errors)}"
            )

        next_revision = expected_revision + 1
        doc_dict["revision"] = next_revision
        if "meta" not in doc_dict:
            doc_dict["meta"] = {}
        doc_dict["meta"]["last_operation_id"] = operation_id
        doc_dict["meta"]["last_actor_id"] = actor_id
        doc_dict["meta"]["committed_at"] = datetime.now(timezone.utc).isoformat()

        doc_bytes = json.dumps(doc_dict, indent=2, ensure_ascii=False).encode("utf-8")
        content_hash = hashlib.sha256(doc_bytes).hexdigest()
        hash_short = content_hash[:16]

        # 2. Upload immutable candidate generation to StorageService
        candidate_key = build_storage_key(
            workspace_id=workspace_id,
            project_id=project_id,
            category="blueprints",
            item_id=f"rev_{next_revision}_{hash_short}",
            filename="blueprint.json",
        )
        self.storage.put(candidate_key, doc_bytes, content_type="application/json")

        now_iso = datetime.now(timezone.utc).isoformat()

        # 3. Transactional CAS in SQL
        with self.db.transaction("IMMEDIATE") as conn:
            # Check current project state and tenant
            cur = conn.execute(
                "SELECT revision, workspace_id FROM project_states WHERE project_id = ?",
                (project_id,),
            )
            row = cur.fetchone()
            if not row:
                raise StateNotFoundError(f"Project state '{project_id}' not found.")

            curr_state_rev, db_ws = row[0], row[1]
            if db_ws != workspace_id:
                raise TenantSecurityError(
                    f"Cross-tenant mutation rejected: Project belongs to '{db_ws}', not '{workspace_id}'."
                )

            # Query latest blueprint revision from project_artifact_versions
            cur = conn.execute(
                """
                SELECT revision
                FROM project_artifact_versions
                WHERE workspace_id = ? AND project_id = ? AND artifact_kind = 'blueprint'
                ORDER BY revision DESC LIMIT 1
                """,
                (workspace_id, project_id),
            )
            art_latest = cur.fetchone()
            current_bp_rev = art_latest[0] if art_latest else curr_state_rev

            if current_bp_rev != expected_revision:
                raise RevisionConflictError(
                    expected_revision=expected_revision,
                    actual_revision=current_bp_rev,
                    message=(
                        f"REVISION_CONFLICT: Expected revision {expected_revision}, "
                        f"but persistent canonical revision is currently {current_bp_rev}."
                    ),
                )

            # Atomic update of project_states updated_at under state revision check
            conn.execute(
                """
                UPDATE project_states
                SET updated_at = ?
                WHERE project_id = ? AND revision = ?
                """,
                (now_iso, project_id, curr_state_rev),
            )

            # Insert immutable artifact version pointer
            art_version_id = f"art_bp_{project_id}_{next_revision}_{hash_short}"
            try:
                conn.execute(
                    """
                    INSERT INTO project_artifact_versions (
                        id, workspace_id, project_id, artifact_kind, revision,
                        content_hash, storage_key, created_by, created_at
                    ) VALUES (?, ?, ?, 'blueprint', ?, ?, ?, ?, ?)
                    """,
                    (
                        art_version_id,
                        workspace_id,
                        project_id,
                        next_revision,
                        content_hash,
                        candidate_key,
                        actor_id,
                        now_iso,
                    ),
                )
            except Exception as insert_err:
                raise RevisionConflictError(
                    expected_revision=expected_revision,
                    actual_revision=None,
                    message=f"Concurrent CAS race committing revision on project '{project_id}': {insert_err}",
                ) from insert_err

            # Update project timestamp
            conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now_iso, project_id))

            # Record durable audit events
            authoring_run_id = f"authoring_{project_id}"
            seq_cur = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_events WHERE run_id = ?",
                (authoring_run_id,),
            )
            seq = seq_cur.fetchone()[0]

            event_id = f"evt_mut_{project_id}_{next_revision}_{operation_id[:8]}"
            event_payload = {
                "operation_id": operation_id,
                "actor_id": actor_id,
                "base_revision": expected_revision,
                "result_revision": next_revision,
                "content_hash": content_hash,
                "storage_key": candidate_key,
                "provenance": provenance or {},
            }
            conn.execute(
                """
                INSERT INTO run_events (
                    event_id, workspace_id, project_id, run_id, sequence,
                    event_type, stage, timestamp, payload_json
                ) VALUES (?, ?, ?, ?, ?, 'AUTHORING_MUTATION_COMMITTED', 'authoring', ?, ?)
                """,
                (event_id, workspace_id, project_id, authoring_run_id, seq, now_iso, json.dumps(event_payload)),
            )

            conn.execute(
                """
                INSERT INTO run_events (
                    event_id, workspace_id, project_id, run_id, sequence,
                    event_type, stage, timestamp, payload_json
                ) VALUES (?, ?, ?, ?, ?, 'REVISION_ADVANCED', 'authoring', ?, ?)
                """,
                (
                    f"evt_rev_{project_id}_{next_revision}",
                    workspace_id,
                    project_id,
                    authoring_run_id,
                    seq + 1,
                    now_iso,
                    json.dumps({"from_revision": expected_revision, "to_revision": next_revision}),
                ),
            )

        # 4. Sync to local disk for dev / local tooling compatibility
        proj_dir = Path("projects") / project_id
        if proj_dir.exists():
            disk_file = proj_dir / "05_blueprint.json"
            try:
                disk_file.write_text(json.dumps(doc_dict, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to sync disk file {disk_file}: {e}")

            # S09: Invalidate downstream review decisions upon canonical mutation
            try:
                from scripts.core.review_service import ReviewService
                ReviewService.invalidate_review(
                    proj_dir,
                    reason=f"Canonical blueprint mutated to revision {next_revision} by {actor_id}",
                )
            except Exception as inv_err:
                logger.warning(f"Failed to invalidate downstream review: {inv_err}")

        logger.info(
            f"Committed revision {next_revision} for project {project_id} under key {candidate_key}"
        )
        return doc_dict, next_revision, candidate_key
