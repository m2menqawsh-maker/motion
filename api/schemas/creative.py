"""
api/schemas/creative.py — Schemas for AI Creative Proposals and Application.
S28 / PR-003: Governs typed creative request, advisory proposal response, and explicit apply.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreativeProposalRequest(BaseModel):
    """Client request for generating an advisory AI creative proposal."""
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="Natural-language creative request or video concept",
    )
    aspect_ratio: Optional[str] = Field(
        default="9:16",
        pattern=r"^(9:16|16:9|1:1)$",
        description="Target video aspect ratio",
    )
    target_duration: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=600.0,
        description="Optional target duration in seconds",
    )
    audio_mode: Optional[str] = Field(
        default=None,
        pattern=r"^(VO_MUSIC|MUSIC_ONLY|VO_ONLY|SILENT|SOURCE_AUDIO|SOURCE_AUDIO_MUSIC)$",
        description="Optional audio treatment mode",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Client-supplied idempotency key",
    )


class CreativeProposalResponse(BaseModel):
    """Advisory creative proposal produced by verified AI domain components."""
    proposal_id: str = Field(description="Unique stable proposal identifier")
    status: str = Field(default="PROPOSED", description="Advisory lifecycle status (PROPOSED)")
    project_id: str = Field(description="Authoritative project ID")
    workspace_id: str = Field(description="Verified tenant workspace ID")
    base_revision: int = Field(description="Current persistent base revision of the project")
    prompt: str = Field(description="Original bounded user prompt")
    brief: Dict[str, Any] = Field(description="Parsed epistemic CreativeBrief")
    recipe_id: str = Field(description="Selected registered recipe ID")
    narrative_hook: str = Field(description="Core hook / key takeaway from NarrativePlan")
    creative_plan: Dict[str, Any] = Field(description="Canonical CreativePlan (scenes and intents)")
    candidate_blueprint: Dict[str, Any] = Field(description="Compiled canonical BlueprintV2 dictionary")
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list, description="Diagnostic messages or warnings")
    approval_required: bool = Field(default=True, description="Strict requirement for explicit human approval")
    can_apply: bool = Field(default=True, description="Whether the proposal can be explicitly applied")


class ApplyCreativeProposalRequest(BaseModel):
    """Request to commit an advisory proposal to the authoritative canonical document."""
    proposal_id: Optional[str] = Field(default=None, description="Proposal identifier if applying generated proposal")
    blueprint: Dict[str, Any] = Field(..., description="Candidate BlueprintV2 document to commit")
    base_revision: Optional[int] = Field(default=None, description="Expected base revision for CAS check")
    operation_id: Optional[str] = Field(default=None, description="Durable idempotency operation key")
