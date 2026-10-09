"""
API Schemas for Pipeline Runs (S21).
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from scripts.core.run_model import RunStatus, RunRecord


class RunCreateRequest(BaseModel):
    """Client request schema for triggering a pipeline run."""
    model_config = {"extra": "allow"}
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
    canonical_document_revision: Optional[int] = None
    canonical_blueprint_sha256: Optional[str] = None
    immutable_storage_key: Optional[str] = None
    approved_review_bundle_id: Optional[str] = None
    lifecycle_state_revision: Optional[int] = None
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
            canonical_document_revision=record.canonical_document_revision,
            canonical_blueprint_sha256=record.canonical_blueprint_sha256,
            immutable_storage_key=record.immutable_storage_key,
            approved_review_bundle_id=record.approved_review_bundle_id,
            lifecycle_state_revision=record.lifecycle_state_revision,
            idempotency_key=record.idempotency_key,
            failure_code=record.failure_code,
            failure_detail=record.failure_detail,
            result_reference=record.result_reference,
        )


class RunListResponse(BaseModel):
    runs: List[RunResponse]
    total: int


class RunEventResponse(BaseModel):
    """Canonical DTO representation of a persistent Run Event (S22 - LED-060)."""
    event_id: str
    run_id: str
    project_id: str
    sequence: int
    event_type: str
    stage: Optional[str] = None
    timestamp: str
    payload: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_record(cls, event: Any) -> "RunEventResponse":
        return cls(
            event_id=event.event_id,
            run_id=event.run_id,
            project_id=event.project_id,
            sequence=event.sequence,
            event_type=event.event_type,
            stage=event.stage,
            timestamp=event.timestamp,
            payload=event.payload,
        )


class RunEventListResponse(BaseModel):
    events: List[RunEventResponse]
    total: int
    latest_sequence: int
