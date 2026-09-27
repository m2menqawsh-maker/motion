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

async def approve_gate(project_id: str, gate: str, by: str = "gui") -> dict:
    validate_project_id(project_id)
    return await PipelineService.approve_gate(project_id, str(gate), approved_by=by)

async def reject_gate(project_id: str, gate: str, by: str = None, note: str = "") -> dict:
    validate_project_id(project_id)
    if gate not in PipelineService.VALID_GATES:
        raise InvalidGateError(gate)

    project_dir = PipelineService._get_project_dir(project_id)
    state = StateStore.load(project_dir)
    if not state:
        raise ProjectNotFoundError(project_id)

    # Legacy fake rejection eliminated (S04 Finding C).
    # Durable review decisions require ReviewService (S09).
    raise UnsupportedGateOperationError(
        operation="reject_gate",
        reason="Gate rejection is not supported. Durable review decisions require ReviewService (S09)."
    )

