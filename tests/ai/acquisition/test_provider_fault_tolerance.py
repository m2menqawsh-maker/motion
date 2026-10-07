"""
Provider Fault Tolerance and Graceful Degradation Tests (S28-M05).
"""

from unittest.mock import AsyncMock, patch
import pytest

from ai.acquisition.contracts import (
    StockCandidate,
    StockMediaType,
    DownloadVariant,
    LicenseClassification,
    CommercialUseStatus,
    StockSearchQuery,
)
from ai.acquisition.errors import ProviderAuthError, ProviderUnavailableError
from ai.acquisition.providers.base import StockSourceAdapter
from ai.acquisition.providers.pexels import PexelsAdapter
from ai.acquisition.providers.pixabay import PixabayAdapter
from ai.acquisition.service import AssetAcquisitionService


class MockFailingAdapter(StockSourceAdapter):
    @property
    def name(self) -> str:
        return "failing_provider"

    @property
    def supported_media_types(self):
        return {StockMediaType.VIDEO}

    def is_available(self) -> bool:
        return True

    async def search(self, query: StockSearchQuery):
        raise ProviderUnavailableError(self.name, "Simulated 500 upstream server outage")

    def resolve_acquisition(self, candidate, requested_variant_id=None):
        raise NotImplementedError()


class MockHealthyAdapter(StockSourceAdapter):
    @property
    def name(self) -> str:
        return "healthy_provider"

    @property
    def supported_media_types(self):
        return {StockMediaType.VIDEO}

    def is_available(self) -> bool:
        return True

    async def search(self, query: StockSearchQuery):
        return [
            StockCandidate(
                candidate_id="healthy:999",
                source="healthy_provider",
                source_asset_id="999",
                media_type=StockMediaType.VIDEO,
                title="Healthy Provider Video",
                preview_url="https://healthy.example.com/prev.jpg",
                download_variants=[DownloadVariant(variant_id="hd", url="https://healthy.example.com/v.mp4")],
                selected_variant=DownloadVariant(variant_id="hd", url="https://healthy.example.com/v.mp4"),
                duration_seconds=12.0,
                license=LicenseClassification.PUBLIC_DOMAIN,
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                retrieved_at="2026-10-04T12:00:00Z",
            )
        ]

    def resolve_acquisition(self, candidate, requested_variant_id=None):
        raise NotImplementedError()


class TestFaultTolerance:
    """Verifies that individual provider failures do not crash the acquisition platform."""

    @pytest.mark.asyncio
    async def test_partial_outage_returns_healthy_results(self):
        """When one provider fails, results from healthy providers are still returned."""
        service = AssetAcquisitionService(
            providers=[MockFailingAdapter(), MockHealthyAdapter()]
        )
        query = StockSearchQuery(query="ocean", media_type=StockMediaType.VIDEO)

        results = await service.search(query)
        assert len(results) == 1
        assert results[0].candidate_id == "healthy:999"

    @pytest.mark.asyncio
    async def test_total_provider_outage_raises_structured_error(self):
        """When all providers fail, the service raises a structured ProviderUnavailableError."""
        service = AssetAcquisitionService(
            providers=[MockFailingAdapter()]
        )
        query = StockSearchQuery(query="ocean", media_type=StockMediaType.VIDEO)

        with pytest.raises(ProviderUnavailableError, match="All stock providers failed"):
            await service.search(query)

    def test_uncredentialed_provider_fails_closed(self):
        """Adapter with missing API key reports unavailable and raises ProviderAuthError."""
        adapter = PexelsAdapter()
        with patch.dict("os.environ", {}, clear=True):
            assert adapter.is_available() is False
            query = StockSearchQuery(query="sunset", media_type=StockMediaType.IMAGE)
            with pytest.raises(ProviderAuthError, match="PEXELS_API_KEY"):
                import asyncio
                asyncio.run(adapter.search(query))
