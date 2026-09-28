"""
Runs API Router for S21.

Canonical entrypoint for triggering and querying durable pipeline execution runs.
Endpoints:
- POST /projects/{project_id}/runs -> Enqueues a durable Run record (202 Accepted).
- GET  /projects/{project_id}/runs/{run_id} -> Queries status of a specific Run.
- GET  /projects/{project_id}/runs -> Lists runs for a project.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Response, status
from api.core.auth import require_permission, Principal, Action
from api.schemas.run import RunCreateRequest, RunResponse, RunListResponse
from api.services.run_service import RunService

router = APIRouter()


@router.post(
    "/{project_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a durable pipeline run",
)
async def create_run(
    project_id: str,
    response: Response,
    req: Optional[RunCreateRequest] = None,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    principal: Principal = Depends(require_permission(Action.RUN_EXECUTE)),
):
    """
    Enqueues a durable pipeline run record before returning HTTP 202 Accepted.
    Supports idempotency keys via 'Idempotency-Key' header or request body.
    """
    effective_idempotency_key = idempotency_key_header or (req.idempotency_key if req else None)
    payload_dict = req.model_dump() if req else {}

    record, is_created = RunService.create_run(
        project_id=project_id,
        idempotency_key=effective_idempotency_key,
        payload=payload_dict,
    )

    # 202 Accepted for new or existing asynchronous queued runs
    response.status_code = status.HTTP_202_ACCEPTED
    return RunResponse.from_record(record)


@router.get(
    "/{project_id}/runs/{run_id}",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get status of a specific pipeline run",
)
async def get_run(
    project_id: str,
    run_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    """Retrieves current state and metadata for a specific run."""
    record = RunService.get_run(project_id=project_id, run_id=run_id)
    return RunResponse.from_record(record)


@router.get(
    "/{project_id}/runs",
    response_model=RunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List runs for a project",
)
async def list_runs(
    project_id: str,
    limit: int = 50,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    """Lists recent runs for the specified project."""
    records = RunService.list_runs(project_id=project_id, limit=limit)
    dto_list = [RunResponse.from_record(r) for r in records]
    return RunListResponse(runs=dto_list, total=len(dto_list))
