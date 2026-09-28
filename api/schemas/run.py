"""
API Schemas for Pipeline Runs (S21).
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from scripts.core.run_model import RunStatus, RunRecord


class RunCreateRequest(BaseModel):
    """Client request schema for triggering a pipeline run."""
    idempotency_key: Optional[str] = Field(default=None, description="Optional client idempotency key")


class RunResponse(BaseModel):
    """Canonical DTO representation of a pipeline run."""
    run_id: str
    project_id: str
    status: RunStatus
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    attempt: int = 1
    worker_id: Optional[str] = None
    lease_expires_at: Optional[str] = None
    input_revision: Optional[int] = None
    idempotency_key: Optional[str] = None
    failure_code: Optional[str] = None
    failure_detail: Optional[Dict[str, Any]] = None
    result_reference: Optional[Dict[str, Any]] = None

    @classmethod
    def from_record(cls, record: RunRecord) -> "RunResponse":
        return cls(
            run_id=record.run_id,
            project_id=record.project_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
            attempt=record.attempt,
            worker_id=record.worker_id,
            lease_expires_at=record.lease_expires_at,
            input_revision=record.input_revision,
            idempotency_key=record.idempotency_key,
            failure_code=record.failure_code,
            failure_detail=record.failure_detail,
            result_reference=record.result_reference,
        )


class RunListResponse(BaseModel):
    runs: List[RunResponse]
    total: int
