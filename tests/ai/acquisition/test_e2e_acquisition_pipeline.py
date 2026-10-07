"""
End-to-End Acquisition Pipeline Tests (S28-M05).
Covers CreativePlan asset requirement parsing through safe download to AssetService registration.
"""

from unittest.mock import AsyncMock, patch
import pytest

from ai.acquisition.contracts import (
    AcquisitionDescriptor,
    DownloadVariant,
    LicenseClassification,
    CommercialUseStatus,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
    AcquiredAssetResult,
)
from ai.acquisition.providers.base import StockSourceAdapter
from ai.acquisition.safe_downloader import DownloadedPayload
from ai.acquisition.service import AssetAcquisitionService


class MockStockAdapter(StockSourceAdapter):
    @property
    def name(self) -> str:
        return "mock_stock"

    @property
    def supported_media_types(self):
        return {StockMediaType.VIDEO, StockMediaType.ICON}

    def is_available(self) -> bool:
        return True

    async def search(self, query: StockSearchQuery):
        return [
            StockCandidate(
                candidate_id="mock:100",
                source="mock_stock",
                source_asset_id="100",
                media_type=query.media_type,
                title="Bustling Modern Tech Office",
                preview_url="https://mock.example.com/prev.jpg",
                download_variants=[
                    DownloadVariant(variant_id="hd", url="https://mock.example.com/office.mp4", width=1080, height=1920)
                ],
                selected_variant=DownloadVariant(variant_id="hd", url="https://mock.example.com/office.mp4", width=1080, height=1920),
                width=1080,
                height=1920,
                duration_seconds=10.0,
                orientation="portrait",
                tags=["bustling", "modern", "tech", "office"],
                license=LicenseClassification.PUBLIC_DOMAIN,
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                retrieved_at="2026-10-04T12:00:00Z",
                provenance_evidence={"provider": "mock_stock", "id": "100"},
            )
        ]

    def resolve_acquisition(self, candidate, requested_variant_id=None):
        return AcquisitionDescriptor(
            candidate_id=candidate.candidate_id,
            source=candidate.source,
            source_asset_id=candidate.source_asset_id,
            download_url="https://mock.example.com/office.mp4",
            media_type=candidate.media_type,
            variant_id="hd",
            expected_mime_type="video/mp4",
            expected_format=".mp4",
            max_bytes=10 * 1024 * 1024,
            provenance=candidate.provenance_evidence,
        )


class TestCreativeRequirementParsing:
    """Verifies natural language requirement conversion into structured queries."""

    def test_parse_vertical_video_requirement(self):
        req = "Vertical 9:16 stock footage of bustling modern tech office"
        query = AssetAcquisitionService.parse_creative_asset_requirement(req)
        assert query.media_type == StockMediaType.VIDEO
        assert query.orientation == "portrait"
        assert "tech" in query.query
        assert "office" in query.query

    def test_parse_icon_requirement(self):
        req = "Icon of shopping cart checkout glyph"
        query = AssetAcquisitionService.parse_creative_asset_requirement(req)
        assert query.media_type == StockMediaType.ICON
        assert "shopping" in query.query

    def test_parse_sfx_requirement(self):
        req = "Foley whoosh sound effect for transition"
        query = AssetAcquisitionService.parse_creative_asset_requirement(req)
        assert query.media_type == StockMediaType.SOUND_EFFECT


class TestEndToEndPipeline:
    """Verifies pipeline execution from requirement to AssetService registration."""

    @pytest.fixture(autouse=True)
    def clean_db(self):
        from scripts.core.database import get_database_engine
        engine = get_database_engine()
        with engine.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM canonical_assets WHERE project_id = 'proj_demo'")
        yield
        with engine.transaction("IMMEDIATE") as conn:
            conn.execute("DELETE FROM canonical_assets WHERE project_id = 'proj_demo'")

    @pytest.mark.asyncio
    async def test_acquire_for_creative_requirement_e2e(self):
        service = AssetAcquisitionService(providers=[MockStockAdapter()])

        dummy_mp4_bytes = b"\x00\x00\x00\x18ftypisom" + b"video_data_sample"
        mock_payload = DownloadedPayload(
            content_bytes=dummy_mp4_bytes,
            content_hash="hash_tech_office_12345",
            mime_type="video/mp4",
            file_size_bytes=len(dummy_mp4_bytes),
            suggested_extension=".mp4",
        )

        mock_asset_rec = {
            "asset_id": "asset_stock_001",
            "kind": "video",
            "content_hash": "hash_tech_office_12345",
            "metadata": {
                "storage_key": "projects/proj_demo/assets/ready/mock_stock_100.mp4"
            },
        }

        with patch("ai.acquisition.service.safe_download_media", new_callable=AsyncMock) as mock_download, \
             patch("ai.acquisition.service.AssetService.upload_asset") as mock_upload, \
             patch("ai.acquisition.dedupe.AssetService.list_assets", return_value=[]):

            mock_download.return_value = mock_payload
            mock_upload.return_value = mock_asset_rec

            result: AcquiredAssetResult = await service.acquire_for_creative_requirement(
                requirement_text="Vertical 9:16 stock footage of bustling tech office",
                project_id="proj_demo",
            )

            assert isinstance(result, AcquiredAssetResult)
            assert result.project_id == "proj_demo"
            assert result.asset_id == "asset_stock_001"
            assert result.content_hash == "hash_tech_office_12345"
            assert result.media_type == StockMediaType.VIDEO
            assert result.is_reused_existing is False
            assert result.provenance_evidence.get("provider") == "mock_stock"

            # Verify AssetService upload was invoked with correct parameters
            mock_upload.assert_called_once()
            call_kwargs = mock_upload.call_args[1]
            assert call_kwargs["project_id"] == "proj_demo"
            assert call_kwargs["content"] == dummy_mp4_bytes
            assert "mock_stock_100.mp4" in call_kwargs["filename"]

    @pytest.mark.asyncio
    async def test_acquire_reusing_existing_asset_dedupe(self):
        service = AssetAcquisitionService(providers=[MockStockAdapter()])

        dummy_mp4_bytes = b"\x00\x00\x00\x18ftypisom" + b"video_data_sample"
        mock_payload = DownloadedPayload(
            content_bytes=dummy_mp4_bytes,
            content_hash="hash_tech_office_12345",
            mime_type="video/mp4",
            file_size_bytes=len(dummy_mp4_bytes),
            suggested_extension=".mp4",
        )

        existing_asset = {
            "asset_id": "asset_existing_999",
            "content_hash": "hash_tech_office_12345",
            "metadata": {"storage_key": "projects/proj_demo/assets/ready/existing.mp4"},
        }

        with patch("ai.acquisition.service.safe_download_media", new_callable=AsyncMock) as mock_download, \
             patch("ai.acquisition.service.AssetService.upload_asset") as mock_upload, \
             patch("ai.acquisition.dedupe.AssetService.list_assets", return_value=[existing_asset]):

            mock_download.return_value = mock_payload

            result: AcquiredAssetResult = await service.acquire_for_creative_requirement(
                requirement_text="Vertical 9:16 stock footage of bustling tech office",
                project_id="proj_demo",
            )

            assert result.is_reused_existing is True
            assert result.asset_id == "asset_existing_999"
            # AssetService upload should NOT be called because existing asset was reused!
            mock_upload.assert_not_called()
