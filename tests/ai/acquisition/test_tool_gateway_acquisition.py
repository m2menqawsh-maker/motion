"""
Tool Gateway Routing and Adapter Integration Tests for Acquisition Capabilities (S28-M05).
"""

from unittest.mock import AsyncMock, patch
import pytest

from ai.acquisition.contracts import (
    AcquiredAssetResult,
    DownloadVariant,
    LicenseClassification,
    CommercialUseStatus,
    StockCandidate,
    StockMediaType,
)
from ai.contracts import (
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.routing.capability_router import get_capability_router
from ai.tools.adapters.acquisition import AssetAcquisitionAdapter
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def trusted_editor_ctx() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_test",
        actor_id="usr_editor",
        roles=["editor"],
        permissions=["editor"],
        is_admin=False,
        accessible_projects=["prj_1"],
    )


class TestAcquisitionGatewayRouting:
    """Verifies that CapabilityRouter and ToolGateway properly resolve AssetAcquisitionAdapter."""

    def test_router_resolves_all_8_acquisition_capabilities_to_adapter(self):
        router = get_capability_router()
        gateway = ToolGateway()

        acquisition_caps = [
            CapabilityType.SEARCH_STOCK_IMAGES,
            CapabilityType.SEARCH_STOCK_VIDEOS,
            CapabilityType.SEARCH_STOCK_AUDIO,
            CapabilityType.SEARCH_SOUND_EFFECTS,
            CapabilityType.SEARCH_ICONS,
            CapabilityType.DOWNLOAD_ICON,
            CapabilityType.DOWNLOAD_REMOTE_MEDIA,
            CapabilityType.EXTRACT_MEDIA_PAGE,
        ]

        for cap_id in acquisition_caps:
            cap_def = router.catalog.get(cap_id)
            assert cap_def is not None, f"Capability {cap_id} missing from registry"

            adapter, impl = gateway.adapter_registry.resolve(cap_def)
            assert adapter is not None, f"No adapter resolved for {cap_id}"
            assert isinstance(adapter, AssetAcquisitionAdapter), f"Expected AssetAcquisitionAdapter for {cap_id}, got {type(adapter)}"

    @pytest.mark.asyncio
    async def test_search_icons_via_gateway(self, trusted_editor_ctx):
        gateway = ToolGateway()
        mock_candidates = [
            StockCandidate(
                candidate_id="iconify:mdi:home",
                source="iconify",
                source_asset_id="mdi:home",
                media_type=StockMediaType.ICON,
                title="Material Design Icons / home",
                preview_url="https://api.iconify.design/mdi/home.svg",
                download_variants=[
                    DownloadVariant(variant_id="svg_vector", url="https://api.iconify.design/mdi/home.svg", format="svg")
                ],
                license=LicenseClassification.OPEN_SOURCE_ICON,
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                retrieved_at="2026-10-04T12:00:00Z",
            )
        ]

        with patch("ai.acquisition.service.AssetAcquisitionService.search_stock", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_candidates

            req = CapabilityRequest(
                capability_id=CapabilityType.SEARCH_ICONS,
                input={"query": "home", "limit": 5},
            )

            result: CapabilityResult = await gateway.execute(req, context=trusted_editor_ctx)
            assert result.status == CapabilityStatus.SUCCESS
            assert result.output_data is not None
            assert "icons" in result.output_data
            assert len(result.output_data["icons"]) == 1
            assert result.output_data["icons"][0]["icon_name"] == "mdi:home"

    @pytest.mark.asyncio
    async def test_download_remote_media_via_gateway(self, trusted_editor_ctx):
        gateway = ToolGateway()
        mock_acquired = AcquiredAssetResult(
            project_id="prj_1",
            asset_id="asset_downloaded_01",
            storage_key="projects/prj_1/assets/ready/remote.mp4",
            content_hash="hash_remote_999",
            media_type=StockMediaType.VIDEO,
            file_size_bytes=1024,
            content_type="video/mp4",
            provenance_evidence={"source_url": "https://example.com/video.mp4"},
            is_reused_existing=False,
        )

        with patch("ai.acquisition.service.AssetAcquisitionService.download_remote_media", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = mock_acquired

            req = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={
                    "project_id": "prj_1",
                    "url": "https://example.com/video.mp4",
                    "media_type": "video",
                },
            )

            result: CapabilityResult = await gateway.execute(req, context=trusted_editor_ctx)
            assert result.status == CapabilityStatus.SUCCESS
            assert result.output_data["asset_id"] == "asset_downloaded_01"
            assert result.output_data["storage_key"] == "projects/prj_1/assets/ready/remote.mp4"

    @pytest.mark.asyncio
    async def test_search_stock_images_via_gateway(self, trusted_editor_ctx):
        gateway = ToolGateway()
        mock_candidates = [
            StockCandidate(
                candidate_id="pexels:54321",
                source="pexels",
                source_asset_id="54321",
                media_type=StockMediaType.IMAGE,
                title="Mountain Sunset",
                preview_url="https://images.pexels.com/prev.jpg",
                download_variants=[
                    DownloadVariant(variant_id="large", url="https://images.pexels.com/large.jpg", width=1920, height=1080)
                ],
                width=1920,
                height=1080,
                license=LicenseClassification.PEXELS_LICENSE,
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                retrieved_at="2026-10-04T12:00:00Z",
            )
        ]

        with patch("ai.acquisition.service.AssetAcquisitionService.search_stock", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_candidates

            req = CapabilityRequest(
                capability_id=CapabilityType.SEARCH_STOCK_IMAGES,
                input={"query": "mountain", "per_page": 10},
            )

            result: CapabilityResult = await gateway.execute(req, context=trusted_editor_ctx)
            assert result.status == CapabilityStatus.SUCCESS
            assert "images" in result.output_data
            assert len(result.output_data["images"]) == 1
            assert result.output_data["images"][0]["media_id"] == "pexels:54321"


class TestToolGatewayIdempotency:
    """Verifies concurrency safety, conflict detection, and deduplication via IdempotencyStore."""

    @pytest.fixture(autouse=True)
    def clean_idempotency_db(self):
        from scripts.core.database import get_database_engine
        engine = get_database_engine()
        with engine.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM tool_idempotency_records WHERE idempotency_key LIKE 'idemp_%' OR idempotency_key LIKE 'shared_%' OR idempotency_key LIKE 'retry_%'")
        yield
        with engine.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM tool_idempotency_records WHERE idempotency_key LIKE 'idemp_%' OR idempotency_key LIKE 'shared_%' OR idempotency_key LIKE 'retry_%'")

    @pytest.mark.asyncio
    async def test_concurrent_identical_requests_execute_single_side_effect(self, trusted_editor_ctx):
        import asyncio
        call_count = 0

        async def _mock_download(project_id, url, media_type, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate bounded work
            return AcquiredAssetResult(
                project_id=project_id,
                asset_id="ast_idemp_123",
                storage_key="projects/prj_1/assets/ready/remote.mp4",
                content_hash="hash_123",
                media_type=StockMediaType.VIDEO,
                file_size_bytes=2048,
                content_type="video/mp4",
                provenance_evidence={"url": url},
                is_reused_existing=False,
            )

        # Independent gateway instances simulating distinct workers/processes
        gateway1 = ToolGateway()
        gateway2 = ToolGateway()

        with patch("ai.acquisition.service.AssetAcquisitionService.download_remote_media", side_effect=_mock_download):
            req1 = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={"project_id": "prj_1", "url": "https://example.com/video.mp4", "media_type": "video"},
                idempotency_key="idemp_key_concur_001",
            )
            req2 = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={"project_id": "prj_1", "url": "https://example.com/video.mp4", "media_type": "video"},
                idempotency_key="idemp_key_concur_001",
            )

            res1, res2 = await asyncio.gather(
                gateway1.execute(req1, context=trusted_editor_ctx),
                gateway2.execute(req2, context=trusted_editor_ctx),
            )

            # Exactly one execution occurred across distinct gateway instances
            assert call_count == 1
            assert res1.status == CapabilityStatus.SUCCESS
            assert res2.status == CapabilityStatus.SUCCESS
            assert res1.output_data["asset_id"] == "ast_idemp_123"
            assert res2.output_data["asset_id"] == "ast_idemp_123"
            # One must be leader, one must be idempotency_hit
            hits = [r.execution_metadata.get("idempotency_hit", False) for r in (res1, res2)]
            assert any(hits)

    @pytest.mark.asyncio
    async def test_same_idempotency_key_different_payload_fails_with_conflict(self, trusted_editor_ctx):
        gateway1 = ToolGateway()
        gateway2 = ToolGateway()
        mock_acquired = AcquiredAssetResult(
            project_id="prj_1",
            asset_id="ast_idemp_1",
            storage_key="k1",
            content_hash="h1",
            media_type=StockMediaType.VIDEO,
            file_size_bytes=100,
            content_type="video/mp4",
            provenance_evidence={},
        )
        with patch("ai.acquisition.service.AssetAcquisitionService.download_remote_media", AsyncMock(return_value=mock_acquired)):
            req1 = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={"project_id": "prj_1", "url": "https://example.com/video1.mp4", "media_type": "video"},
                idempotency_key="shared_key_002",
            )
            req2 = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={"project_id": "prj_1", "url": "https://example.com/video2.mp4", "media_type": "video"},
                idempotency_key="shared_key_002",
            )

            res1 = await gateway1.execute(req1, context=trusted_editor_ctx)
            assert res1.status == CapabilityStatus.SUCCESS

            res2 = await gateway2.execute(req2, context=trusted_editor_ctx)
            assert res2.status == CapabilityStatus.FAILED
            assert res2.error.code.value == "POLICY_DENIED"
            assert "Idempotency conflict" in res2.error.message

    @pytest.mark.asyncio
    async def test_retry_after_side_effect_returns_cached_asset_without_duplication(self, trusted_editor_ctx):
        gateway_worker_a = ToolGateway()
        call_count = 0

        async def _mock_download(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return AcquiredAssetResult(
                project_id="prj_1",
                asset_id="ast_idemp_retry",
                storage_key="k",
                content_hash="h",
                media_type=StockMediaType.VIDEO,
                file_size_bytes=500,
                content_type="video/mp4",
                provenance_evidence={},
            )

        with patch("ai.acquisition.service.AssetAcquisitionService.download_remote_media", side_effect=_mock_download):
            req = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={"project_id": "prj_1", "url": "https://example.com/retry.mp4", "media_type": "video"},
                idempotency_key="retry_key_003",
            )

            first_run = await gateway_worker_a.execute(req, context=trusted_editor_ctx)

            # Second execution through a completely distinct gateway worker instance
            gateway_worker_b = ToolGateway()
            retry_run = await gateway_worker_b.execute(req, context=trusted_editor_ctx)

            assert call_count == 1
            assert first_run.status == CapabilityStatus.SUCCESS
            assert retry_run.status == CapabilityStatus.SUCCESS
            assert retry_run.execution_metadata.get("idempotency_hit") is True
            assert retry_run.output_data["asset_id"] == "ast_idemp_retry"

    @pytest.mark.asyncio
    async def test_cross_process_crash_recovery_and_lease_expiry(self, trusted_editor_ctx):
        """
        Verifies cross-process crash recovery:
        1. If Worker A completes side-effect and terminates, Worker B recovers from durable DB.
        2. If Worker A crashed mid-execution and its lease expires, Worker C takes over without deadlock.
        """
        from scripts.core.idempotency_repository import SQLIdempotencyRepository

        repo = SQLIdempotencyRepository()
        call_count = 0

        async def _mock_download(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return AcquiredAssetResult(
                project_id="prj_1",
                asset_id="ast_idemp_crashed",
                storage_key="k",
                content_hash="h_crash",
                media_type=StockMediaType.VIDEO,
                file_size_bytes=800,
                content_type="video/mp4",
                provenance_evidence={},
            )

        crash_key = "idemp_crash_lease_test"
        with repo.db.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM tool_idempotency_records WHERE idempotency_key = ?", (crash_key,))

        # Simulate Worker A claiming lease but crashing (stale lease in the past)
        with repo.db.transaction("IMMEDIATE") as conn:
            conn.execute(
                "INSERT INTO tool_idempotency_records ("
                "idempotency_key, payload_hash, status, result_json, error_json, created_at, updated_at, lease_expires_at"
                ") VALUES (?, ?, 'IN_PROGRESS', NULL, NULL, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                (crash_key, "expected_payload_hash"),
            )

        with patch("ai.acquisition.service.AssetAcquisitionService.download_remote_media", side_effect=_mock_download):
            req = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={"project_id": "prj_1", "url": "https://example.com/crash.mp4", "media_type": "video"},
                idempotency_key=crash_key,
            )

            # Compute actual payload hash for the input
            gw_temp = ToolGateway()
            req_hash = gw_temp._compute_payload_hash(req.input)
            with repo.db.transaction("IMMEDIATE") as conn:
                conn.execute("UPDATE tool_idempotency_records SET payload_hash = ? WHERE idempotency_key = ?", (req_hash, crash_key))

            # Worker C arrives after Worker A crashed and lease expired
            gateway_worker_c = ToolGateway()
            recovery_run = await gateway_worker_c.execute(req, context=trusted_editor_ctx)

            assert recovery_run.status == CapabilityStatus.SUCCESS
            assert call_count == 1
            assert recovery_run.output_data["asset_id"] == "ast_idemp_crashed"

    @pytest.mark.asyncio
    async def test_crash_after_side_effect_recovers_without_duplicate_canonical_mutation(self, trusted_editor_ctx):
        """
        Simulates:
        1. Worker A executes side effect committed (writes to DB & AssetService manifest)
        2. Worker A process dies before gateway records COMPLETED (status stays IN_PROGRESS)
        3. Lease expires
        4. Second independent gateway Worker B retries
        Expected:
        - Worker B assumes leadership on expired lease
        - Domain-level CAS / content-hash deduplication detects committed asset
        - Zero duplicate canonical mutation (strictly 1 asset in manifest, 1 row in canonical_assets)
        - Gateway transitions record to COMPLETED
        """
        import hashlib
        import shutil
        from pathlib import Path
        from unittest.mock import AsyncMock
        from ai.acquisition.safe_downloader import DownloadedPayload
        from api.services.asset_service import AssetService
        from scripts.core.canonical_asset_repository import CanonicalAssetRepository
        from scripts.core.idempotency_repository import SQLIdempotencyRepository

        project_id = "prj_crash_window_recovery"
        proj_dir = Path("projects") / project_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = proj_dir / "02_asset_manifest.json"
        manifest_path.write_text(f'{{"schema_version": "2.0.0", "project_id": "{project_id}", "assets": []}}', encoding="utf-8")

        test_bytes = b"\x00\x00\x00\x18ftypisom" + (b"\xee" * 160)
        full_hash = hashlib.sha256(test_bytes).hexdigest()

        mock_payload = DownloadedPayload(
            content_bytes=test_bytes,
            content_hash=full_hash,
            mime_type="video/mp4",
            file_size_bytes=len(test_bytes),
            suggested_extension=".mp4",
        )

        idemp_key = "idemp_crash_window_dedupe"
        repo = SQLIdempotencyRepository()
        canon_repo = CanonicalAssetRepository()

        # Clean slate
        with repo.db.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM tool_idempotency_records WHERE idempotency_key = ?", (idemp_key,))
            conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))

        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="usr_editor",
            roles=["editor"],
            permissions=["editor"],
            accessible_projects=[project_id],
        )

        req = CapabilityRequest(
            capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
            input={"project_id": project_id, "url": "https://example.com/crash_rec.mp4", "media_type": "video"},
            idempotency_key=idemp_key,
        )

        try:
            # 1. Worker 1 claims leadership in DB
            gw_1 = ToolGateway()
            req_hash = gw_1._compute_payload_hash(req.input)
            status, _ = repo.try_claim_leader(idemp_key, req_hash, lease_seconds=60.0)
            assert status == "LEADER"

            # 2. Worker 1 executes the real side effect
            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                from ai.acquisition.service import AssetAcquisitionService
                service_1 = AssetAcquisitionService()
                side_effect_res = await service_1.download_remote_media(
                    project_id, "https://example.com/crash_rec.mp4", "video"
                )
                assert side_effect_res.is_reused_existing is False
                assert side_effect_res.content_hash == full_hash

            # Verify side effect committed
            manifest_assets = AssetService.list_assets(project_id)
            assert len(manifest_assets) == 1
            canon_recs = canon_repo.list_by_project(project_id)
            assert len(canon_recs) == 1

            # 3. Simulate Worker 1 process dies BEFORE calling idempotency_store.complete!
            # The record remains IN_PROGRESS in the durable DB.
            record_before = repo.get_record(idemp_key)
            assert record_before["status"] == "IN_PROGRESS"
            assert record_before["result_json"] is None

            # 4. Lease expires (simulated by setting lease_expires_at to the past)
            with repo.db.transaction("IMMEDIATE") as conn:
                conn.execute(
                    "UPDATE tool_idempotency_records SET lease_expires_at = '2026-01-01T00:00:00Z' WHERE idempotency_key = ?",
                    (idemp_key,),
                )

            # 5. Second independent gateway (Worker 2) retries
            gw_2 = ToolGateway()
            with patch("ai.acquisition.service.safe_download_media", AsyncMock(return_value=mock_payload)):
                res_worker_2 = await gw_2.execute(req, context=ctx)

            assert res_worker_2.status == CapabilityStatus.SUCCESS
            assert res_worker_2.output_data["asset_id"] == f"ast_{full_hash}"

            # 6. Verify ZERO duplicate canonical mutations
            # Manifest still has strictly 1 asset
            manifest_after = AssetService.list_assets(project_id)
            assert len(manifest_after) == 1
            assert manifest_after[0]["asset_id"] == f"ast_{full_hash}"

            # Database still has strictly 1 canonical asset
            canon_after = canon_repo.list_by_project(project_id)
            assert len(canon_after) == 1
            assert canon_after[0].id == f"{project_id}:{full_hash}"

            # Idempotency record transitioned to COMPLETED
            record_after = repo.get_record(idemp_key)
            assert record_after["status"] == "COMPLETED"
            assert record_after["result_json"] is not None

            # 7. Subsequent retry immediately replays without re-execution
            gw_3 = ToolGateway()
            res_worker_3 = await gw_3.execute(req, context=ctx)
            assert res_worker_3.status == CapabilityStatus.SUCCESS
            assert res_worker_3.execution_metadata.get("idempotency_hit") is True
            assert len(AssetService.list_assets(project_id)) == 1
        finally:
            try:
                with repo.db.transaction("IMMEDIATE") as conn:
                    conn.execute("DELETE FROM tool_idempotency_records WHERE idempotency_key = ?", (idemp_key,))
                    conn.execute("DELETE FROM canonical_assets WHERE project_id = ?", (project_id,))
            except Exception:
                pass
            if proj_dir.exists():
                shutil.rmtree(proj_dir, ignore_errors=True)

