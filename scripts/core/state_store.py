import os
import json
import hashlib
from pathlib import Path
from typing import Optional

from scripts.core.state_model import ProjectState, ArtifactRecord, ValidationLevel

class StateStore:
    STATE_FILE = ".pipeline_state.json"
    
    @staticmethod
    def _compute_sha256(path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def create_artifact_record(project_dir: Path, rel_path: str, validation: ValidationLevel) -> ArtifactRecord:
        """
        Creates an ArtifactRecord for the given file relative to project_dir.
        Calculates size and sha256 according to validation level.
        """
        full_path = project_dir / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Cannot create artifact record, file missing: {rel_path}")
            
        record = ArtifactRecord(path=rel_path, validation=validation)
        
        if validation in (ValidationLevel.SIZE, ValidationLevel.SHA256):
            record.size_bytes = full_path.stat().st_size
            
        if validation == ValidationLevel.SHA256:
            record.sha256 = StateStore._compute_sha256(full_path)
            
        return record

    @staticmethod
    def save(project_dir: Path, state: ProjectState) -> None:
        """
        Atomically saves the state record to the project directory.
        """
        state_file = project_dir / StateStore.STATE_FILE
        tmp_file = project_dir / f"{StateStore.STATE_FILE}.tmp"
        
        with open(tmp_file, "w", encoding="utf-8") as f:
            # We dump the model, explicitly converting enums to values.
            # Using model_dump (Pydantic v2) or dict (Pydantic v1)
            if hasattr(state, "model_dump"):
                data = state.model_dump(mode='json')
            else:
                data = state.dict()
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        os.replace(tmp_file, state_file)
        
    @staticmethod
    def load(project_dir: Path) -> Optional[ProjectState]:
        """
        Loads the state record from the project directory if it exists.
        """
        state_file = project_dir / StateStore.STATE_FILE
        if not state_file.exists():
            return None
            
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProjectState(**data)
        except Exception:
            return None
