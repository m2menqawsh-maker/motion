from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

class CheckpointStage(str, Enum):
    INITIALIZED = "INITIALIZED"
    ASSETS_READY = "ASSETS_READY"
    PLAN_READY = "PLAN_READY"
    BLUEPRINT_READY = "BLUEPRINT_READY"
    RENDERED = "RENDERED"
    QC_PASSED = "QC_PASSED"
    COMPLETE = "COMPLETE"

class ValidationLevel(str, Enum):
    EXISTS = "EXISTS"       # Level 1 — Exists only (temporary/derived files)
    SIZE = "SIZE"           # Level 2 — Exists + size (large files like out.mp4)
    SHA256 = "SHA256"       # Level 3 — SHA256 (logic files like master_plan.md)

@dataclass
class ArtifactRecord:
    path: str
    validation: ValidationLevel
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "path": self.path,
            "validation": self.validation.value,
        }
        if self.size_bytes is not None:
            d["size_bytes"] = self.size_bytes
        if self.sha256 is not None:
            d["sha256"] = self.sha256
        return d
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactRecord":
        return cls(
            path=data["path"],
            validation=ValidationLevel(data["validation"]),
            size_bytes=data.get("size_bytes"),
            sha256=data.get("sha256")
        )

@dataclass
class CheckpointRecord:
    project_id: str
    run_id: str
    checkpoint: CheckpointStage
    timestamp: float
    checkpoint_schema_version: str = "1.0"
    pipeline_version: str = "1.0"
    artifact_references: List[ArtifactRecord] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "checkpoint": self.checkpoint.value,
            "timestamp": self.timestamp,
            "checkpoint_schema_version": self.checkpoint_schema_version,
            "pipeline_version": self.pipeline_version,
            "artifact_references": [a.to_dict() for a in self.artifact_references]
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointRecord":
        return cls(
            project_id=data["project_id"],
            run_id=data["run_id"],
            checkpoint=CheckpointStage(data["checkpoint"]),
            timestamp=data["timestamp"],
            checkpoint_schema_version=data.get("checkpoint_schema_version", "1.0"),
            pipeline_version=data.get("pipeline_version", "1.0"),
            artifact_references=[ArtifactRecord.from_dict(a) for a in data.get("artifact_references", [])]
        )
