"""
Run Service for S21.

Handles run creation, validation, idempotency enforcement, and querying.
Interacts exclusively with RunRepository and StateStore.
"""

import hashlib
import json
import uuid
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from api.core.errors import ProjectNotFoundError, RunNotFoundError, IdempotencyConflictError, RunNotCancellableError, ProvenanceConflictError
from scripts.core.run_model import RunRecord, RunStatus, RunEvent, InvalidRunTransitionError
from scripts.core.run_repository import RunRepository
from scripts.core.state_store import StateStore
from scripts.security.path_security import validate_project_id
from scripts.core.database import TenantSecurityError


class RunService:
    """Domain service for managing pipeline runs."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        return Path(f"projects/{project_id}")

    @classmethod
    def _compute_payload_hash(cls, payload: Optional[Dict[str, Any]]) -> str:
        serialized = json.dumps(payload or {}, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def create_run(
        cls,
        project_id: str,
        idempotency_key: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        db_path: Optional[Path | str] = None,
        workspace_id: Optional[str] = None,
    ) -> Tuple[RunRecord, bool]:
        """
        Creates a durable RunRecord with status QUEUED.
        
        Returns:
            (RunRecord, is_created: bool)
        
        Raises:
            ProjectNotFoundError: If the project directory does not exist.
            IdempotencyConflictError: If idempotency_key was used with a different payload.
        """
        validate_project_id(project_id)
        proj_dir = cls._get_project_dir(project_id)
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)

        repo = RunRepository(db_path=db_path)
        payload_hash = cls._compute_payload_hash(payload)

        # Determine verified workspace_id
        actual_ws_id = workspace_id
        state = StateStore.load(proj_dir)
        input_revision = state.revision if state else 1

        if not actual_ws_id and state and getattr(state, "workspace_id", None):
            actual_ws_id = state.workspace_id
        if not actual_ws_id:
            try:
                from scripts.core.database import get_database_engine, TenantRepository
                repo_tenant = TenantRepository(get_database_engine())
                prj_rec = repo_tenant.get_project(project_id)
                if prj_rec:
                    actual_ws_id = prj_rec.workspace_id
            except Exception:
                pass
        actual_ws_id = actual_ws_id or "ws_default"

        # Verify tenant workspace ownership
        if state and getattr(state, "workspace_id", None):
            if state.workspace_id != actual_ws_id and actual_ws_id != "ws_default":
                raise TenantSecurityError(f"Cross-tenant access violation: project '{project_id}' belongs to workspace '{state.workspace_id}', not '{actual_ws_id}'")

        # Reject client-provided forged workspace_id in payload
        client_ws = payload.get("workspace_id") if payload else None
        if client_ws and client_ws != actual_ws_id:
            raise TenantSecurityError(f"Client-provided workspace_id '{client_ws}' conflicts with verified tenant workspace '{actual_ws_id}'")

        # 1. Idempotency Check
        if idempotency_key:
            existing = repo.find_by_idempotency(project_id, idempotency_key, workspace_id=actual_ws_id)
            if existing:
                if existing.request_payload_hash and existing.request_payload_hash != payload_hash:
                    raise IdempotencyConflictError(
                        idempotency_key=idempotency_key,
                        message=f"Idempotency conflict: Key '{idempotency_key}' was previously used with a different request payload."
                    )
                return existing, False

        # 2. Authoritative Server Provenance Resolution
        auth_lifecycle_rev = state.revision if state else 1
        auth_review_bundle_id = None
        if state:
            active_b = state.get_active_review_bundle()
            if active_b:
                auth_review_bundle_id = active_b.review_bundle_id

        auth_doc_rev = None
        auth_bp_sha = None
        auth_storage_key = None

        try:
            from scripts.core.database import get_database_engine
            db_engine = get_database_engine()
            conn = db_engine.get_connection()
            try:
                cur = conn.execute(
                    """
                    SELECT revision, content_hash, storage_key
                    FROM project_artifact_versions
                    WHERE workspace_id = ? AND project_id = ? AND artifact_kind = 'blueprint'
                    ORDER BY revision DESC LIMIT 1
                    """,
                    (actual_ws_id, project_id),
                )
                row_art = cur.fetchone()
                if row_art:
                    auth_doc_rev = row_art[0]
                    auth_bp_sha = row_art[1]
                    auth_storage_key = row_art[2]
            finally:
                conn.close()
        except Exception:
            pass

        if auth_bp_sha is None:
            bp_file = proj_dir / "05_blueprint.json"
            if bp_file.exists():
                import hashlib
                auth_bp_sha = hashlib.sha256(bp_file.read_bytes()).hexdigest()

        # 3. Reject Malicious / Conflicting Client-Provided Provenance Values
        if payload:
            c_doc_rev = payload.get("canonical_document_revision")
            if c_doc_rev is not None and auth_doc_rev is not None and c_doc_rev != auth_doc_rev:
                raise ProvenanceConflictError("canonical_document_revision", expected=auth_doc_rev, actual=c_doc_rev)

            c_bp_sha = payload.get("canonical_blueprint_sha256")
            if c_bp_sha is not None and auth_bp_sha is not None and c_bp_sha != auth_bp_sha:
                raise ProvenanceConflictError("canonical_blueprint_sha256", expected=auth_bp_sha, actual=c_bp_sha)

            c_key = payload.get("immutable_storage_key")
            if c_key is not None and auth_storage_key is not None and c_key != auth_storage_key:
                raise ProvenanceConflictError("immutable_storage_key", expected=auth_storage_key, actual=c_key)

            c_bundle = payload.get("approved_review_bundle_id")
            if c_bundle is not None and auth_review_bundle_id is not None and c_bundle != auth_review_bundle_id:
                raise ProvenanceConflictError("approved_review_bundle_id", expected=auth_review_bundle_id, actual=c_bundle)

            c_life = payload.get("lifecycle_state_revision")
            if c_life is not None and auth_lifecycle_rev is not None and c_life != auth_lifecycle_rev:
                raise ProvenanceConflictError("lifecycle_state_revision", expected=auth_lifecycle_rev, actual=c_life)

        # 4. Create durable Run record with Authoritative Provenance
        run_id = f"run_{uuid.uuid4().hex}"
        record = RunRecord(
            run_id=run_id,
            workspace_id=actual_ws_id,
            project_id=project_id,
            status=RunStatus.QUEUED,
            input_revision=input_revision,
            canonical_document_revision=auth_doc_rev,
            canonical_blueprint_sha256=auth_bp_sha,
            immutable_storage_key=auth_storage_key,
            approved_review_bundle_id=auth_review_bundle_id,
            lifecycle_state_revision=auth_lifecycle_rev,
            idempotency_key=idempotency_key,
            request_payload_hash=payload_hash,
        )

        persisted = repo.create_run(record)
        is_created = (persisted.run_id == record.run_id)

        # 4. Emit durable RUN_QUEUED event only if newly created
        if is_created:
            repo.record_event(
                run_id=persisted.run_id,
                project_id=project_id,
                event_type="RUN_QUEUED",
                payload={
                    "attempt": persisted.attempt,
                    "input_revision": persisted.input_revision,
                    "canonical_document_revision": persisted.canonical_document_revision,
                    "canonical_blueprint_sha256": persisted.canonical_blueprint_sha256,
                    "immutable_storage_key": persisted.immutable_storage_key,
                    "approved_review_bundle_id": persisted.approved_review_bundle_id,
                    "lifecycle_state_revision": persisted.lifecycle_state_revision,
                },
                workspace_id=actual_ws_id,
            )

        return persisted, is_created

    @classmethod
    def cancel_run(
        cls,
        project_id: str,
        run_id: str,
        db_path: Optional[Path | str] = None,
        workspace_id: Optional[str] = None,
    ) -> RunRecord:
        """Requests cancellation of a run in QUEUED or RUNNING state."""
        validate_project_id(project_id)
        repo = RunRepository(db_path=db_path)
        existing = repo.get_run(run_id)
        if not existing or existing.project_id != project_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)
        if workspace_id and existing.workspace_id != workspace_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)

        try:
            record, _ = repo.request_cancel_run(run_id=run_id, project_id=project_id, workspace_id=workspace_id)
            return record
        except InvalidRunTransitionError as e:
            raise RunNotCancellableError(run_id=run_id, status=existing.status.value, message=str(e))

    @classmethod
    def get_events(
        cls,
        project_id: str,
        run_id: str,
        after_sequence: int = 0,
        limit: int = 500,
        db_path: Optional[Path | str] = None,
        workspace_id: Optional[str] = None,
    ) -> List[RunEvent]:
        """Retrieves persistent events for a specific run."""
        validate_project_id(project_id)
        repo = RunRepository(db_path=db_path)
        existing = repo.get_run(run_id)
        if not existing or existing.project_id != project_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)
        if workspace_id and existing.workspace_id != workspace_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)

        return repo.get_events(run_id=run_id, project_id=project_id, after_sequence=after_sequence, limit=limit, workspace_id=workspace_id)

    @classmethod
    def get_run(
        cls,
        project_id: str,
        run_id: str,
        db_path: Optional[Path | str] = None,
        workspace_id: Optional[str] = None,
    ) -> RunRecord:
        """Retrieves an existing RunRecord, scoped to project_id."""
        validate_project_id(project_id)
        repo = RunRepository(db_path=db_path)
        record = repo.get_run(run_id)
        if not record or record.project_id != project_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)
        if workspace_id and record.workspace_id != workspace_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)
        return record

    @classmethod
    def list_runs(
        cls,
        project_id: str,
        limit: int = 50,
        db_path: Optional[Path | str] = None,
        workspace_id: Optional[str] = None,
    ) -> List[RunRecord]:
        """Lists runs for a specific project."""
        validate_project_id(project_id)
        proj_dir = cls._get_project_dir(project_id)
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        repo = RunRepository(db_path=db_path)
        return repo.list_runs(project_id=project_id, limit=limit, workspace_id=workspace_id)
