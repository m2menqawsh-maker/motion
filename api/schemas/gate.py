from pydantic import BaseModel
from typing import Any, Dict
from scripts.state_model import ProjectState

class GateResponse(BaseModel):
    status: str
    output: Any

class StageStatusResponse(BaseModel):
    state: ProjectState
