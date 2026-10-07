"""
tests/ai/audio_modernization/test_voiceover_manifest_and_timeline.py
===================================================================
Test suite for canonical SpeechManifestBuilder and SpeechTimelineBuilder (S28-M07).
Validates chronology, word coverage, zero-start, gap/overlap constraints, and DomainServiceAdapter execution.
"""

import json
from pathlib import Path
import pytest

from ai.contracts import CapabilityRequest, CapabilityType
from ai.contracts.media_ops import (
    SpeechManifestInput,
    SpeechTimelineInput,
)
from ai.speech.manifest import SpeechManifestBuilder
from ai.speech.timeline import SpeechTimelineBuilder
from ai.tools.adapters.domain_service import DomainServiceAdapter
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def sample_analysis():
    return {
        "duration": 5.0,
        "sample_rate": 44100,
        "channels": 2,
        "language": "en",
        "words": [
            {"word": "Welcome", "start": 0.0, "end": 0.8},
            {"word": "to", "start": 0.9, "end": 1.1},
            {"word": "our", "start": 1.2, "end": 1.5},
            {"word": "show.", "start": 1.6, "end": 2.2},
            {"word": "Enjoy.", "start": 3.0, "end": 4.5},
        ],
        "silence_periods": [
            {"start": 2.2, "end": 3.0},
            {"start": 4.5, "end": 5.0},
        ],
    }


@pytest.fixture
def sample_split_sentences():
    return [
        {
            "index": 1,
            "text": "Welcome to our show.",
            "source_timing": {"start": 0.0, "end": 2.2, "duration": 2.2},
            "words": [
                {"word": "Welcome", "start": 0.0, "end": 0.8},
                {"word": "to", "start": 0.9, "end": 1.1},
                {"word": "our", "start": 1.2, "end": 1.5},
                {"word": "show.", "start": 1.6, "end": 2.2},
            ],
        },
        {
            "index": 2,
            "text": "Enjoy.",
            "source_timing": {"start": 3.0, "end": 4.5, "duration": 1.5},
            "words": [
                {"word": "Enjoy.", "start": 3.0, "end": 4.5},
            ],
        },
    ]


@pytest.fixture
def trusted_context():
    return TrustedToolExecutionContext(
        workspace_id="ws_audio_qc",
        actor_id="usr_audio_qc",
        roles=["editor"],
        permissions=["editor", "viewer"],
    )


class TestVoiceoverManifestAndTimeline:
    """Test suite for SpeechManifestBuilder and SpeechTimelineBuilder."""

    def test_build_manifest_success_and_validation(
        self,
        sample_analysis,
        sample_split_sentences,
        tmp_path,
    ):
        out_file = tmp_path / "manifest.json"
        manifest = SpeechManifestBuilder.build_manifest(
            project_id="prj_test_vo",
            audio_key_or_path="audio/intro.wav",
            analysis_data=sample_analysis,
            split_sentences=sample_split_sentences,
            output_path=str(out_file),
        )

        assert manifest["success"] is True
        assert manifest["manifest_type"] == "voiceover_manifest"
        assert manifest["project_id"] == "prj_test_vo"
        assert manifest["statistics"]["sentence_count"] == 2
        assert manifest["statistics"]["word_count"] == 5
        assert len(manifest["sentences"]) == 2
        assert len(manifest["unmapped_intervals"]) >= 1

        assert manifest["statistics"]["sentence_count"] == 2

    def test_build_manifest_overlap_detected(self, sample_analysis):
        overlapping_sentences = [
            {
                "index": 1,
                "text": "Sentence one.",
                "source_timing": {"start": 0.0, "end": 2.5, "duration": 2.5},
                "words": [],
            },
            {
                "index": 2,
                "text": "Sentence two.",
                "source_timing": {"start": 2.0, "end": 4.0, "duration": 2.0},  # Overlaps at 2.0 < 2.5
                "words": [],
            },
        ]
        manifest = SpeechManifestBuilder.build_manifest(
            project_id="prj_overlap",
            audio_key_or_path="audio/overlap.wav",
            analysis_data=sample_analysis,
            split_sentences=overlapping_sentences,
        )
        assert manifest["success"] is False
        assert manifest["validation"]["checks"]["no_overlap"] is False
        assert any(w["code"] == "OVERLAP_DETECTED" for w in manifest["validation"]["warnings"])

    def test_build_timeline_success(
        self,
        sample_analysis,
        sample_split_sentences,
        tmp_path,
    ):
        manifest = SpeechManifestBuilder.build_manifest(
            project_id="prj_timeline",
            audio_key_or_path="audio/intro.wav",
            analysis_data=sample_analysis,
            split_sentences=sample_split_sentences,
        )

        out_timeline_file = tmp_path / "timeline.json"
        timeline = SpeechTimelineBuilder.build_timeline(
            manifest_data=manifest,
            fps=30.0,
            output_path=str(out_timeline_file),
        )

        assert timeline["success"] is True
        assert timeline["type"] == "voiceover_timeline"
        assert timeline["source"]["fps"] == 30.0
        assert timeline["source"]["total_frames"] == int(5.0 * 30.0)

        # Check events
        assert len(timeline["events"]) >= 2
        assert len(timeline["words"]) == 5
        assert len(timeline["sentences"]) == 2

    def test_build_timeline_gap_or_overlap_reporting(self):
        # Manifest with gap between sentences that isn't classified
        manifest_data = {
            "project_id": "prj_gap",
            "source": {"duration": 5.0, "audio_path": "audio/test.wav"},
            "sentences": [
                {
                    "id": "vo_001",
                    "text": "Sentence 1",
                    "timing": {"source_start": 0.5, "source_end": 2.0, "source_duration": 1.5},
                    "words": [],
                },
                {
                    "id": "vo_002",
                    "text": "Sentence 2",
                    "timing": {"source_start": 2.5, "source_end": 4.5, "source_duration": 2.0},
                    "words": [],
                },
            ],
            "unmapped_intervals": [],
        }

        timeline = SpeechTimelineBuilder.build_timeline(manifest_data=manifest_data, fps=30.0)
        # Should flag timeline does not start at zero or has gaps
        checks = timeline["validation"]["checks"]
        assert checks["timeline_starts_at_zero"] is False or checks["no_gaps"] is False

    @pytest.mark.asyncio
    async def test_domain_service_adapter_speech_manifest_and_timeline(self, trusted_context):
        adapter = DomainServiceAdapter()

        # 1. Execute GENERATE_SPEECH_MANIFEST
        req_manifest = CapabilityRequest(
            capability_id=CapabilityType.GENERATE_SPEECH_MANIFEST,
            workspace_id="ws_audio_qc",
            project_id="prj_audio_qc",
            input={
                "project_id": "prj_audio_qc",
                "audio_storage_key": "storage/prj/audio.wav",
            },
        )
        val_manifest = SpeechManifestInput(
            project_id="prj_audio_qc",
            audio_storage_key="storage/prj/audio.wav",
        )
        out_manifest = await adapter.execute(req_manifest, val_manifest, trusted_context)
        assert out_manifest["project_id"] == "prj_audio_qc"
        assert "manifest_storage_key" in out_manifest
        assert out_manifest["sentence_count"] >= 0

        # 2. Execute BUILD_SPEECH_TIMELINE
        req_timeline = CapabilityRequest(
            capability_id=CapabilityType.BUILD_SPEECH_TIMELINE,
            workspace_id="ws_audio_qc",
            project_id="prj_audio_qc",
            input={
                "project_id": "prj_audio_qc",
                "audio_storage_key": "storage/prj/audio.wav",
                "fps": 30.0,
            },
        )
        val_timeline = SpeechTimelineInput(
            project_id="prj_audio_qc",
            audio_storage_key="storage/prj/audio.wav",
            fps=30.0,
        )
        out_timeline = await adapter.execute(req_timeline, val_timeline, trusted_context)
        assert out_timeline["project_id"] == "prj_audio_qc"
        assert "timeline_storage_key" in out_timeline
        assert out_timeline["total_frames"] > 0
        assert "cue_points_count" in out_timeline
