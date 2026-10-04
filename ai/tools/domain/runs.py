"""
ai/tools/domain/runs.py
=======================
Domain tool adapter for pipeline run execution and cancellation (S27.9).

Invariants:
- AI has NO direct execution lock or lifecycle authority.
- Delegates strictly to RunService and RunRepository.
- Enforces workspace ownership and idempotency semantics.
"""

from __future__ import annotations

from api.services.run_service import RunService
from ai.tools.contracts import (
    CancelRunInput,
    CancelRunOutput,
    StartRunInput,
    StartRunOutput,
)
from ai.tools.types import TrustedToolExecutionContext


def start_run_adapter(
    input_data: StartRunInput,
    context: TrustedToolExecutionContext,
) -> StartRunOutput:
    """
    Submits a new pipeline execution run via RunService.
    """
    # Pre-execution timeout checkpoint
    context.assert_not_timed_out()

    record, is_created = RunService.create_run(
        project_id=input_data.project_id,
        idempotency_key=input_data.idempotency_key,
        workspace_id=context.workspace_id,
    )

    return StartRunOutput(
        project_id=input_data.project_id,
        run_id=record.run_id,
        status=record.status.value if hasattr(record.status, "value") else str(record.status),
        is_created=is_created,
        input_revision=record.input_revision,
    )


def cancel_run_adapter(
    input_data: CancelRunInput,
    context: TrustedToolExecutionContext,
) -> CancelRunOutput:
    """
    Requests cancellation of an active pipeline run via RunService.
    """
    # Pre-execution timeout checkpoint
    context.assert_not_timed_out()

    record = RunService.cancel_run(
        project_id=input_data.project_id,
        run_id=input_data.run_id,
        workspace_id=context.workspace_id,
    )

    return CancelRunOutput(
        project_id=input_data.project_id,
        run_id=record.run_id,
        status=record.status.value if hasattr(record.status, "value") else str(record.status),
    )
