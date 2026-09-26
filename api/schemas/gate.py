from pydantic import BaseModel
from typing import Any, Dict

class GateResponse(BaseModel):
    status: str
    output: Any

class StageStatusResponse(BaseModel):
    state: Dict[str, Any]
