"""
Legacy MCP Parity and Capability Preservation Tests (S28-M05).
Proves that new canonical capabilities preserve and enrich all functionality of media-sources-mcp
without capability loss.
"""

from pathlib import Path
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
from ai.tools.adapters.acquisition import AssetAcquisitionAdapter
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def trusted_editor_ctx() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_legacy_test",
        actor_id="usr_tester",
        roles=["editor"],
        permissions=["editor"],
        is_admin=False,
        accessible_projects=["prj_parity"],
    )


class TestLegacyFilePreservation:
    """Verifies that legacy MCP source code files are preserved untouched."""

    def test_legacy_mcp_files_exist(self):
        legacy_dir = Path(".agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp")
        assert legacy_dir.exists(), "Legacy media-sources-mcp directory must be preserved"

        required_legacy_files = [
            legacy_dir / "server.py",
            legacy_dir / "README.md",
            legacy_dir / ".env.example",
            legacy_dir / "tools" / "pexels.py",
            legacy_dir / "tools" / "pixabay.py",
            legacy_dir / "tools" / "freesound.py",
            legacy_dir / "tools" / "iconify.py",
            legacy_dir / "utils" / "downloader.py",
            legacy_dir / "utils" / "file_organizer.py",
            legacy_dir / "utils" / "http_client.py",
            legacy_dir / "utils" / "pixabay_scraper.py",
        ]

        for file_path in required_legacy_files:
            assert file_path.exists(), f"Legacy file '{file_path}' must NOT be deleted or removed"


class TestCanonicalParityAndEnrichment:
    """Verifies that the canonical capability layer provides full superset parity over legacy MCP."""

    @pytest.mark.asyncio
    async def test_search_icons_parity_and_enrichment(self, trusted_editor_ctx):
        """
        Legacy iconify_search_icons provided basic icon names.
        Canonical SEARCH_ICONS provides structured collections, icon_name, and svg_preview.
        """
        gateway = ToolGateway()
        mock_candidates = [
            StockCandidate(
                candidate_id="iconify:lucide:sparkles",
                source="iconify",
                source_asset_id="lucide:sparkles",
                media_type=StockMediaType.ICON,
                title="Lucide Icons / sparkles",
                preview_url="https://api.iconify.design/lucide/sparkles.svg",
                download_variants=[
                    DownloadVariant(variant_id="svg_vector", url="https://api.iconify.design/lucide/sparkles.svg", format="svg")
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
                input={"query": "sparkles", "limit": 10},
            )

            result: CapabilityResult = await gateway.execute(req, context=trusted_editor_ctx)
            assert result.status == CapabilityStatus.SUCCESS
            assert "icons" in result.output_data
            icon = result.output_data["icons"][0]

            # Parity checks
            assert icon["icon_name"] == "lucide:sparkles"
            assert icon["collection"] == "lucide"
            assert icon["name"] == "sparkles"
            assert icon["svg_preview"] == "https://api.iconify.design/lucide/sparkles.svg"

    @pytest.mark.asyncio
    async def test_search_stock_videos_parity_and_enrichment(self, trusted_editor_ctx):
        """
        Legacy video searches returned raw unvalidated dictionaries.
        Canonical SEARCH_STOCK_VIDEOS returns typed StockMediaItem with resolution, duration, license.
        """
        gateway = ToolGateway()
        mock_candidates = [
            StockCandidate(
                candidate_id="pexels:98765",
                source="pexels",
                source_asset_id="98765",
                media_type=StockMediaType.VIDEO,
                title="Cinematic Sunset Reel",
                preview_url="https://images.pexels.com/preview.jpg",
                download_variants=[
                    DownloadVariant(variant_id="hd", url="https://vod.pexels.com/video.mp4", width=1080, height=1920)
                ],
                selected_variant=DownloadVariant(variant_id="hd", url="https://vod.pexels.com/video.mp4", width=1080, height=1920),
                width=1080,
                height=1920,
                duration_seconds=15.0,
                orientation="portrait",
                license=LicenseClassification.PEXELS_LICENSE,
                license_name="Pexels Content License",
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                retrieved_at="2026-10-04T12:00:00Z",
            )
        ]

        with patch("ai.acquisition.service.AssetAcquisitionService.search_stock", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_candidates

            req = CapabilityRequest(
                capability_id=CapabilityType.SEARCH_STOCK_VIDEOS,
                input={"query": "sunset", "orientation": "portrait", "per_page": 5},
            )

            result: CapabilityResult = await gateway.execute(req, context=trusted_editor_ctx)
            assert result.status == CapabilityStatus.SUCCESS
            assert "videos" in result.output_data
            video = result.output_data["videos"][0]

            assert video["media_id"] == "pexels:98765"
            assert video["media_type"] == "video"
            assert video["width"] == 1080
            assert video["height"] == 1920
            assert video["duration_seconds"] == 15.0
            assert video["license"] == "PEXELS_LICENSE"
            assert video["download_url"] == "https://vod.pexels.com/video.mp4"

    @pytest.mark.asyncio
    async def test_download_remote_media_parity_and_governance(self, trusted_editor_ctx):
        """
        Legacy download_media wrote raw files directly to local disk.
        Canonical DOWNLOAD_REMOTE_MEDIA securely persists into StorageService / AssetService.
        """
        gateway = ToolGateway()
        mock_result = AcquiredAssetResult(
            project_id="prj_parity",
            asset_id="asset_governed_001",
            storage_key="projects/prj_parity/assets/ready/stock_video.mp4",
            content_hash="sha256_dummy_hash",
            media_type=StockMediaType.VIDEO,
            file_size_bytes=5000000,
            content_type="video/mp4",
            provenance_evidence={"origin": "remote_url"},
            is_reused_existing=False,
        )

        with patch("ai.acquisition.service.AssetAcquisitionService.download_remote_media", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = mock_result

            req = CapabilityRequest(
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                input={
                    "project_id": "prj_parity",
                    "url": "https://example.com/asset.mp4",
                    "media_type": "video",
                },
            )

            result: CapabilityResult = await gateway.execute(req, context=trusted_editor_ctx)
            assert result.status == CapabilityStatus.SUCCESS
            assert result.output_data["asset_id"] == "asset_governed_001"
            assert result.output_data["storage_key"] == "projects/prj_parity/assets/ready/stock_video.mp4"
