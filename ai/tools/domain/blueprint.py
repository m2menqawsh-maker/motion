"""
ai/tools/domain/blueprint.py
============================
Domain tool adapter for blueprint queries and mutations (S27.9).

Invariants:
- Zero raw file writing or bypassing validation.
- All mutations pass through PipelineService validation and StateStore.
- Optimistic state tracking and revision monotonicity.
"""

from __future__ import annotations

from api.services.pipeline_service import PipelineService
from ai.tools.contracts import (
    PatchBlueprintInput,
    PatchBlueprintOutput,
    ReadBlueprintInput,
    ReadBlueprintOutput,
)
from ai.tools.types import TrustedToolExecutionContext


def read_blueprint_adapter(
    input_data: ReadBlueprintInput,
    context: TrustedToolExecutionContext,
) -> ReadBlueprintOutput:
    """
    Reads the authoritative blueprint representation via PipelineService.
    """
    bp_dict = PipelineService.get_blueprint(input_data.project_id)
    if not bp_dict:
        raise ValueError(f"Blueprint for project '{input_data.project_id}' not found.")

    scenes = bp_dict.get("scenes") or []
    audio = bp_dict.get("audio")

    # Fetch current revision from project status
    from api.services.project_service import ProjectService
    status_dto = ProjectService.get_lifecycle_dto(input_data.project_id)

    return ReadBlueprintOutput(
        project_id=input_data.project_id,
        revision=status_dto.revision,
        fps=int(bp_dict.get("fps", 30)),
        aspect_ratio=str(bp_dict.get("aspect_ratio", "16:9")),
        scene_count=len(scenes),
        scenes=scenes,
        audio=audio,
    )


def patch_blueprint_adapter(
    input_data: PatchBlueprintInput,
    context: TrustedToolExecutionContext,
) -> PatchBlueprintOutput:
    """
    Validates and mutates project blueprint via PipelineService.
    Guarantees optimistic locking, project identity alignment, and timeout safety.
    """
    # 1. Pre-execution timeout checkpoint
    context.assert_not_timed_out()

    bp_dict = input_data.blueprint.to_dict()

    # 2. Structural & domain validation via PipelineService
    ok, errors = PipelineService.validate_blueprint_payload(
        input_data.project_id,
        bp_dict,
    )
    if not ok:
        raise ValueError(f"Blueprint validation failed: {'; '.join(errors)}")

    # 3. Optimistic concurrency control (expected revision check)
    from api.services.project_service import ProjectService
    status_dto = ProjectService.get_lifecycle_dto(input_data.project_id)
    if input_data.expected_revision is not None and status_dto.revision != input_data.expected_revision:
        raise ValueError(
            f"Stale revision conflict: expected revision {input_data.expected_revision}, "
            f"current project revision is {status_dto.revision}."
        )

    # 4. Pre-commit timeout checkpoint (guarantees zero side-effect if timeout elapsed)
    context.assert_not_timed_out()

    # 5. Mutate blueprint via authoritative domain service
    PipelineService.mutate_blueprint(
        project_id=input_data.project_id,
        payload=bp_dict,
        actor_id=context.actor_id,
    )

    new_status_dto = ProjectService.get_lifecycle_dto(input_data.project_id)

    return PatchBlueprintOutput(
        project_id=input_data.project_id,
        revision=new_status_dto.revision,
        success=True,
        message="Blueprint successfully validated and applied.",
    )
