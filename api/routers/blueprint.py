from scripts.path_security import validate_project_id
from fastapi import APIRouter, Body
import json
from pathlib import Path
from jsonschema import validate, ValidationError
from api.schemas import BlueprintResponse, StandardResponse
from api.core.errors import ProjectNotFoundError, APIError

router = APIRouter()

# Load schema once
SCHEMA_PATH = Path("schemas/blueprint.schema.json")
BLUEPRINT_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) if SCHEMA_PATH.exists() else None

@router.get("/{project_id}", response_model=BlueprintResponse)
async def get_blueprint(project_id: str):
    project_id = validate_project_id(project_id)
    blueprint_path = Path(f"projects/{project_id}/05_blueprint.json")
    overrides_path = Path(f"projects/{project_id}/overrides.json")
    
    data = {}
    if blueprint_path.exists():
        data["blueprint"] = json.loads(blueprint_path.read_text(encoding="utf-8"))
    if overrides_path.exists():
        data["overrides"] = json.loads(overrides_path.read_text(encoding="utf-8"))
        
    if not data:
        raise APIError(message="Blueprint/Overrides not found", status_code=404)
    return BlueprintResponse(**data)

@router.post("/{project_id}/blueprint", response_model=StandardResponse)
async def update_blueprint(project_id: str, payload: dict = Body(...)):
    if BLUEPRINT_SCHEMA:
        try:
            validate(instance=payload, schema=BLUEPRINT_SCHEMA)
        except ValidationError as e:
            raise APIError(message=f"Invalid blueprint: {e.message}", status_code=400)
            
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)
        
    filepath = project_dir / "05_blueprint.json"
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return StandardResponse(status="success")

@router.post("/{project_id}/overrides", response_model=StandardResponse)
async def update_overrides(project_id: str, payload: dict = Body(...)):
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)
        
    filepath = project_dir / "overrides.json"
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return StandardResponse(status="success")
