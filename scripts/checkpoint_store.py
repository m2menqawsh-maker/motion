import os
import json
import hashlib
from pathlib import Path
from typing import Optional

from scripts.checkpoint_model import CheckpointRecord, ArtifactRecord, ValidationLevel

class CheckpointStore:
    CHECKPOINT_FILE = ".pipeline_checkpoint.json"
    
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
            record.sha256 = CheckpointStore._compute_sha256(full_path)
            
        return record

    @staticmethod
    def save(project_dir: Path, record: CheckpointRecord) -> None:
        """
        Atomically saves the checkpoint record to the project directory.
        """
        checkpoint_file = project_dir / CheckpointStore.CHECKPOINT_FILE
        tmp_file = project_dir / f"{CheckpointStore.CHECKPOINT_FILE}.tmp"
        
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno()) # Ensure it is written to disk
            
        os.replace(tmp_file, checkpoint_file)
        
    @staticmethod
    def load(project_dir: Path) -> Optional[CheckpointRecord]:
        """
        Loads the checkpoint record from the project directory if it exists.
        """
        checkpoint_file = project_dir / CheckpointStore.CHECKPOINT_FILE
        if not checkpoint_file.exists():
            return None
            
        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CheckpointRecord.from_dict(data)
        except Exception:
            return None
