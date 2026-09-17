from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from scripts.state_model import ProjectState

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., description="Project name")
    aspect: str = Field(..., description="Aspect ratio (e.g., 16:9, 9:16, 1:1)")
    fps: int = Field(30, description="Frames per second")
    language: str = Field("ar", description="Project language")

class ProjectCreateResponse(BaseModel):
    project_id: str

class ProjectListResponse(BaseModel):
    projects: List[str]

class ProjectResponse(BaseModel):
    project: Optional[Dict[str, Any]] = None
    manifest: Optional[Dict[str, Any]] = None
    state: ProjectState
