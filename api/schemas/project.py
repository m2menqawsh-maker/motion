from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., description="Project name")
    language: str = Field("ar", description="Project language")

class ProjectCreateResponse(BaseModel):
    project_id: str

class ProjectListResponse(BaseModel):
    projects: List[str]

class ProjectResponse(BaseModel):
    project: Optional[Dict[str, Any]] = None
    manifest: Optional[Dict[str, Any]] = None
    state: Dict[str, Any]
