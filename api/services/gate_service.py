from api.services.pipeline_service import PipelineService
from scripts.security.path_security import validate_project_id

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

async def reject_gate(project_id: str, gate: str, by: str, note: str) -> dict:
    validate_project_id(project_id)
    # Rejection just resets the stage status to "started" and drops approval
    legacy = await PipelineService.start_stage(project_id, str(gate))
    legacy["note"] = note
    return legacy
