"""
ai/planning/asset_preparation.py
================================
Canonical Asset Preparation Orchestrator (S28-M).

Invariants:
- Coordinates mismatch detection between SceneIntent requirements and acquired assets.
- Automatically determines required media transformations (probe, trim, resize, crop, loudness normalize).
- Dispatches all transformations strictly through CapabilityRouter -> ToolGateway.
- Zero direct FFmpeg commands or shell strings.
- Never mutates raw host filesystem; interacts strictly with StorageService & AssetService.
- Produces canonical prepared AssetRefs for downstream BlueprintCompiler consumption.
- Fails closed on impossible or unsafe transformations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ai.contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.contracts.creative.plan import SceneIntent
from ai.routing.capability_router import CapabilityRouter, get_capability_router
from ai.tools.types import TrustedToolExecutionContext
from api.services.asset_service import AssetService
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.storage.storage_service import StorageService, get_storage_service

logger = logging.getLogger("clean_video.ai.planning.asset_preparation")


class AssetPreparationError(Exception):
    """Raised when asset preparation fails or cannot be safely satisfied."""
    def __init__(self, message: str, code: str = "PREPARATION_FAILED", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class PreparedAssetResult(BaseModel):
    """Result of automated asset preparation against scene intent requirements."""
    project_id: str
    original_asset_id: str
    prepared_asset_id: str
    original_storage_key: str
    prepared_storage_key: str
    is_transformed: bool
    transformations_applied: List[str] = Field(default_factory=list)
    final_width: Optional[int] = None
    final_height: Optional[int] = None
    final_duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetPreparationOrchestrator:
    """
    Authoritative domain orchestrator that inspects acquired assets against
    SceneIntent requirements and automatically dispatches canonical capabilities
    (TRIM_VIDEO, RESIZE_VIDEO, CROP_IMAGE_TO_RATIO, NORMALIZE_AUDIO) when mismatches are detected.
    """

    ASPECT_RATIO_DIMENSIONS = {
        "9:16": (1080, 1920),
        "16:9": (1920, 1080),
        "1:1": (1080, 1080),
        "4:5": (1080, 1350),
    }

    def __init__(
        self,
        capability_router: Optional[CapabilityRouter] = None,
        storage: Optional[StorageService] = None,
        asset_service: Optional[Any] = None,
    ) -> None:
        self.router = capability_router or get_capability_router()
        self.storage = storage or get_storage_service()
        self.asset_service = asset_service or AssetService

    async def prepare_asset_for_scene(
        self,
        project_id: str,
        workspace_id: str,
        scene_intent: SceneIntent,
        target_aspect_ratio: str,
        source_asset_id: str,
        source_storage_key: str,
        media_type: str = "video",
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> PreparedAssetResult:
        """
        Main orchestration entry point.
        Compares acquired asset characteristics with scene requirements and
        executes automated transformation chain via CapabilityRouter if needed.
        """
        ctx = context or TrustedToolExecutionContext(
            workspace_id=workspace_id,
            actor_id="system_asset_preparer",
            roles=["editor"],
            permissions=["viewer", "editor", "asset:upload", "asset:read"],
            accessible_projects=[project_id],
        )

        # Basic source presence validation
        if not self.storage.exists(source_storage_key):
            raise AssetPreparationError(
                f"Source asset '{source_asset_id}' not found in storage key '{source_storage_key}'.",
                code="SOURCE_NOT_FOUND",
                details={"asset_id": source_asset_id, "storage_key": source_storage_key},
            )

        mtype = media_type.lower().strip()
        if mtype in ("video", "stock_video"):
            return await self._prepare_video(
                project_id=project_id,
                workspace_id=workspace_id,
                scene_intent=scene_intent,
                target_aspect_ratio=target_aspect_ratio,
                source_asset_id=source_asset_id,
                source_storage_key=source_storage_key,
                ctx=ctx,
            )
        elif mtype in ("image", "stock_image", "photo"):
            return await self._prepare_image(
                project_id=project_id,
                workspace_id=workspace_id,
                scene_intent=scene_intent,
                target_aspect_ratio=target_aspect_ratio,
                source_asset_id=source_asset_id,
                source_storage_key=source_storage_key,
                ctx=ctx,
            )
        elif mtype in ("audio", "music", "sound_effect", "sfx"):
            return await self._prepare_audio(
                project_id=project_id,
                workspace_id=workspace_id,
                scene_intent=scene_intent,
                source_asset_id=source_asset_id,
                source_storage_key=source_storage_key,
                ctx=ctx,
            )
        else:
            raise AssetPreparationError(
                f"Unsupported media type for preparation: '{media_type}'.",
                code="UNSUPPORTED_MEDIA_TYPE",
            )

    # -------------------------------------------------------------------------
    # Video Asset Preparation Flow
    # -------------------------------------------------------------------------

    async def _prepare_video(
        self,
        project_id: str,
        workspace_id: str,
        scene_intent: SceneIntent,
        target_aspect_ratio: str,
        source_asset_id: str,
        source_storage_key: str,
        ctx: TrustedToolExecutionContext,
    ) -> PreparedAssetResult:
        desired_duration = scene_intent.estimated_duration_sec
        target_dims = self.ASPECT_RATIO_DIMENSIONS.get(target_aspect_ratio, (1080, 1920))
        target_w, target_h = target_dims

        # 1. Automatic INSPECT_MEDIA via CapabilityRouter
        probe_req = CapabilityRequest(
            capability_id=CapabilityType.INSPECT_MEDIA,
            workspace_id=workspace_id,
            project_id=project_id,
            input={"project_id": project_id, "storage_keys": [source_storage_key]},
        )
        probe_res = await self.router.route_and_execute(probe_req, context=ctx)
        if probe_res.status != CapabilityStatus.SUCCESS or not probe_res.output:
            raise AssetPreparationError(
                f"Failed to probe video asset '{source_asset_id}': {probe_res.error}",
                code="PROBE_FAILED",
            )

        probe_data = probe_res.output
        files_info = probe_data.get("files_info", [])
        first_file = files_info[0] if files_info else {}
        actual_duration = float(first_file.get("duration_seconds") or 0.0)
        actual_width = int(first_file.get("width") or 0)
        actual_height = int(first_file.get("height") or 0)

        if actual_duration <= 0.0 or actual_width <= 0 or actual_height <= 0:
            raise AssetPreparationError(
                f"Video asset '{source_asset_id}' is corrupt or unreadable.",
                code="CORRUPT_MEDIA",
            )

        # Check safety: cannot satisfy scene if source is substantially shorter than requested
        # without explicit loop policy
        if actual_duration < (desired_duration - 0.5):
            raise AssetPreparationError(
                f"Source video duration ({actual_duration:.1f}s) is shorter than required scene duration ({desired_duration:.1f}s).",
                code="INSUFFICIENT_DURATION",
                details={"actual_duration": actual_duration, "required_duration": desired_duration},
            )

        # 2. Evaluate Mismatches
        needs_trim = (actual_duration - desired_duration) > 0.25
        source_ratio = actual_width / actual_height
        target_ratio = target_w / target_h
        needs_resize = abs(source_ratio - target_ratio) > 0.05 or actual_width != target_w or actual_height != target_h

        # Case 1: Already compatible
        if not needs_trim and not needs_resize:
            return PreparedAssetResult(
                project_id=project_id,
                original_asset_id=source_asset_id,
                prepared_asset_id=source_asset_id,
                original_storage_key=source_storage_key,
                prepared_storage_key=source_storage_key,
                is_transformed=False,
                transformations_applied=[],
                final_width=actual_width,
                final_height=actual_height,
                final_duration_seconds=actual_duration,
                metadata=first_file,
            )

        transformations: List[str] = []
        current_key = source_storage_key
        current_duration = actual_duration
        current_w = actual_width
        current_h = actual_height

        # 3. Automatic TRIM_VIDEO if duration exceeds requirement
        if needs_trim:
            trim_req = CapabilityRequest(
                capability_id=CapabilityType.TRIM_VIDEO,
                workspace_id=workspace_id,
                project_id=project_id,
                input={
                    "project_id": project_id,
                    "video_storage_key": current_key,
                    "start_time_seconds": 0.0,
                    "duration_seconds": desired_duration,
                },
            )
            trim_res = await self.router.route_and_execute(trim_req, context=ctx)
            if trim_res.status != CapabilityStatus.SUCCESS or not trim_res.output:
                raise AssetPreparationError(
                    f"Automated trim failed on asset '{source_asset_id}': {trim_res.error}",
                    code="TRIM_FAILED",
                )
            current_key = trim_res.output["output_storage_key"]
            current_duration = trim_res.output.get("duration_seconds", desired_duration)
            transformations.append("TRIM_VIDEO")

        # 4. Automatic RESIZE_VIDEO if aspect ratio or dimensions mismatch
        if needs_resize:
            resize_req = CapabilityRequest(
                capability_id=CapabilityType.RESIZE_VIDEO,
                workspace_id=workspace_id,
                project_id=project_id,
                input={
                    "project_id": project_id,
                    "video_storage_key": current_key,
                    "target_width": target_w,
                    "target_height": target_h,
                    "mode": "cover",
                },
            )
            resize_res = await self.router.route_and_execute(resize_req, context=ctx)
            if resize_res.status != CapabilityStatus.SUCCESS or not resize_res.output:
                raise AssetPreparationError(
                    f"Automated resize/crop failed on asset '{source_asset_id}': {resize_res.error}",
                    code="RESIZE_FAILED",
                )
            current_key = resize_res.output["output_storage_key"]
            current_w = resize_res.output.get("width", target_w)
            current_h = resize_res.output.get("height", target_h)
            transformations.append("RESIZE_VIDEO")

        # 5. Register Prepared Canonical Asset
        prepared_asset_id = f"ast_prep_{uuid.uuid4().hex[:10]}"
        try:
            self.asset_service.update_asset_status(
                project_id=project_id,
                asset_id=prepared_asset_id,
                new_status="ready",
            )
        except Exception:
            pass

        return PreparedAssetResult(
            project_id=project_id,
            original_asset_id=source_asset_id,
            prepared_asset_id=prepared_asset_id,
            original_storage_key=source_storage_key,
            prepared_storage_key=current_key,
            is_transformed=True,
            transformations_applied=transformations,
            final_width=current_w,
            final_height=current_h,
            final_duration_seconds=current_duration,
            metadata={
                "target_aspect_ratio": target_aspect_ratio,
                "desired_duration": desired_duration,
                "original_probe": probe_data,
            },
        )

    # -------------------------------------------------------------------------
    # Image Asset Preparation Flow
    # -------------------------------------------------------------------------

    async def _prepare_image(
        self,
        project_id: str,
        workspace_id: str,
        scene_intent: SceneIntent,
        target_aspect_ratio: str,
        source_asset_id: str,
        source_storage_key: str,
        ctx: TrustedToolExecutionContext,
    ) -> PreparedAssetResult:
        target_dims = self.ASPECT_RATIO_DIMENSIONS.get(target_aspect_ratio, (1080, 1920))
        target_w, target_h = target_dims

        # 1. Automatic PROBE_IMAGE
        probe_req = CapabilityRequest(
            capability_id=CapabilityType.PROBE_IMAGE,
            workspace_id=workspace_id,
            project_id=project_id,
            input={"project_id": project_id, "image_storage_key": source_storage_key},
        )
        probe_res = await self.router.route_and_execute(probe_req, context=ctx)
        if probe_res.status != CapabilityStatus.SUCCESS or not probe_res.output:
            raise AssetPreparationError(
                f"Failed to probe image asset '{source_asset_id}': {probe_res.error}",
                code="PROBE_FAILED",
            )

        probe_data = probe_res.output
        actual_width = int(probe_data.get("width") or 0)
        actual_height = int(probe_data.get("height") or 0)

        if actual_width <= 0 or actual_height <= 0:
            raise AssetPreparationError(
                f"Image asset '{source_asset_id}' has invalid dimensions.",
                code="CORRUPT_MEDIA",
            )

        source_ratio = actual_width / actual_height
        target_ratio = target_w / target_h
        needs_crop_or_resize = abs(source_ratio - target_ratio) > 0.05 or actual_width != target_w or actual_height != target_h

        if not needs_crop_or_resize:
            return PreparedAssetResult(
                project_id=project_id,
                original_asset_id=source_asset_id,
                prepared_asset_id=source_asset_id,
                original_storage_key=source_storage_key,
                prepared_storage_key=source_storage_key,
                is_transformed=False,
                transformations_applied=[],
                final_width=actual_width,
                final_height=actual_height,
                metadata=probe_data,
            )

        # 2. Automated Crop to Ratio & Resize via CapabilityRouter
        crop_req = CapabilityRequest(
            capability_id=CapabilityType.CROP_IMAGE_TO_RATIO,
            workspace_id=workspace_id,
            project_id=project_id,
            input={
                "project_id": project_id,
                "image_storage_key": source_storage_key,
                "target_ratio": target_aspect_ratio,
            },
        )
        crop_res = await self.router.route_and_execute(crop_req, context=ctx)
        if crop_res.status != CapabilityStatus.SUCCESS or not crop_res.output:
            raise AssetPreparationError(
                f"Automated image crop failed on asset '{source_asset_id}': {crop_res.error}",
                code="CROP_FAILED",
            )

        prepared_key = crop_res.output["output_storage_key"]
        final_w = crop_res.output.get("width", target_w)
        final_h = crop_res.output.get("height", target_h)
        prepared_asset_id = f"ast_prep_img_{uuid.uuid4().hex[:10]}"

        return PreparedAssetResult(
            project_id=project_id,
            original_asset_id=source_asset_id,
            prepared_asset_id=prepared_asset_id,
            original_storage_key=source_storage_key,
            prepared_storage_key=prepared_key,
            is_transformed=True,
            transformations_applied=["CROP_IMAGE_TO_RATIO"],
            final_width=final_w,
            final_height=final_h,
            metadata=probe_data,
        )

    # -------------------------------------------------------------------------
    # Audio Asset Preparation Flow
    # -------------------------------------------------------------------------

    async def _prepare_audio(
        self,
        project_id: str,
        workspace_id: str,
        scene_intent: SceneIntent,
        source_asset_id: str,
        source_storage_key: str,
        ctx: TrustedToolExecutionContext,
    ) -> PreparedAssetResult:
        # 1. Automatic ANALYZE_LOUDNESS
        loudness_req = CapabilityRequest(
            capability_id=CapabilityType.ANALYZE_LOUDNESS,
            workspace_id=workspace_id,
            project_id=project_id,
            input={"project_id": project_id, "audio_storage_key": source_storage_key},
        )
        loudness_res = await self.router.route_and_execute(loudness_req, context=ctx)
        if loudness_res.status != CapabilityStatus.SUCCESS or not loudness_res.output:
            raise AssetPreparationError(
                f"Failed to analyze audio asset '{source_asset_id}': {loudness_res.error}",
                code="ANALYSIS_FAILED",
            )

        loudness_data = loudness_res.output
        actual_lufs = float(loudness_data.get("integrated_lufs") or -24.0)
        actual_duration = float(loudness_data.get("duration_seconds") or 0.0)

        # Standard broadcast target is -16.0 LUFS
        needs_norm = abs(actual_lufs - (-16.0)) > 2.0

        if not needs_norm:
            return PreparedAssetResult(
                project_id=project_id,
                original_asset_id=source_asset_id,
                prepared_asset_id=source_asset_id,
                original_storage_key=source_storage_key,
                prepared_storage_key=source_storage_key,
                is_transformed=False,
                transformations_applied=[],
                final_duration_seconds=actual_duration,
                metadata=loudness_data,
            )

        # 2. Automatic NORMALIZE_AUDIO
        norm_req = CapabilityRequest(
            capability_id=CapabilityType.NORMALIZE_AUDIO,
            workspace_id=workspace_id,
            project_id=project_id,
            input={
                "project_id": project_id,
                "audio_storage_key": source_storage_key,
                "target_lufs": -16.0,
            },
        )
        norm_res = await self.router.route_and_execute(norm_req, context=ctx)
        if norm_res.status != CapabilityStatus.SUCCESS or not norm_res.output:
            raise AssetPreparationError(
                f"Automated audio normalization failed on asset '{source_asset_id}': {norm_res.error}",
                code="NORMALIZATION_FAILED",
            )

        prepared_key = norm_res.output["output_storage_key"]
        prepared_asset_id = f"ast_prep_aud_{uuid.uuid4().hex[:10]}"

        return PreparedAssetResult(
            project_id=project_id,
            original_asset_id=source_asset_id,
            prepared_asset_id=prepared_asset_id,
            original_storage_key=source_storage_key,
            prepared_storage_key=prepared_key,
            is_transformed=True,
            transformations_applied=["NORMALIZE_AUDIO"],
            final_duration_seconds=actual_duration,
            metadata={"original_lufs": actual_lufs, "target_lufs": -16.0},
        )
