"""
Tests for Stock Media Filtering, Ranking, and Deterministic Selection (S28-M05).
"""

import pytest
from ai.acquisition.contracts import (
    StockMediaType,
    LicenseClassification,
    CommercialUseStatus,
    DownloadVariant,
    StockCandidate,
    StockSearchQuery,
)
from ai.acquisition.filtering import StockFilterEngine
from ai.acquisition.ranking import StockRankingEngine


def _make_candidate(
    source="pexels",
    source_asset_id="1",
    media_type=StockMediaType.VIDEO,
    title="Sample Candidate",
    width=1080,
    height=1920,
    duration=10.0,
    commercial_use=CommercialUseStatus.ALLOWED,
    attribution_required=False,
    tags=None,
    provider_score=100.0,
) -> StockCandidate:
    orientation = "portrait" if (height and width and height > width) else "landscape"
    return StockCandidate(
        candidate_id=f"{source}:{source_asset_id}",
        source=source,
        source_asset_id=source_asset_id,
        media_type=media_type,
        title=title,
        preview_url="https://example.com/prev.jpg",
        download_variants=[
            DownloadVariant(variant_id="hd", url="https://example.com/v.mp4", width=width, height=height)
        ],
        width=width,
        height=height,
        duration_seconds=duration,
        license=LicenseClassification.PUBLIC_DOMAIN,
        license_name="Test License",
        commercial_use=commercial_use,
        attribution_required=attribution_required,
        creator="Test Creator",
        source_reference="https://example.com/asset/1",
        query="test",
        retrieved_at="2026-10-04T12:00:00Z",
        provenance_evidence={"provider": source},
        orientation=orientation,
        tags=tags or [],
        provider_score=provider_score,
    )


class TestHardFiltering:
    """Verifies that hard constraints eliminate incompatible candidates before ranking."""

    def test_media_type_filter(self):
        query = StockSearchQuery(query="nature", media_type=StockMediaType.VIDEO)
        c_video = _make_candidate(source_asset_id="1", media_type=StockMediaType.VIDEO)
        c_image = _make_candidate(source_asset_id="2", media_type=StockMediaType.IMAGE)

        filtered, stats = StockFilterEngine.filter_candidates([c_video, c_image], query)
        assert len(filtered) == 1
        assert filtered[0].source_asset_id == "1"
        assert stats["media_type_mismatch"] == 1

    def test_orientation_filter(self):
        query = StockSearchQuery(query="nature", media_type=StockMediaType.VIDEO, orientation="portrait")
        c_portrait = _make_candidate(source_asset_id="1", width=1080, height=1920)
        c_landscape = _make_candidate(source_asset_id="2", width=1920, height=1080)

        filtered, stats = StockFilterEngine.filter_candidates([c_portrait, c_landscape], query)
        assert len(filtered) == 1
        assert filtered[0].source_asset_id == "1"
        assert stats["orientation_mismatch"] == 1

    def test_dimension_filter(self):
        query = StockSearchQuery(query="nature", media_type=StockMediaType.VIDEO, min_width=1080, min_height=1920)
        c_hd = _make_candidate(source_asset_id="1", width=1080, height=1920)
        c_sd = _make_candidate(source_asset_id="2", width=540, height=960)

        filtered, stats = StockFilterEngine.filter_candidates([c_hd, c_sd], query)
        assert len(filtered) == 1
        assert filtered[0].source_asset_id == "1"
        assert stats["min_dimensions_violated"] == 1

    def test_duration_filter(self):
        query = StockSearchQuery(
            query="audio",
            media_type=StockMediaType.AUDIO,
            min_duration=3.0,
            max_duration=10.0,
        )
        c_short = _make_candidate(source_asset_id="1", duration=1.5, media_type=StockMediaType.AUDIO)
        c_good = _make_candidate(source_asset_id="2", duration=5.0, media_type=StockMediaType.AUDIO)
        c_long = _make_candidate(source_asset_id="3", duration=45.0, media_type=StockMediaType.AUDIO)

        filtered, stats = StockFilterEngine.filter_candidates([c_short, c_good, c_long], query)
        assert len(filtered) == 1
        assert filtered[0].source_asset_id == "2"
        assert stats["duration_out_of_bounds"] == 2

    def test_commercial_use_filter(self):
        query = StockSearchQuery(query="music", media_type=StockMediaType.AUDIO, commercial_use_required=True)
        c_comm = _make_candidate(source_asset_id="1", media_type=StockMediaType.AUDIO, commercial_use=CommercialUseStatus.ALLOWED)
        c_non_comm = _make_candidate(source_asset_id="2", media_type=StockMediaType.AUDIO, commercial_use=CommercialUseStatus.PROHIBITED)

        filtered, stats = StockFilterEngine.filter_candidates([c_comm, c_non_comm], query)
        assert len(filtered) == 1
        assert filtered[0].source_asset_id == "1"
        assert stats["commercial_use_prohibited"] == 1

    def test_attribution_filter(self):
        query = StockSearchQuery(query="icon", media_type=StockMediaType.ICON, require_no_attribution=True)
        c_no_attr = _make_candidate(source_asset_id="1", media_type=StockMediaType.ICON, attribution_required=False)
        c_attr = _make_candidate(source_asset_id="2", media_type=StockMediaType.ICON, attribution_required=True)

        filtered, stats = StockFilterEngine.filter_candidates([c_no_attr, c_attr], query)
        assert len(filtered) == 1
        assert filtered[0].source_asset_id == "1"
        assert stats["attribution_unacceptable"] == 1


class TestRankingAndScoring:
    """Verifies deterministic ranking and explainable feature breakdowns."""

    def test_case_a_vertical_video_ranking(self):
        """Case A: Vertical video request must reject landscape candidates and rank best match first."""
        query = StockSearchQuery(
            query="city aerial neon",
            media_type=StockMediaType.VIDEO,
            orientation="portrait",
            min_width=1080,
            min_height=1920,
        )

        c1 = _make_candidate(
            source_asset_id="1",
            title="City Aerial Neon Lights at Night",
            width=1080,
            height=1920,
            tags=["city", "aerial", "neon"],
        )
        c2 = _make_candidate(
            source_asset_id="2",
            title="Daytime Park Walk",
            width=1080,
            height=1920,
            tags=["park", "daytime"],
        )
        c_landscape = _make_candidate(
            source_asset_id="3",
            title="City Aerial Neon Panorama",
            width=3840,
            height=2160,
            tags=["city", "aerial", "neon"],
        )

        filtered, _ = StockFilterEngine.filter_candidates([c1, c2, c_landscape], query)
        assert len(filtered) == 2
        assert c_landscape not in filtered

        ranked = StockRankingEngine.rank_candidates(filtered, query)
        assert ranked[0].source_asset_id == "1"
        assert ranked[0].ranking_features["relevance"] > ranked[1].ranking_features["relevance"]
        assert ranked[0].ranking_score > ranked[1].ranking_score

    def test_case_b_audio_sfx_duration_fit(self):
        """Case B: SFX request prefers candidate matching target duration."""
        query = StockSearchQuery(
            query="whoosh transition",
            media_type=StockMediaType.SOUND_EFFECT,
            min_duration=1.0,
            max_duration=5.0,
        )

        c_ideal = _make_candidate(
            source_asset_id="1",
            media_type=StockMediaType.SOUND_EFFECT,
            title="Fast Whoosh Transition",
            duration=3.0,
            tags=["whoosh", "transition"],
        )
        c_acceptable = _make_candidate(
            source_asset_id="2",
            media_type=StockMediaType.SOUND_EFFECT,
            title="Long Ambient Whoosh Sweep",
            duration=4.9,
            tags=["whoosh", "transition"],
        )

        filtered, _ = StockFilterEngine.filter_candidates([c_ideal, c_acceptable], query)
        ranked = StockRankingEngine.rank_candidates(filtered, query)
        assert ranked[0].source_asset_id == "1"
        assert ranked[0].ranking_features["duration"] >= ranked[1].ranking_features["duration"]

    def test_case_c_icon_keyword_match(self):
        """Case C: Icon search with specific keyword match."""
        query = StockSearchQuery(
            query="shopping cart checkout",
            media_type=StockMediaType.ICON,
        )

        c_exact = _make_candidate(
            source_asset_id="1",
            media_type=StockMediaType.ICON,
            title="shopping cart checkout",
            tags=["shopping", "cart", "checkout"],
        )
        c_generic = _make_candidate(
            source_asset_id="2",
            media_type=StockMediaType.ICON,
            title="arrow right next",
            tags=["arrow", "next"],
        )

        filtered, _ = StockFilterEngine.filter_candidates([c_exact, c_generic], query)
        ranked = StockRankingEngine.rank_candidates(filtered, query)
        assert ranked[0].source_asset_id == "1"
        assert ranked[0].ranking_features["relevance"] > ranked[1].ranking_features["relevance"]
