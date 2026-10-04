"""
ai/orchestration/activity_classification.py
===========================================
Authoritative idempotency classification matrix and validation policy (S27.11 / AI-10BR).

Invariants:
- Real-world external operation taxonomy: Providers, MCP Adapters, Domain Tools.
- Zero false claims: Operations without native idempotency or deterministic reconciliation
  MUST NEVER be classified as EFFECTIVELY_ONCE.
- Safe failure: Ambiguous crashes in non-idempotent activities (AT_MOST_ONCE) must fail terminally
  without automated blind retries to prevent duplicate side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from ai.contracts.activity import IdempotencySemantics
from ai.orchestration.errors import OrchestrationError


class ActivityBoundaryType(str, Enum):
    """Architectural classification of external activity boundaries."""
    PROVIDER = "PROVIDER"
    MCP = "MCP"
    TOOL = "TOOL"


class FalseIdempotencyClaimError(OrchestrationError):
    """Raised when an operation falsely claims EFFECTIVELY_ONCE without provable idempotency."""
    pass


@dataclass(frozen=True)
class ActivityClassification:
    """
    Authoritative specification of an activity's execution semantics and failure characteristics.
    """
    activity_name: str
    boundary_type: ActivityBoundaryType
    semantics: IdempotencySemantics
    native_idempotency_supported: bool
    stable_key_propagated: bool
    recovery_after_ambiguous_crash: str
    blind_retry_possible: bool
    residual_duplicate_risk: str
    description: str


# =============================================================================
# Authoritative Activity Classification Matrix
# =============================================================================

ACTIVITY_CLASSIFICATIONS: Dict[str, ActivityClassification] = {
    # -------------------------------------------------------------------------
    # 1. Provider Activities (ai/providers/)
    # -------------------------------------------------------------------------
    "provider:llm_text_generation": ActivityClassification(
        activity_name="provider:llm_text_generation",
        boundary_type=ActivityBoundaryType.PROVIDER,
        semantics=IdempotencySemantics.AT_LEAST_ONCE,
        native_idempotency_supported=False,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Retry with new attempt; prompt cache/re-generation is acceptable for text output.",
        blind_retry_possible=True,
        residual_duplicate_risk="Potential duplicate token generation cost if provider executed before crash.",
        description="Text generation via LLM APIs lacking native wire-level request deduplication.",
    ),
    "provider:embedding_generation": ActivityClassification(
        activity_name="provider:embedding_generation",
        boundary_type=ActivityBoundaryType.PROVIDER,
        semantics=IdempotencySemantics.AT_LEAST_ONCE,
        native_idempotency_supported=False,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Retry with new attempt; repeated execution reproduces deterministic vector output, but incurs duplicate external provider execution/cost if crash occurred post-dispatch.",
        blind_retry_possible=True,
        residual_duplicate_risk="duplicate provider execution/cost possible after ambiguous crash; output itself is deterministic",
        description="Embedding generation over text or multimodal inputs (deterministic vector projection).",
    ),
    "provider:paid_video_generation": ActivityClassification(
        activity_name="provider:paid_video_generation",
        boundary_type=ActivityBoundaryType.PROVIDER,
        semantics=IdempotencySemantics.AT_MOST_ONCE,
        native_idempotency_supported=False,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Fail terminally without automated retry to prevent duplicate financial debit ($5-$10/run). Requires manual reconciliation.",
        blind_retry_possible=False,
        residual_duplicate_risk="Zero duplicate execution permitted on ambiguous crash.",
        description="High-cost generative video models (Sora, Runway, Luma) without native request ID deduplication.",
    ),
    "provider:native_idempotent_generation": ActivityClassification(
        activity_name="provider:native_idempotent_generation",
        boundary_type=ActivityBoundaryType.PROVIDER,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=True,
        recovery_after_ambiguous_crash="Re-dispatch with identical logical idempotency key; provider returns cached execution without re-generation.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (provider-enforced deduplication).",
        description="Provider adapters supporting client-side idempotency keys (e.g. OpenAI client-request-id / gateway).",
    ),

    # -------------------------------------------------------------------------
    # 2. MCP Activities (ai/mcp/)
    # -------------------------------------------------------------------------
    "mcp:trim_audio": ActivityClassification(
        activity_name="mcp:trim_audio",
        boundary_type=ActivityBoundaryType.MCP,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=True,
        recovery_after_ambiguous_crash="Re-execute FFmpeg trim to content-addressed destination; atomic overwrite produces identical binary artifact.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (content-addressed idempotent file overwrite).",
        description="FFmpeg-based audio duration trimming to deterministic target path.",
    ),
    "mcp:normalize_loudness": ActivityClassification(
        activity_name="mcp:normalize_loudness",
        boundary_type=ActivityBoundaryType.MCP,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=True,
        recovery_after_ambiguous_crash="Re-execute EBU R128 normalization; atomic output overwrite yields identical audio waveform.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (deterministic media transform).",
        description="Loudness normalization (LUFS) for spoken dialogue and music tracks.",
    ),
    "mcp:trim_video": ActivityClassification(
        activity_name="mcp:trim_video",
        boundary_type=ActivityBoundaryType.MCP,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=True,
        recovery_after_ambiguous_crash="Re-execute stream-copy or transcode cut to deterministic artifact key; atomic replacement.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (deterministic media transform).",
        description="FFmpeg-based video trimming and frame-accurate cutting.",
    ),
    "mcp:dev_system_command": ActivityClassification(
        activity_name="mcp:dev_system_command",
        boundary_type=ActivityBoundaryType.MCP,
        semantics=IdempotencySemantics.AT_MOST_ONCE,
        native_idempotency_supported=False,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Fail terminally. Automated blind retry strictly forbidden because command may have non-idempotent external side effects.",
        blind_retry_possible=False,
        residual_duplicate_risk="Zero duplicate execution permitted; requires manual intervention.",
        description="Arbitrary external process execution via development executor MCP.",
    ),

    # -------------------------------------------------------------------------
    # 3. Domain Tool Activities (ai/tools/domain/)
    # -------------------------------------------------------------------------
    "tool:get_project_status": ActivityClassification(
        activity_name="tool:get_project_status",
        boundary_type=ActivityBoundaryType.TOOL,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Read-only query against local DB; safe to retry indefinitely.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (side-effect-free read).",
        description="Authoritative lifecycle state inspection tool.",
    ),
    "tool:read_blueprint": ActivityClassification(
        activity_name="tool:read_blueprint",
        boundary_type=ActivityBoundaryType.TOOL,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Read-only query; safe to retry indefinitely.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (side-effect-free read).",
        description="Retrieval of project structural blueprint specification.",
    ),
    "tool:patch_blueprint": ActivityClassification(
        activity_name="tool:patch_blueprint",
        boundary_type=ActivityBoundaryType.TOOL,
        semantics=IdempotencySemantics.AT_MOST_ONCE,
        native_idempotency_supported=False,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Fail terminally. Non-idempotent JSON patch mutation could corrupt project state if reapplied blindly.",
        blind_retry_possible=False,
        residual_duplicate_risk="Zero duplicate mutation permitted on crash.",
        description="Domain tool applying structural modifications to project blueprint.",
    ),
    "tool:start_run": ActivityClassification(
        activity_name="tool:start_run",
        boundary_type=ActivityBoundaryType.TOOL,
        semantics=IdempotencySemantics.AT_MOST_ONCE,
        native_idempotency_supported=False,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Fail terminally unless run_id was pre-allocated. Blind retry could launch runaway parallel pipeline runs.",
        blind_retry_possible=False,
        residual_duplicate_risk="Zero duplicate runs permitted.",
        description="Domain tool dispatching pipeline execution runs.",
    ),
    "tool:cancel_run": ActivityClassification(
        activity_name="tool:cancel_run",
        boundary_type=ActivityBoundaryType.TOOL,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=False,
        recovery_after_ambiguous_crash="Idempotent state machine transition; cancelling an already cancelled run is a safe no-op.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (state transition is idempotent).",
        description="Domain tool requesting pipeline run cancellation.",
    ),
    "tool:save_asset_cache": ActivityClassification(
        activity_name="tool:save_asset_cache",
        boundary_type=ActivityBoundaryType.TOOL,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        native_idempotency_supported=True,
        stable_key_propagated=True,
        recovery_after_ambiguous_crash="Content-addressable storage write; identical hash yields identical cache entry.",
        blind_retry_possible=True,
        residual_duplicate_risk="None (content-addressable immutable cache).",
        description="Domain tool persisting media asset variants to cache.",
    ),
}


def validate_activity_semantics(
    activity_name: str,
    requested_semantics: IdempotencySemantics,
    native_idempotency_supported: bool = False,
    is_deterministic_read: bool = False,
    is_deterministic_output: bool = False,
) -> None:
    """
    Enforces the mandatory rule:
    Operations without native idempotency or local side-effect-free read reconciliation
    CANNOT be falsely classified as EFFECTIVELY_ONCE.

    Crucial policy invariant:
    Deterministic output (e.g. embedding vector projection or fixed seed generation)
    DOES NOT equate to effectively-once external execution. External providers lacking
    native wire idempotency will still execute and bill multiple times on ambiguous crash,
    and must be classified as AT_LEAST_ONCE or AT_MOST_ONCE.
    """
    if requested_semantics == IdempotencySemantics.EFFECTIVELY_ONCE:
        if not native_idempotency_supported and not is_deterministic_read:
            raise FalseIdempotencyClaimError(
                f"Activity '{activity_name}' cannot be classified as EFFECTIVELY_ONCE without "
                f"native wire idempotency support or local side-effect-free read reconciliation. "
                f"Deterministic output alone does not prevent duplicate external provider execution or billing."
            )


def get_activity_classification(activity_name: str) -> Optional[ActivityClassification]:
    """Retrieves the authoritative classification record for an activity."""
    return ACTIVITY_CLASSIFICATIONS.get(activity_name)
