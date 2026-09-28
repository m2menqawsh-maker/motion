import json
from pathlib import Path
from fastapi import APIRouter, Body, Depends
from jsonschema import validate, ValidationError
from scripts.security.path_security import validate_project_id
from api.schemas import BlueprintResponse, StandardResponse
from api.core.errors import ProjectNotFoundError, APIError
from api.core.auth import require_permission, Principal, Action

router = APIRouter()

SCHEMA_PATH = Path("schemas/blueprint.schema.json")
BLUEPRINT_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) if SCHEMA_PATH.exists() else None


@router.get("/{project_id}", response_model=BlueprintResponse)
async def get_blueprint(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.BLUEPRINT_READ))
):
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        from api.services.pipeline_service import PipelineService
        project_dir = PipelineService._get_project_dir(project_id)
    blueprint_path = project_dir / "05_blueprint.json"
    overrides_path = project_dir / "overrides.json"

    data = {}
    if blueprint_path.exists():
        try:
            from scripts.core.blueprint_loader import load_blueprint
            bp_v2 = load_blueprint(blueprint_path, expected_project_id=project_id, allow_migrate=True)
            data["blueprint"] = bp_v2.to_dict()
        except Exception:
            data["blueprint"] = json.loads(blueprint_path.read_text(encoding="utf-8"))
    if overrides_path.exists():
        data["overrides"] = json.loads(overrides_path.read_text(encoding="utf-8"))

    if not data:
        raise APIError(message="Blueprint/Overrides not found", status_code=404)
    return BlueprintResponse(**data)


@router.post("/{project_id}/blueprint", response_model=StandardResponse)
async def update_blueprint(
    project_id: str,
    payload: dict = Body(...),
    principal: Principal = Depends(require_permission(Action.BLUEPRINT_EDIT))
):
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        from api.services.pipeline_service import PipelineService
        project_dir = PipelineService._get_project_dir(project_id)
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    from scripts.core.blueprint_validator import validate_blueprint_v2
    from scripts.core.manifest_loader import load_manifest

    man = None
    manifest_path = project_dir / "02_asset_manifest.json"
    if manifest_path.exists():
        try:
            man = load_manifest(manifest_path, expected_project_id=project_id, allow_migrate=True)
        except Exception:
            pass

    v_res = validate_blueprint_v2(payload, expected_project_id=project_id, manifest=man)
    if not v_res.ok:
        raise APIError(message=f"Invalid blueprint: {'; '.join(v_res.errors)}", status_code=400)

    from api.services.pipeline_service import PipelineService
    actor = getattr(principal, "principal_id", "api_user")
    PipelineService.mutate_blueprint(project_id, payload, actor_id=actor)

    return StandardResponse(status="success")


@router.post("/{project_id}/overrides", response_model=StandardResponse)
async def update_overrides(
    project_id: str,
    payload: dict = Body(...),
    principal: Principal = Depends(require_permission(Action.BLUEPRINT_EDIT))
):
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        from api.services.pipeline_service import PipelineService
        project_dir = PipelineService._get_project_dir(project_id)
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)

    filepath = project_dir / "overrides.json"
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return StandardResponse(status="success")
