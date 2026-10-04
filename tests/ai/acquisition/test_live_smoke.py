"""
Live Network Smoke Tests for Stock Media Providers (S28-M05).
Strictly separates LIVE_SMOKE_PASS (Iconify) from LIVE_SMOKE_BLOCKED (uncredentialed providers).
Zero fake success: uncredentialed providers fail closed with structured ProviderAuthError.
"""

import os
import pytest

from ai.acquisition.contracts import StockMediaType, StockSearchQuery
from ai.acquisition.errors import ProviderAuthError
from ai.acquisition.providers.freesound import FreesoundAdapter
from ai.acquisition.providers.iconify import IconifyAdapter
from ai.acquisition.providers.pexels import PexelsAdapter
from ai.acquisition.providers.pixabay import PixabayAdapter


class TestLiveSmokeAcquisition:
    """Live network verification of stock provider adapters."""

    @pytest.mark.asyncio
    async def test_live_smoke_iconify_public_api(self):
        """
        Iconify is a public open-source API with zero secret requirements.
        Live call must succeed (HTTP 200) and return normalized icon candidates.
        """
        adapter = IconifyAdapter()
        assert adapter.is_available() is True

        query = StockSearchQuery(
            query="home",
            media_type=StockMediaType.ICON,
            per_page=3,
        )

        candidates = await adapter.search(query)
        assert len(candidates) > 0, "Iconify search returned 0 candidates"
        c = candidates[0]
        assert c.source == "iconify"
        assert c.media_type == StockMediaType.ICON
        assert c.preview_url.startswith("https://api.iconify.design/")
        assert len(c.download_variants) > 0

    @pytest.mark.asyncio
    async def test_live_smoke_pexels_credentials_check(self):
        """
        Pexels requires PEXELS_API_KEY.
        If missing: LIVE_SMOKE_BLOCKED (must raise ProviderAuthError).
        If present: performs live query and validates candidates.
        """
        adapter = PexelsAdapter()
        api_key = os.environ.get("PEXELS_API_KEY")

        query = StockSearchQuery(
            query="nature landscape",
            media_type=StockMediaType.IMAGE,
            per_page=2,
        )

        if not api_key:
            # LIVE_SMOKE_BLOCKED: strictly verified fail-closed behavior
            assert adapter.is_available() is False
            with pytest.raises(ProviderAuthError, match="PEXELS_API_KEY"):
                await adapter.search(query)
        else:
            assert adapter.is_available() is True
            candidates = await adapter.search(query)
            assert len(candidates) > 0
            assert candidates[0].source == "pexels"

    @pytest.mark.asyncio
    async def test_live_smoke_pixabay_credentials_check(self):
        """
        Pixabay requires PIXABAY_API_KEY.
        If missing: LIVE_SMOKE_BLOCKED (must raise ProviderAuthError).
        If present: performs live query and validates candidates.
        """
        adapter = PixabayAdapter()
        api_key = os.environ.get("PIXABAY_API_KEY")

        query = StockSearchQuery(
            query="technology computer",
            media_type=StockMediaType.IMAGE,
            per_page=2,
        )

        if not api_key:
            # LIVE_SMOKE_BLOCKED: strictly verified fail-closed behavior
            assert adapter.is_available() is False
            with pytest.raises(ProviderAuthError, match="PIXABAY_API_KEY"):
                await adapter.search(query)
        else:
            assert adapter.is_available() is True
            candidates = await adapter.search(query)
            assert len(candidates) > 0
            assert candidates[0].source == "pixabay"

    @pytest.mark.asyncio
    async def test_live_smoke_freesound_credentials_check(self):
        """
        Freesound requires FREESOUND_API_KEY.
        If missing: LIVE_SMOKE_BLOCKED (must raise ProviderAuthError).
        If present: performs live query and validates candidates.
        """
        adapter = FreesoundAdapter()
        api_key = os.environ.get("FREESOUND_API_KEY")

        query = StockSearchQuery(
            query="cinematic whoosh",
            media_type=StockMediaType.SOUND_EFFECT,
            per_page=2,
        )

        if not api_key:
            # LIVE_SMOKE_BLOCKED: strictly verified fail-closed behavior
            assert adapter.is_available() is False
            with pytest.raises(ProviderAuthError, match="FREESOUND_API_KEY"):
                await adapter.search(query)
        else:
            assert adapter.is_available() is True
            candidates = await adapter.search(query)
            assert len(candidates) > 0
            assert candidates[0].source == "freesound"
