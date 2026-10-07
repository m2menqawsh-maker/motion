"""
tests/ai/e2e/test_s28_m_automatic_stock_preparation.py
=====================================================
Automated Stock Media Preparation & Mismatch Resolution Suite (S28-M Evidence Closure).

Validates:
1. Case 1 — Already compatible:
   required = 9:16, 5s | stock = 9:16, 5s -> no unnecessary processing, original AssetRef preserved.
2. Case 2 — Duration mismatch:
   required = 5s | stock = 15s -> automatic TRIM_VIDEO, processed AssetRef.
3. Case 3 — Aspect-ratio mismatch:
   required = 9:16 | stock = 16:9 -> automatic RESIZE_VIDEO, processed AssetRef.
4. Case 4 — Both mismatch:
   required = 9:16, 4s | stock = 16:9, 18s -> automatic TRIM_VIDEO + RESIZE_VIDEO chain.
5. Case 5 — Impossible / unsafe transformation:
   required = 15s | stock = 1.0s (insufficient) -> structured AssetPreparationError fail-closed.
6. Image Stock Mismatch:
   required = 9:16 | stock image = 16:9 -> automatic CROP_IMAGE_TO_RATIO, processed AssetRef.
7. Audio Stock Preparation:
   required = -16 LUFS | stock audio = -25 LUFS -> automatic NORMALIZE_AUDIO, processed AssetRef.
8. End-to-End Product Flow:
   SceneIntent -> Acquired Stock Mismatch -> Automatic Preparation -> ManifestV2 -> BlueprintCompiler -> Valid BlueprintV2.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import pytest
from PIL import Image

from ai.contracts import (
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanStatus,
    CreativeTier,
    ResolvedTemplateDecision,
    SceneIntent,
)
from ai.planning.asset_preparation import (
    AssetPreparationError,
    AssetPreparationOrchestrator,
    PreparedAssetResult,
)
from ai.capabilities.catalog import get_capability_catalog
from ai.planning.compiler import BlueprintCompiler
from ai.planning.tier_policy import CreativeTierPolicy
from ai.routing.capability_router import CapabilityRouter, get_capability_router
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.storage.storage_service import (
    LocalStorageBackend,
    build_storage_key,
    set_storage_service,
)
from scripts.core.template_contract import TemplateRegistryContract


# =============================================================================
# Synthetic Generation Helpers
# =============================================================================

def make_test_video(path: Path, width: int, height: int, duration: float = 3.0, fps: int = 30) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        str(path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def make_test_audio(path: Path, duration: float = 3.0, freq: int = 440) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
        "-c:a", "pcm_s16le",
        str(path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def make_test_image(path: Path, width: int, height: int, color=(100, 150, 200)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), color=color)
    img.save(str(path))


def make_scene_intent(scene_id: str, duration: float, asset_reqs: list) -> SceneIntent:
    return SceneIntent(
        scene_id=scene_id,
        scene_index=0,
        intent_label="product_showcase",
        mood="energetic",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=duration,
        asset_requirements=asset_reqs,
    )


# =============================================================================
# Test Suite
# =============================================================================

class TestAutomaticStockPreparation:

    @staticmethod
    def _reset_process_singletons() -> None:
        """Test isolation: drop singletons that captured a previous test's StorageService."""
        import ai.acquisition.service as _acq
        import ai.image_processing.service as _img
        import ai.routing.capability_router as _cap_router
        import ai.speech.cache as _stt_cache
        import ai.tools.adapters.registry as _reg

        _img._default_image_service = None
        _acq._default_acquisition_service = None
        _stt_cache._default_stt_cache_manager = None
        _reg._default_adapter_registry = None
        _cap_router._default_capability_router = None

    @pytest.fixture(autouse=True)
    def setup_env(self, tmp_path):
        self._reset_process_singletons()
        self.tmp_dir = tmp_path
        self.storage_dir = tmp_path / "storage"
        self.storage = LocalStorageBackend(root_dir=self.storage_dir)
        set_storage_service(self.storage)

        self.catalog = get_capability_catalog()
        self.tool_gateway = ToolGateway(catalog=self.catalog)
        self.router = CapabilityRouter(
            catalog=self.catalog,
            tool_gateway=self.tool_gateway,
        )
        self.orchestrator = AssetPreparationOrchestrator(
            capability_router=self.router,
            storage=self.storage,
        )
        self.ws_id = "ws_test_auto_prep"
        self.proj_id = "prj_auto_prep_01"
        self.ctx = TrustedToolExecutionContext(
            workspace_id=self.ws_id,
            actor_id="test_director",
            roles=["editor"],
            permissions=["viewer", "editor", "asset:upload", "asset:read"],
            accessible_projects=[self.proj_id],
        )

        yield

        set_storage_service(None)
        self._reset_process_singletons()

    # -------------------------------------------------------------------------
    # Case 1: Already Compatible
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_01_already_compatible_no_unnecessary_processing(self):
        """
        Stock asset already matches scene intent: 9:16 (1080x1920) and 5.0s.
        Expected: is_transformed=False, transformations_applied=[], original asset returned.
        """
        local_vid = self.tmp_dir / "stock_matching.mp4"
        make_test_video(local_vid, width=1080, height=1920, duration=5.0)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_stock_match", "stock_matching.mp4")
        self.storage.put(storage_key, local_vid.read_bytes())

        scene = make_scene_intent("scn_01", 5.0, ["stock footage"])

        result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_stock_match",
            source_storage_key=storage_key,
            media_type="video",
            context=self.ctx,
        )

        assert result.is_transformed is False
        assert len(result.transformations_applied) == 0
        assert result.prepared_asset_id == "ast_stock_match"
        assert result.prepared_storage_key == storage_key
        assert result.final_width == 1080
        assert result.final_height == 1920

    # -------------------------------------------------------------------------
    # Case 2: Duration Mismatch
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_02_duration_mismatch_triggers_automatic_trim(self):
        """
        Stock asset is 15.0s, but SceneIntent requires 5.0s. Aspect ratio is already 9:16.
        Expected: automatic TRIM_VIDEO invoked via CapabilityRouter, new canonical asset returned.
        """
        local_vid = self.tmp_dir / "stock_long.mp4"
        make_test_video(local_vid, width=1080, height=1920, duration=15.0)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_stock_long", "stock_long.mp4")
        self.storage.put(storage_key, local_vid.read_bytes())

        scene = make_scene_intent("scn_02", 5.0, ["stock footage"])

        result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_stock_long",
            source_storage_key=storage_key,
            media_type="video",
            context=self.ctx,
        )

        assert result.is_transformed is True
        assert "TRIM_VIDEO" in result.transformations_applied
        assert "RESIZE_VIDEO" not in result.transformations_applied
        assert result.prepared_asset_id != "ast_stock_long"
        assert self.storage.exists(result.prepared_storage_key)
        assert abs(result.final_duration_seconds - 5.0) < 0.2

    # -------------------------------------------------------------------------
    # Case 3: Aspect Ratio Mismatch
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_03_aspect_ratio_mismatch_triggers_automatic_resize(self):
        """
        Stock asset is 16:9 (1920x1080), but SceneIntent requires 9:16 (1080x1920). Duration is 5.0s.
        Expected: automatic RESIZE_VIDEO invoked via CapabilityRouter, 1080x1920 output.
        """
        local_vid = self.tmp_dir / "stock_landscape.mp4"
        make_test_video(local_vid, width=1920, height=1080, duration=5.0)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_stock_land", "stock_landscape.mp4")
        self.storage.put(storage_key, local_vid.read_bytes())

        scene = make_scene_intent("scn_03", 5.0, ["stock footage"])

        result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_stock_land",
            source_storage_key=storage_key,
            media_type="video",
            context=self.ctx,
        )

        assert result.is_transformed is True
        assert "RESIZE_VIDEO" in result.transformations_applied
        assert result.final_width == 1080
        assert result.final_height == 1920
        assert self.storage.exists(result.prepared_storage_key)

    # -------------------------------------------------------------------------
    # Case 4: Both Duration and Aspect Ratio Mismatch
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_04_both_mismatch_chains_trim_and_resize(self):
        """
        Stock asset is 16:9 (1920x1080) and 18.0s.
        SceneIntent requires 9:16 and 4.0s.
        Expected: automatic TRIM_VIDEO followed by RESIZE_VIDEO in sequence.
        """
        local_vid = self.tmp_dir / "stock_raw_untrimmed.mp4"
        make_test_video(local_vid, width=1920, height=1080, duration=18.0)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_stock_raw", "stock_raw.mp4")
        self.storage.put(storage_key, local_vid.read_bytes())

        scene = make_scene_intent("scn_04", 4.0, ["stock footage"])

        result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_stock_raw",
            source_storage_key=storage_key,
            media_type="video",
            context=self.ctx,
        )

        assert result.is_transformed is True
        assert result.transformations_applied == ["TRIM_VIDEO", "RESIZE_VIDEO"]
        assert result.final_width == 1080
        assert result.final_height == 1920
        assert abs(result.final_duration_seconds - 4.0) < 0.2
        assert self.storage.exists(result.prepared_storage_key)

    # -------------------------------------------------------------------------
    # Case 5: Impossible / Unsafe Transformation (Fail Closed)
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_05_insufficient_duration_fails_closed(self):
        """
        Stock asset is 1.0s, but SceneIntent strictly requires 10.0s.
        Expected: fails closed with structured AssetPreparationError (INSUFFICIENT_DURATION).
        """
        local_vid = self.tmp_dir / "stock_too_short.mp4"
        make_test_video(local_vid, width=1080, height=1920, duration=1.0)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_too_short", "stock_too_short.mp4")
        self.storage.put(storage_key, local_vid.read_bytes())

        scene = make_scene_intent("scn_05", 10.0, ["stock footage"])

        with pytest.raises(AssetPreparationError) as exc_info:
            await self.orchestrator.prepare_asset_for_scene(
                project_id=self.proj_id,
                workspace_id=self.ws_id,
                scene_intent=scene,
                target_aspect_ratio="9:16",
                source_asset_id="ast_too_short",
                source_storage_key=storage_key,
                media_type="video",
                context=self.ctx,
            )

        assert exc_info.value.code == "INSUFFICIENT_DURATION"

    # -------------------------------------------------------------------------
    # Case 6: Stock Image Preparation
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_06_stock_image_aspect_ratio_mismatch_auto_crop(self):
        """
        Stock image is 16:9 (1920x1080), but scene requires 9:16.
        Expected: automatic CROP_IMAGE_TO_RATIO invoked via CapabilityRouter.
        """
        local_img = self.tmp_dir / "stock_photo_16_9.png"
        make_test_image(local_img, width=1920, height=1080)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_img_16_9", "stock_photo_16_9.png")
        self.storage.put(storage_key, local_img.read_bytes())

        scene = make_scene_intent("scn_img_01", 3.0, ["stock footage"])

        result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_img_16_9",
            source_storage_key=storage_key,
            media_type="image",
            context=self.ctx,
        )

        assert result.is_transformed is True
        assert "CROP_IMAGE_TO_RATIO" in result.transformations_applied
        assert self.storage.exists(result.prepared_storage_key)

    # -------------------------------------------------------------------------
    # Case 7: Stock Audio Preparation
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_07_stock_audio_loudness_mismatch_auto_normalize(self):
        """
        Stock audio has low loudness (-28 LUFS), broadcast target is -16 LUFS.
        Expected: automatic NORMALIZE_AUDIO invoked via CapabilityRouter.
        """
        local_aud = self.tmp_dir / "stock_audio_quiet.wav"
        make_test_audio(local_aud, duration=4.0, freq=440)

        storage_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_aud_quiet", "stock_audio_quiet.wav")
        self.storage.put(storage_key, local_aud.read_bytes())

        scene = make_scene_intent("scn_aud_01", 4.0, ["stock footage"])

        result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_aud_quiet",
            source_storage_key=storage_key,
            media_type="audio",
            context=self.ctx,
        )

        assert result.is_transformed is True
        assert "NORMALIZE_AUDIO" in result.transformations_applied
        assert self.storage.exists(result.prepared_storage_key)

    # -------------------------------------------------------------------------
    # Case 8: End-to-End Product Integration with BlueprintCompiler
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_case_08_e2e_product_pipeline_automatic_prep_into_blueprint(self):
        """
        Proves the complete product chain:
        Acquired mismatched stock video (1920x1080, 16:9, 12s) ->
        AssetPreparationOrchestrator detects mismatch with 9:16, 4s requirement ->
        Chains TRIM_VIDEO + RESIZE_VIDEO ->
        Prepared AssetRef enters ManifestV2 ->
        BlueprintCompiler references prepared asset ->
        Valid BlueprintV2 compiled without manual developer intervention.
        """
        local_stock = self.tmp_dir / "raw_stock_landscape_12s.mp4"
        make_test_video(local_stock, width=1920, height=1080, duration=12.0)

        raw_key = build_storage_key(self.ws_id, self.proj_id, "assets", "ast_raw_coffee", "raw_stock.mp4")
        self.storage.put(raw_key, local_stock.read_bytes())

        scene = make_scene_intent("scene_hero", 4.0, ["stock footage"])

        # 1. Automatic Preparation Orchestration
        prep_result: PreparedAssetResult = await self.orchestrator.prepare_asset_for_scene(
            project_id=self.proj_id,
            workspace_id=self.ws_id,
            scene_intent=scene,
            target_aspect_ratio="9:16",
            source_asset_id="ast_raw_coffee",
            source_storage_key=raw_key,
            media_type="video",
            context=self.ctx,
        )

        assert prep_result.is_transformed is True
        assert prep_result.transformations_applied == ["TRIM_VIDEO", "RESIZE_VIDEO"]
        assert prep_result.final_width == 1080
        assert prep_result.final_height == 1920

        # 2. Build Manifest with Prepared AssetRef
        manifest = ManifestV2(
            manifest_version="2.0.0",
            project_id=self.proj_id,
            assets=[
                AssetV2(
                    asset_id=prep_result.prepared_asset_id,
                    kind=AssetKind.VIDEO,
                    provenance=Provenance.GENERATED,
                    status=AssetStatus.READY,
                    source_path=prep_result.prepared_storage_key,
                )
            ],
        )

        # 3. CreativePlan with SceneIntent via canonical CreativePlanner
        from ai.intent.brief_builder import CreativeBriefBuilder
        from ai.narrative.planner import NarrativePlanner
        from ai.planning.creative_planner import CreativePlanner
        from ai.recipes.registry import RecipeRegistry

        brief = CreativeBriefBuilder().build_brief(
            user_request="High-converting vertical coffee showcase ad",
            workspace_id=self.ws_id,
            project_id=self.proj_id,
        )
        recipe = RecipeRegistry().get("product-showcase")
        narrative = NarrativePlanner().plan(brief=brief, recipe=recipe)
        cplan_raw = CreativePlanner().plan(brief=brief, recipe=recipe, narrative_plan=narrative, taste_decisions=None)
        cplan = cplan_raw.model_copy(update={"scenes": [scene]})

        # 4. Blueprint Compilation
        tier_policy = CreativeTierPolicy()
        tier_dec = tier_policy.decide(
            scene_intent=scene,
            requested_tier=CreativeTier.REUSE,
            aspect_ratio="9:16",
            audio_mode=AudioMode.VO_MUSIC,
        )
        template_decisions = {
            scene.scene_id: ResolvedTemplateDecision(
                scene_id=scene.scene_id,
                template_id=tier_dec.template_ref or "rui-b-roll-stack",
                template_props={"videoAssetId": prep_result.prepared_asset_id},
            )
        }

        compiler = BlueprintCompiler()
        compile_res = compiler.compile(
            plan=cplan,
            template_decisions=template_decisions,
            manifest=manifest,
            template_registry=TemplateRegistryContract(),
            aspect_ratio="9:16",
            audio_mode=AudioMode.VO_MUSIC,
        )

        assert compile_res.success is True
        bp = compile_res.blueprint
        assert bp["aspect_ratio"] == "9:16"
        assert len(bp["scenes"]) == 1
        assert bp["scenes"][0]["template_props"]["videoAssetId"] == prep_result.prepared_asset_id
        # Duration frames at 30fps for 4.0s = 120 frames
        assert bp["scenes"][0]["durationFrames"] == 120
