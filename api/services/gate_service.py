from api.services.pipeline_service import PipelineService
from scripts.security.path_security import validate_project_id
from scripts.core.state_store import StateStore
from api.core.errors import InvalidGateError, ProjectNotFoundError, UnsupportedGateOperationError

async def get_status(project_id: str) -> dict:
    """Thin wrapper around PipelineService for backward compatibility"""
    validate_project_id(project_id)
    return await PipelineService.get_status(project_id)

async def start_stage(project_id: str, stage: str) -> dict:
    validate_project_id(project_id)
    return await PipelineService.start_stage(project_id, str(stage))

async def finish_stage(project_id: str, stage: str) -> dict:
    validate_project_id(project_id)
    return await PipelineService.finish_stage(project_id, str(stage))

async def approve_gate(project_id: str, gate: str, by: str = "gui", principal=None) -> dict:
    validate_project_id(project_id)
    return await PipelineService.approve_gate(project_id, str(gate), approved_by=by, principal=principal)

async def reject_gate(project_id: str, gate: str, by: str = None, note: str = "", principal=None) -> dict:
    validate_project_id(project_id)
    return await PipelineService.reject_gate(project_id, str(gate), by=by, note=note, principal=principal)


async def get_review_status(project_id: str) -> dict:
    validate_project_id(project_id)
    from scripts.core.review_service import ReviewService
    return ReviewService.get_review_status(project_id).model_dump()

