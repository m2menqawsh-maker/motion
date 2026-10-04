"""
ai/tools/domain/projects.py
===========================
Domain tool adapter for project queries and lifecycle status (S27.9).

Invariants:
- Zero raw filesystem or direct DB access.
- Delegates completely to canonical ProjectService.
- Read-only projection without state mutation.
"""

from __future__ import annotations

from api.services.project_service import ProjectService
from ai.tools.contracts import GetProjectStatusInput, GetProjectStatusOutput
from ai.tools.types import TrustedToolExecutionContext


def get_project_status_adapter(
    input_data: GetProjectStatusInput,
    context: TrustedToolExecutionContext,
) -> GetProjectStatusOutput:
    """
    Retrieves canonical lifecycle DTO for a project via ProjectService.
    """
    lifecycle_dto = ProjectService.get_lifecycle_dto(input_data.project_id)

    review_status_val = None
    if lifecycle_dto.review and isinstance(lifecycle_dto.review, dict):
        review_status_val = lifecycle_dto.review.get("review_state")

    latest_run_id_val = None
    if lifecycle_dto.latest_run and isinstance(lifecycle_dto.latest_run, dict):
        latest_run_id_val = lifecycle_dto.latest_run.get("run_id")

    return GetProjectStatusOutput(
        project_id=input_data.project_id,
        lifecycle_state=lifecycle_dto.lifecycle_state,
        revision=lifecycle_dto.revision,
        allowed_actions=list(lifecycle_dto.allowed_actions),
        blocked_reason=lifecycle_dto.blocked_reason,
        review_status=review_status_val,
        latest_run_id=latest_run_id_val,
    )
