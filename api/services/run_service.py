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

from api.core.errors import ProjectNotFoundError, RunNotFoundError, IdempotencyConflictError, RunNotCancellableError
from scripts.core.run_model import RunRecord, RunStatus, RunEvent, InvalidRunTransitionError
from scripts.core.run_repository import RunRepository
from scripts.core.state_store import StateStore
from scripts.security.path_security import validate_project_id


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

        # 1. Idempotency Check
        if idempotency_key:
            existing = repo.find_by_idempotency(project_id, idempotency_key)
            if existing:
                if existing.request_payload_hash and existing.request_payload_hash != payload_hash:
                    raise IdempotencyConflictError(
                        idempotency_key=idempotency_key,
                        message=f"Idempotency conflict: Key '{idempotency_key}' was previously used with a different request payload."
                    )
                return existing, False

        # 2. Capture baseline project state revision
        state = StateStore.load(proj_dir)
        input_revision = state.revision if state else 1

        # Determine workspace_id
        actual_ws_id = workspace_id
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

        # 3. Create durable Run record
        run_id = f"run_{uuid.uuid4().hex}"
        record = RunRecord(
            run_id=run_id,
            workspace_id=actual_ws_id,
            project_id=project_id,
            status=RunStatus.QUEUED,
            input_revision=input_revision,
            idempotency_key=idempotency_key,
            request_payload_hash=payload_hash,
        )

        persisted = repo.create_run(record)

        # 4. Emit durable RUN_QUEUED event
        repo.record_event(
            run_id=persisted.run_id,
            project_id=project_id,
            event_type="RUN_QUEUED",
            payload={"attempt": persisted.attempt, "input_revision": persisted.input_revision},
            workspace_id=actual_ws_id,
        )

        return persisted, True

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
