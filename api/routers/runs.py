"""
Runs API Router for S21.

Canonical entrypoint for triggering and querying durable pipeline execution runs.
Endpoints:
- POST /projects/{project_id}/runs -> Enqueues a durable Run record (202 Accepted).
- GET  /projects/{project_id}/runs/{run_id} -> Queries status of a specific Run.
- GET  /projects/{project_id}/runs -> Lists runs for a project.
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, Header, Response, Request, status
from fastapi.responses import StreamingResponse
from api.core.auth import require_permission, Principal, Action
from api.schemas.run import RunCreateRequest, RunResponse, RunListResponse, RunEventResponse, RunEventListResponse
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
    request: Request,
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
    tenant_ctx = getattr(request.state, "tenant_context", None)
    ws_id = tenant_ctx.workspace_id if tenant_ctx else None

    record, is_created = RunService.create_run(
        project_id=project_id,
        idempotency_key=effective_idempotency_key,
        payload=payload_dict,
        workspace_id=ws_id,
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
    request: Request,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    """Retrieves current state and metadata for a specific run."""
    tenant_ctx = getattr(request.state, "tenant_context", None)
    ws_id = tenant_ctx.workspace_id if tenant_ctx else None
    record = RunService.get_run(project_id=project_id, run_id=run_id, workspace_id=ws_id)
    return RunResponse.from_record(record)


@router.get(
    "/{project_id}/runs",
    response_model=RunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List runs for a project",
)
async def list_runs(
    project_id: str,
    request: Request,
    limit: int = 50,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    """Lists recent runs for the specified project."""
    tenant_ctx = getattr(request.state, "tenant_context", None)
    ws_id = tenant_ctx.workspace_id if tenant_ctx else None
    records = RunService.list_runs(project_id=project_id, limit=limit, workspace_id=ws_id)
    dto_list = [RunResponse.from_record(r) for r in records]
    return RunListResponse(runs=dto_list, total=len(dto_list))


@router.post(
    "/{project_id}/runs/{run_id}/cancel",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a pipeline run",
)
async def cancel_run(
    project_id: str,
    run_id: str,
    request: Request,
    principal: Principal = Depends(require_permission(Action.RUN_CANCEL)),
):
    """
    Cancels a QUEUED or RUNNING pipeline execution run.
    Idempotent for already cancelled runs.
    Rejects terminal runs (SUCCEEDED, FAILED) with HTTP 409 Conflict.
    """
    tenant_ctx = getattr(request.state, "tenant_context", None)
    ws_id = tenant_ctx.workspace_id if tenant_ctx else None
    record = RunService.cancel_run(project_id=project_id, run_id=run_id, workspace_id=ws_id)
    return RunResponse.from_record(record)


@router.get(
    "/{project_id}/runs/{run_id}/events",
    summary="Query or stream persistent events for a run",
)
async def get_run_events(
    project_id: str,
    run_id: str,
    request: Request,
    after: int = 0,
    limit: int = 500,
    stream: bool = False,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    accept: Optional[str] = Header(None),
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    """
    Retrieves durable run events.
    Supports reconnection and cursor pagination via 'after' query parameter or 'Last-Event-ID' header.
    When stream=true or Accept: text/event-stream, streams events via Server-Sent Events (SSE).
    """
    tenant_ctx = getattr(request.state, "tenant_context", None)
    ws_id = tenant_ctx.workspace_id if tenant_ctx else None

    effective_after = after
    if last_event_id and last_event_id.isdigit():
        effective_after = max(effective_after, int(last_event_id))

    is_sse = stream or (accept and "text/event-stream" in accept)

    if not is_sse:
        events = RunService.get_events(
            project_id=project_id, run_id=run_id, after_sequence=effective_after, limit=limit, workspace_id=ws_id
        )
        dto_list = [RunEventResponse.from_record(e) for e in events]
        latest_seq = max([e.sequence for e in dto_list], default=effective_after)
        return RunEventListResponse(events=dto_list, total=len(dto_list), latest_sequence=latest_seq)

    # SSE Streaming response
    async def sse_event_generator():
        current_seq = effective_after
        terminal_seen = False
        empty_polls = 0

        while True:
            events = RunService.get_events(
                project_id=project_id, run_id=run_id, after_sequence=current_seq, limit=100, workspace_id=ws_id
            )
            if events:
                empty_polls = 0
                for ev in events:
                    current_seq = max(current_seq, ev.sequence)
                    dto = RunEventResponse.from_record(ev)
                    ev_json = json.dumps(dto.model_dump())
                    yield f"id: {ev.sequence}\nevent: {ev.event_type}\ndata: {ev_json}\n\n"
                    if ev.event_type in ("RUN_SUCCEEDED", "RUN_FAILED", "RUN_CANCELLED"):
                        terminal_seen = True
            else:
                empty_polls += 1
                run_rec = RunService.get_run(project_id=project_id, run_id=run_id, workspace_id=ws_id)
                if run_rec.is_terminal and empty_polls >= 2:
                    break

            if terminal_seen:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
