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

from api.core.errors import ProjectNotFoundError, RunNotFoundError, IdempotencyConflictError
from scripts.core.run_model import RunRecord, RunStatus
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

        # 3. Create durable Run record
        run_id = f"run_{uuid.uuid4().hex}"
        record = RunRecord(
            run_id=run_id,
            project_id=project_id,
            status=RunStatus.QUEUED,
            input_revision=input_revision,
            idempotency_key=idempotency_key,
            request_payload_hash=payload_hash,
        )

        persisted = repo.create_run(record)
        return persisted, True

    @classmethod
    def get_run(
        cls,
        project_id: str,
        run_id: str,
        db_path: Optional[Path | str] = None,
    ) -> RunRecord:
        """Retrieves an existing RunRecord, scoped to project_id."""
        validate_project_id(project_id)
        repo = RunRepository(db_path=db_path)
        record = repo.get_run(run_id)
        if not record or record.project_id != project_id:
            raise RunNotFoundError(run_id=run_id, project_id=project_id)
        return record

    @classmethod
    def list_runs(
        cls,
        project_id: str,
        limit: int = 50,
        db_path: Optional[Path | str] = None,
    ) -> List[RunRecord]:
        """Lists runs for a specific project."""
        validate_project_id(project_id)
        proj_dir = cls._get_project_dir(project_id)
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        repo = RunRepository(db_path=db_path)
        return repo.list_runs(project_id=project_id, limit=limit)
