from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class GateStatus(str, Enum):
    LOCKED = "locked"
    AWAITING = "awaiting"
    APPROVED = "approved"
    REJECTED = "rejected"

class StageEntry(BaseModel):
    status: StageStatus = StageStatus.PENDING
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

class GateEntry(BaseModel):
    status: GateStatus = GateStatus.LOCKED
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    note: Optional[str] = None

class ValidationLevel(str, Enum):
    EXISTS = "EXISTS"       # Level 1 — Exists only (temporary/derived files)
    SIZE = "SIZE"           # Level 2 — Exists + size (large files like out.mp4)
    SHA256 = "SHA256"       # Level 3 — SHA256 (logic files like master_plan.md)

class ArtifactRecord(BaseModel):
    path: str
    validation: ValidationLevel
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None

class CheckpointStage(str, Enum):
    INITIALIZED = "INITIALIZED"
    ASSETS_READY = "ASSETS_READY"
    PLAN_READY = "PLAN_READY"
    BLUEPRINT_READY = "BLUEPRINT_READY"
    PROBE_READY = "PROBE_READY"
    APPROVED = "APPROVED"
    RENDERED = "RENDERED"
    QC_PASSED = "QC_PASSED"
    COMPLETE = "COMPLETE"

class ProjectState(BaseModel):
    project_id: str
    current_stage: int = 0
    last_error: Optional[str] = None
    stages: Dict[str, StageEntry] = Field(default_factory=lambda: {
        "0": StageEntry(),
        "1": StageEntry(),
        "2": StageEntry(),
        "3": StageEntry(),
    })
    gates: Dict[str, GateEntry] = Field(default_factory=lambda: {
        "gate_1": GateEntry(),
        "gate_2": GateEntry(),
        "gate_3": GateEntry(),
    })
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Merged from CheckpointRecord
    run_id: Optional[str] = None
    checkpoint: CheckpointStage = CheckpointStage.INITIALIZED
    artifact_references: List[ArtifactRecord] = Field(default_factory=list)

    class Config:
        use_enum_values = True
        extra = "allow" # To handle old fields or custom fields safely
