"""
API Schemas for Project Artifacts & Reports (S22 - LED-064).
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class ArtifactItem(BaseModel):
    """Canonical descriptor for a project artifact."""
    kind: str
    filename: str
    status: str
    size_bytes: int = 0
    sha256: Optional[str] = None
    validation_level: str = "NONE"
    updated_at: Optional[str] = None


class ArtifactInventoryResponse(BaseModel):
    """Inventory of all governed project artifacts."""
    project_id: str
    artifacts: List[ArtifactItem]
    total: int


class ArtifactContentResponse(BaseModel):
    """Payload response when reading an artifact."""
    project_id: str
    kind: str
    filename: str
    content: Any
    revision: int
    sha256: Optional[str] = None
