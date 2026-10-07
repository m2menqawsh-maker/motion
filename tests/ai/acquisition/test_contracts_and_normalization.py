"""
Tests for Stock Media Contracts and Provider Result Normalization (S28-M05).
"""

import pytest
from ai.acquisition.contracts import (
    StockMediaType,
    LicenseClassification,
    CommercialUseStatus,
    DownloadVariant,
    StockCandidate,
    StockSearchQuery,
    AcquisitionDescriptor,
    AcquiredAssetResult,
)
from ai.acquisition.providers.pexels import PexelsAdapter
from ai.acquisition.providers.pixabay import PixabayAdapter
from ai.acquisition.providers.freesound import FreesoundAdapter
from ai.acquisition.providers.iconify import IconifyAdapter


class TestContractsSerialization:
    """Verifies pydantic serialization and type preservation."""

    def test_stock_candidate_dump(self):
        candidate = StockCandidate(
            candidate_id="pexels:12345",
            source="pexels",
            source_asset_id="12345",
            media_type=StockMediaType.IMAGE,
            title="Sunny Beach",
            preview_url="https://images.pexels.com/preview.jpg",
            download_variants=[
                DownloadVariant(
                    variant_id="large",
                    url="https://images.pexels.com/large.jpg",
                    width=1920,
                    height=1080,
                    format="jpg",
                )
            ],
            width=1920,
            height=1080,
            duration_seconds=None,
            license=LicenseClassification.PEXELS_LICENSE,
            license_name="Pexels Content License",
            commercial_use=CommercialUseStatus.ALLOWED,
            attribution_required=False,
            creator="Photographer Name",
            source_reference="https://www.pexels.com/photo/12345",
            query="beach",
            retrieved_at="2026-10-04T12:00:00Z",
            provenance_evidence={"provider": "pexels", "id": "12345"},
            mime_type="image/jpeg",
            orientation="landscape",
            tags=["beach", "sunny", "ocean"],
            provider_score=0.95,
        )

        data = candidate.model_dump()
        assert data["candidate_id"] == "pexels:12345"
        assert data["source"] == "pexels"
        assert data["media_type"] == StockMediaType.IMAGE
        assert data["commercial_use"] == CommercialUseStatus.ALLOWED
        assert len(data["download_variants"]) == 1
        assert data["download_variants"][0]["variant_id"] == "large"
        assert data["orientation"] == "landscape"

    def test_acquisition_descriptor_dump(self):
        descriptor = AcquisitionDescriptor(
            candidate_id="pexels:12345",
            source="pexels",
            source_asset_id="12345",
            download_url="https://images.pexels.com/large.jpg",
            media_type=StockMediaType.IMAGE,
            variant_id="large",
            expected_mime_type="image/jpeg",
            expected_format=".jpg",
            max_bytes=10 * 1024 * 1024,
            provenance={"provider": "pexels", "query": "beach"},
        )

        data = descriptor.model_dump()
        assert data["download_url"] == "https://images.pexels.com/large.jpg"
        assert data["media_type"] == StockMediaType.IMAGE
        assert data["max_bytes"] == 10 * 1024 * 1024


class TestPexelsNormalization:
    """Verifies Pexels raw payload normalization to canonical StockCandidate."""

    def test_normalize_photo(self):
        adapter = PexelsAdapter(api_key="mock_key")
        raw_photo = {
            "id": 2014445,
            "width": 3000,
            "height": 2000,
            "url": "https://www.pexels.com/photo/rock-formation-2014445/",
            "photographer": "Jane Doe",
            "photographer_url": "https://www.pexels.com/@janedoe",
            "alt": "Rock Formation under Blue Sky",
            "src": {
                "original": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg",
                "large": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
                "medium": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg?auto=compress&cs=tinysrgb&h=350",
                "small": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg?auto=compress&cs=tinysrgb&h=130",
                "portrait": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=1200&w=800",
                "landscape": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=627&w=1200",
                "tiny": "https://images.pexels.com/photos/2014445/pexels-photo-2014445.jpeg?auto=compress&cs=tinysrgb&dpr=1&fit=crop&h=200&w=280",
            },
        }

        candidates = adapter._normalize_photos([raw_photo], query="nature", timestamp="2026-10-04T12:00:00Z")
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.source == "pexels"
        assert candidate.source_asset_id == "2014445"
        assert candidate.media_type == StockMediaType.IMAGE
        assert candidate.title == "Rock Formation under Blue Sky"
        assert candidate.creator == "Jane Doe"
        assert candidate.width == 3000
        assert candidate.height == 2000
        assert candidate.orientation == "landscape"
        assert candidate.commercial_use == CommercialUseStatus.ALLOWED
        assert candidate.attribution_required is False
        assert candidate.license_name == "Pexels Content License"
        assert len(candidate.download_variants) > 0

    def test_normalize_video(self):
        adapter = PexelsAdapter(api_key="mock_key")
        raw_video = {
            "id": 854999,
            "width": 1080,
            "height": 1920,
            "duration": 15,
            "url": "https://www.pexels.com/video/854999/",
            "user": {"name": "Video Creator", "url": "https://www.pexels.com/@videocreator"},
            "image": "https://images.pexels.com/videos/854999/preview.jpg",
            "video_files": [
                {
                    "id": 1,
                    "quality": "hd",
                    "file_type": "video/mp4",
                    "width": 1080,
                    "height": 1920,
                    "fps": 30.0,
                    "link": "https://vod-progressive.akamaized.net/exp=1/video-1080p.mp4",
                },
                {
                    "id": 2,
                    "quality": "sd",
                    "file_type": "video/mp4",
                    "width": 540,
                    "height": 960,
                    "fps": 30.0,
                    "link": "https://vod-progressive.akamaized.net/exp=1/video-540p.mp4",
                },
            ],
            "video_pictures": [{"picture": "https://images.pexels.com/videos/854999/preview.jpg"}],
        }

        candidates = adapter._normalize_videos([raw_video], query="vertical reel", timestamp="2026-10-04T12:00:00Z")
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.source == "pexels"
        assert candidate.source_asset_id == "854999"
        assert candidate.media_type == StockMediaType.VIDEO
        assert candidate.duration_seconds == 15.0
        assert candidate.orientation == "portrait"
        assert candidate.width == 1080
        assert candidate.height == 1920
        assert len(candidate.download_variants) == 2


class TestPixabayNormalization:
    """Verifies Pixabay raw payload normalization to canonical StockCandidate."""

    def test_normalize_image(self):
        adapter = PixabayAdapter(api_key="mock_key")
        raw_hit = {
            "id": 4825366,
            "pageURL": "https://pixabay.com/photos/mountains-4825366/",
            "type": "photo",
            "tags": "mountains, sunset, landscape",
            "previewURL": "https://cdn.pixabay.com/photo/preview.jpg",
            "webformatURL": "https://pixabay.com/photo/webformat.jpg",
            "webformatWidth": 640,
            "webformatHeight": 426,
            "largeImageURL": "https://pixabay.com/photo/large.jpg",
            "imageWidth": 4000,
            "imageHeight": 2666,
            "imageSize": 2500000,
            "views": 15000,
            "downloads": 4000,
            "likes": 250,
            "user": "NatureLover",
        }

        candidates = adapter._normalize_images([raw_hit], query="mountains", timestamp="2026-10-04T12:00:00Z")
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.source == "pixabay"
        assert candidate.source_asset_id == "4825366"
        assert candidate.media_type == StockMediaType.IMAGE
        assert "mountains" in candidate.title
        assert candidate.creator == "NatureLover"
        assert candidate.width == 4000
        assert candidate.height == 2666
        assert candidate.orientation == "landscape"
        assert candidate.commercial_use == CommercialUseStatus.ALLOWED
        assert candidate.attribution_required is False
        assert candidate.license_name == "Pixabay Content License"
        assert "mountains" in candidate.tags

    def test_normalize_video(self):
        adapter = PixabayAdapter(api_key="mock_key")
        raw_video_hit = {
            "id": 123456,
            "pageURL": "https://pixabay.com/videos/waterfall-123456/",
            "type": "film",
            "tags": "waterfall, river, nature",
            "duration": 22,
            "videos": {
                "large": {"url": "https://cdn.pixabay.com/video/large.mp4", "width": 1920, "height": 1080, "size": 15000000},
                "medium": {"url": "https://cdn.pixabay.com/video/medium.mp4", "width": 1280, "height": 720, "size": 8000000},
                "tiny": {"url": "https://cdn.pixabay.com/video/tiny.mp4", "width": 640, "height": 360, "size": 2000000},
            },
            "user": "VideoPro",
        }

        candidates = adapter._normalize_videos([raw_video_hit], query="waterfall", timestamp="2026-10-04T12:00:00Z")
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.source == "pixabay"
        assert candidate.source_asset_id == "123456"
        assert candidate.media_type == StockMediaType.VIDEO
        assert candidate.duration_seconds == 22.0
        assert candidate.width == 1920
        assert candidate.height == 1080
        assert len(candidate.download_variants) == 3


class TestFreesoundNormalization:
    """Verifies Freesound sound normalization and license detection."""

    def test_normalize_cc0_sound(self):
        adapter = FreesoundAdapter(api_key="mock_key")
        raw_sound = {
            "id": 998877,
            "name": "Cinematic Whoosh",
            "tags": ["whoosh", "transition", "cinematic"],
            "description": "Fast air whoosh effect",
            "created": "2025-01-01T10:00:00Z",
            "license": "http://creativecommons.org/publicdomain/zero/1.0/",
            "type": "wav",
            "duration": 2.5,
            "bitrate": 1411,
            "samplerate": 44100,
            "filesize": 441000,
            "username": "SoundArtist",
            "url": "https://freesound.org/people/SoundArtist/sounds/998877/",
            "previews": {
                "preview-hq-mp3": "https://freesound.org/data/previews/998877/preview.mp3",
                "preview-hq-ogg": "https://freesound.org/data/previews/998877/preview.ogg",
            },
            "download": "https://freesound.org/apiv2/sounds/998877/download/",
            "avg_rating": 4.8,
            "num_ratings": 35,
        }

        candidates = adapter._normalize_sounds([raw_sound], query="whoosh", timestamp="2026-10-04T12:00:00Z")
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.source == "freesound"
        assert candidate.source_asset_id == "998877"
        assert candidate.media_type == StockMediaType.SOUND_EFFECT
        assert candidate.duration_seconds == 2.5
        assert candidate.license == LicenseClassification.CC0
        assert candidate.commercial_use == CommercialUseStatus.ALLOWED
        assert candidate.attribution_required is False

    def test_normalize_cc_by_nc_sound(self):
        adapter = FreesoundAdapter(api_key="mock_key")
        raw_sound = {
            "id": 112233,
            "name": "Non-commercial Music Loop",
            "tags": ["ambient", "loop"],
            "license": "https://creativecommons.org/licenses/by-nc/4.0/",
            "duration": 30.0,
            "username": "Composer",
            "url": "https://freesound.org/sounds/112233/",
            "previews": {"preview-hq-mp3": "https://freesound.org/preview.mp3"},
            "download": "https://freesound.org/download/",
        }

        candidates = adapter._normalize_sounds([raw_sound], query="music", timestamp="2026-10-04T12:00:00Z")
        assert len(candidates) == 1
        candidate = candidates[0]

        assert candidate.license == LicenseClassification.CC_BY_NC
        assert candidate.commercial_use == CommercialUseStatus.PROHIBITED
        assert candidate.attribution_required is True

    def test_normalize_cc_by_sa_sound_requires_review(self):
        adapter = FreesoundAdapter(api_key="mock_key")
        raw_sound = {
            "id": 445566,
            "name": "ShareAlike Effect",
            "license": "https://creativecommons.org/licenses/by-sa/4.0/",
            "duration": 5.0,
            "username": "CopyleftSound",
            "previews": {"preview-hq-mp3": "https://freesound.org/preview.mp3"},
        }
        candidates = adapter._normalize_sounds([raw_sound], query="effect", timestamp="2026-10-04T12:00:00Z")
        assert candidates[0].commercial_use == CommercialUseStatus.REQUIRES_REVIEW
        assert candidates[0].attribution_required is True

    def test_normalize_missing_license_sound_requires_review(self):
        adapter = FreesoundAdapter(api_key="mock_key")
        raw_sound = {
            "id": 778899,
            "name": "Unspecified License Sound",
            "license": "",
            "duration": 4.0,
            "username": "MysteryUser",
            "previews": {"preview-hq-mp3": "https://freesound.org/preview.mp3"},
        }
        candidates = adapter._normalize_sounds([raw_sound], query="test", timestamp="2026-10-04T12:00:00Z")
        assert candidates[0].commercial_use == CommercialUseStatus.REQUIRES_REVIEW
        assert candidates[0].license == LicenseClassification.UNKNOWN


class TestIconifyNormalization:
    """Verifies Iconify SVG icon normalization and truthful licensing."""

    def test_normalize_icon_permissive_license(self):
        adapter = IconifyAdapter()
        candidate = adapter._normalize_icon(
            prefix="mdi",
            icon_name="check-circle",
            query="check",
            timestamp="2026-10-04T12:00:00Z",
            col_meta={
                "name": "Material Design Icons",
                "category": "General",
                "license": {"title": "Apache 2.0", "spdx": "Apache-2.0"},
            },
        )

        assert candidate.source == "iconify"
        assert candidate.source_asset_id == "mdi:check-circle"
        assert candidate.media_type == StockMediaType.ICON
        assert candidate.commercial_use == CommercialUseStatus.ALLOWED
        assert len(candidate.download_variants) == 1
        assert "mdi/check-circle.svg" in candidate.download_variants[0].url

    def test_normalize_icon_missing_license_requires_review(self):
        adapter = IconifyAdapter()
        candidate = adapter._normalize_icon(
            prefix="custom",
            icon_name="unknown-icon",
            query="icon",
            timestamp="2026-10-04T12:00:00Z",
            col_meta={"name": "No License Set"},
        )
        assert candidate.license == LicenseClassification.UNKNOWN
        assert candidate.commercial_use == CommercialUseStatus.REQUIRES_REVIEW
        assert candidate.attribution_required is True

    def test_normalize_icon_non_commercial_prohibited(self):
        adapter = IconifyAdapter()
        candidate = adapter._normalize_icon(
            prefix="nc-set",
            icon_name="personal-use",
            query="icon",
            timestamp="2026-10-04T12:00:00Z",
            col_meta={
                "name": "Personal Icon Pack",
                "license": {"title": "Creative Commons Non-Commercial", "spdx": "CC-BY-NC-4.0"},
            },
        )
        assert candidate.license == LicenseClassification.CC_BY_NC
        assert candidate.commercial_use == CommercialUseStatus.PROHIBITED
        assert candidate.attribution_required is True

    def test_normalize_icon_copyleft_requires_review(self):
        adapter = IconifyAdapter()
        candidate = adapter._normalize_icon(
            prefix="gpl-set",
            icon_name="copyleft-icon",
            query="icon",
            timestamp="2026-10-04T12:00:00Z",
            col_meta={
                "name": "GPL Icon Set",
                "license": {"title": "GPL 3.0", "spdx": "GPL-3.0"},
            },
        )
        assert candidate.commercial_use == CommercialUseStatus.REQUIRES_REVIEW
        assert candidate.attribution_required is True
