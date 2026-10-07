"""
tests/ai/speech/test_reconciliation.py
======================================
Tests for long-audio segmentation, timestamp shifting, boundary deduplication,
and speaker catalog reconciliation (S27.14 Rules 10, 11, 12, 13).
"""

import pytest

from ai.contracts.media import SpeechSegment, SpeechSpeaker, SpeechWord
from ai.speech.reconciliation import (
    AudioChunkPlan,
    deduplicate_boundary_words,
    plan_media_chunks,
    reconcile_chunk_transcripts,
    reconcile_speaker_catalog,
    shift_segment_timestamps,
    shift_word_timestamps,
)


def test_chunk_planning_short_media():
    # Short media under limit -> single chunk
    chunks = plan_media_chunks(total_duration_sec=45.0, max_chunk_sec=60.0)
    assert len(chunks) == 1
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 45.0
    assert chunks[0].overlap_sec == 0.0


def test_chunk_planning_long_media():
    # 130s media with 60s max chunk and 2s overlap
    chunks = plan_media_chunks(total_duration_sec=130.0, max_chunk_sec=60.0, overlap_sec=2.0)
    assert len(chunks) == 3
    # Chunk 0: [0.0, 60.0]
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 60.0
    # Chunk 1: [58.0, 118.0]
    assert chunks[1].start_sec == 58.0
    assert chunks[1].end_sec == 118.0
    assert chunks[1].overlap_sec == 2.0
    # Chunk 2: [116.0, 130.0]
    assert chunks[2].start_sec == 116.0
    assert chunks[2].end_sec == 130.0


def test_timestamp_shifting_relative_to_asset_start():
    """
    Mandatory Test (Rule 11):
    chunk 1: 0–60, chunk 2: 60–120. Word at second 5 of chunk 2 must become ~65 sec in final output.
    """
    chunk_words = [
        SpeechWord(text="world", start=5.0, end=5.8),
    ]

    shifted = shift_word_timestamps(chunk_words, offset_sec=60.0)

    assert len(shifted) == 1
    assert shifted[0].text == "world"
    assert shifted[0].start == 65.0
    assert shifted[0].end == 65.8


def test_boundary_deduplication_prevents_repetition():
    """
    Mandatory Test (Rule 12):
    Chunk A ends with '... hello' and Chunk B begins with 'hello world ...'.
    Must not become 'hello hello world' without reconciliation.
    """
    # Chunk A ends with 'hello' at 59.5 - 60.2
    words_a = [
        SpeechWord(text="say", start=58.0, end=58.5),
        SpeechWord(text="hello", start=59.5, end=60.2),
    ]

    # Chunk B starts with overlapping 'hello' at 59.8 - 60.5 and 'world' at 61.0 - 61.8
    words_b = [
        SpeechWord(text="hello", start=59.8, end=60.5),
        SpeechWord(text="world", start=61.0, end=61.8),
    ]

    kept_a, reconciled_b = deduplicate_boundary_words(words_a, words_b, boundary_time=60.0, temporal_window_sec=2.0)

    # Invariant: Duplicate 'hello' in Chunk B was dropped
    assert len(kept_a) == 2
    assert len(reconciled_b) == 1
    assert reconciled_b[0].text == "world"

    combined_text = " ".join(w.text for w in (kept_a + reconciled_b))
    assert combined_text == "say hello world"
    assert "hello hello" not in combined_text


def test_reconcile_chunk_transcripts_full_pipeline():
    plan_1 = AudioChunkPlan(chunk_index=0, start_sec=0.0, end_sec=60.0, overlap_sec=0.0)
    segs_1 = [SpeechSegment(start=0.0, end=5.0, text="الموبايل الي بايدك")]
    words_1 = [
        SpeechWord(text="الموبايل", start=0.0, end=1.5),
        SpeechWord(text="الي", start=1.6, end=2.5),
        SpeechWord(text="بايدك", start=2.6, end=5.0),
    ]

    plan_2 = AudioChunkPlan(chunk_index=1, start_sec=60.0, end_sec=120.0, overlap_sec=2.0)
    segs_2 = [SpeechSegment(start=5.0, end=10.0, text="أقوى من ناسا")]  # local to chunk
    words_2 = [
        SpeechWord(text="أقوى", start=5.0, end=6.5),  # 60 + 5.0 = 65.0s
        SpeechWord(text="من", start=6.6, end=7.5),
        SpeechWord(text="ناسا", start=7.6, end=10.0),
    ]

    full_transcript, reconciled_segs, reconciled_words = reconcile_chunk_transcripts([
        (plan_1, segs_1, words_1),
        (plan_2, segs_2, words_2),
    ])

    assert "الموبايل" in full_transcript
    assert "ناسا" in full_transcript

    # Word 'أقوى' was at local 5.0s in chunk 2; must now be at 65.0s
    aqwa_word = next(w for w in reconciled_words if w.text == "أقوى")
    assert aqwa_word.start == 65.0
    assert aqwa_word.end == 66.5


def test_reconcile_speaker_catalog():
    segs = [
        SpeechSegment(start=0.0, end=5.0, text="first turn", speaker_id="SPEAKER_00"),
        SpeechSegment(start=5.5, end=10.0, text="second turn", speaker_id="SPEAKER_01"),
        SpeechSegment(start=10.5, end=15.0, text="third turn", speaker_id="SPEAKER_00"),
    ]

    speakers = reconcile_speaker_catalog(segs, [])

    assert len(speakers) == 2
    spk_00 = next(s for s in speakers if s.speaker_id == "SPEAKER_00")
    spk_01 = next(s for s in speakers if s.speaker_id == "SPEAKER_01")

    # SPEAKER_00 spoke from 0-5 (5s) + 10.5-15 (4.5s) = 9.5s
    assert spk_00.total_speaking_time_seconds == 9.5
    # SPEAKER_01 spoke from 5.5-10 = 4.5s
    assert spk_01.total_speaking_time_seconds == 4.5
