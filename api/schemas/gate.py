from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict

class GateName(str, Enum):
    ASSET_GATE = "asset_gate"
    PLAN_GATE = "plan_gate"
    TASTE_GATE = "taste_gate"
    QC_GATE = "qc_gate"

class StageName(str, Enum):
    ASSET_GATE = "asset_gate"
    PLAN_GATE = "plan_gate"
    TASTE_GATE = "taste_gate"
    QC_GATE = "qc_gate"

class GateResponse(BaseModel):
    status: str
    output: Any

class StageStatusResponse(BaseModel):
    state: Dict[str, Any]
