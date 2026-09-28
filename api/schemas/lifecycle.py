"""
Canonical Lifecycle DTO Schema (S22 - LED-071).

Provides the unified, non-degraded projection of project lifecycle state for GUI clients:
- Single source of truth derived from LifecycleService, ReviewService, RunRepository, and ArtifactService
- Eliminates legacy facade collapse (where multiple states were squashed to 'qc_gate')
- Exposes allowed actions, blocking reasons, active review bundle, latest execution run, and artifact integrity
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LifecycleDTO(BaseModel):
    """Canonical lifecycle projection for a project."""
    project_id: str
    lifecycle_state: str
    revision: int
    allowed_actions: List[str] = Field(default_factory=list)
    blocked_reason: Optional[str] = None
    review: Optional[Dict[str, Any]] = None
    latest_run: Optional[Dict[str, Any]] = None
    artifacts_status: Dict[str, str] = Field(default_factory=dict)
