"""
ai/speech/reconciliation.py
===========================
Long-media segmentation, timestamp alignment, and boundary reconciliation (S27.13 / S27.14).

Invariants:
- All final timestamps are globally relative to original asset start (never relative to chunk 0.0).
- Monotonic timestamps across chunk boundaries.
- Boundary deduplication: overlapping chunk segments do not produce duplicate words/tokens.
- Neutral speaker identity preservation (SPEAKER_00, SPEAKER_01).
- Arabic and multilingual code-switching tokens are fully supported during merge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ai.contracts.media import SpeechSegment, SpeechSpeaker, SpeechWord


@dataclass(frozen=True)
class AudioChunkPlan:
    """Specification of an individual chunk segment of a long media track."""
    chunk_index: int
    start_sec: float
    end_sec: float
    overlap_sec: float

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


def plan_media_chunks(
    total_duration_sec: float,
    max_chunk_sec: float = 60.0,
    overlap_sec: float = 2.0,
) -> List[AudioChunkPlan]:
    """
    Plans chronological media chunks for long-audio transcription.
    If total_duration <= max_chunk_sec, returns a single chunk [0.0, total_duration].
    """
    if total_duration_sec <= 0.0:
        return []

    if total_duration_sec <= max_chunk_sec:
        return [AudioChunkPlan(chunk_index=0, start_sec=0.0, end_sec=total_duration_sec, overlap_sec=0.0)]

    chunks: List[AudioChunkPlan] = []
    current_start = 0.0
    index = 0

    while current_start < total_duration_sec:
        current_end = min(current_start + max_chunk_sec, total_duration_sec)
        actual_overlap = overlap_sec if current_start > 0.0 else 0.0
        chunks.append(
            AudioChunkPlan(
                chunk_index=index,
                start_sec=current_start,
                end_sec=current_end,
                overlap_sec=actual_overlap,
            )
        )
        if current_end >= total_duration_sec:
            break
        # Next start accounts for overlap
        current_start = current_end - overlap_sec
        index += 1

    return chunks


def shift_word_timestamps(words: List[SpeechWord], offset_sec: float) -> List[SpeechWord]:
    """Shifts all word timestamps by a global offset in seconds."""
    if offset_sec == 0.0:
        return words

    shifted: List[SpeechWord] = []
    for w in words:
        shifted.append(
            SpeechWord(
                text=w.text,
                start=round(w.start + offset_sec, 3),
                end=round(w.end + offset_sec, 3),
                speaker_id=w.speaker_id,
                confidence=w.confidence,
                language=w.language,
            )
        )
    return shifted


def shift_segment_timestamps(segments: List[SpeechSegment], offset_sec: float) -> List[SpeechSegment]:
    """Shifts all segment and constituent word timestamps by a global offset in seconds."""
    if offset_sec == 0.0:
        return segments

    shifted: List[SpeechSegment] = []
    for seg in segments:
        shifted_words = shift_word_timestamps(seg.words, offset_sec)
        shifted.append(
            SpeechSegment(
                id=seg.id,
                start=round(seg.start + offset_sec, 3),
                end=round(seg.end + offset_sec, 3),
                text=seg.text,
                speaker_id=seg.speaker_id,
                confidence=seg.confidence,
                language=seg.language,
                words=shifted_words,
            )
        )
    return shifted


def _normalize_token_for_comparison(token: str) -> str:
    """Strips punctuation and whitespace for fuzzy duplicate token detection."""
    cleaned = re.sub(r"[^\w\s]", "", token, flags=re.UNICODE).strip().lower()
    return cleaned


def deduplicate_boundary_words(
    words_a: List[SpeechWord],
    words_b: List[SpeechWord],
    boundary_time: float,
    temporal_window_sec: float = 2.5,
) -> Tuple[List[SpeechWord], List[SpeechWord]]:
    """
    Deduplicates words appearing in both chunk A and chunk B within the overlap boundary window.
    If chunk A ends with token X and chunk B starts with token X near boundary_time,
    the duplicate token in chunk B is omitted.
    """
    if not words_a or not words_b:
        return words_a, words_b

    # Find words in words_a that occur near boundary_time
    recent_a = [
        (idx, w) for idx, w in enumerate(words_a)
        if abs(w.end - boundary_time) <= temporal_window_sec or w.start >= (boundary_time - temporal_window_sec)
    ]
    if not recent_a:
        return words_a, words_b

    # Find candidate duplicate words in words_b near boundary_time
    words_b_filtered = list(words_b)
    skip_b_indices = set()

    for idx_b, wb in enumerate(words_b):
        if wb.start > (boundary_time + temporal_window_sec):
            break  # Past the overlap window

        norm_b = _normalize_token_for_comparison(wb.text)
        if not norm_b:
            continue

        for _, wa in recent_a:
            norm_a = _normalize_token_for_comparison(wa.text)
            if norm_a == norm_b and abs(wa.start - wb.start) <= temporal_window_sec:
                skip_b_indices.add(idx_b)
                break

    reconciled_b = [wb for idx, wb in enumerate(words_b_filtered) if idx not in skip_b_indices]
    return words_a, reconciled_b


def reconcile_chunk_transcripts(
    chunk_results: List[Tuple[AudioChunkPlan, List[SpeechSegment], List[SpeechWord]]],
) -> Tuple[str, List[SpeechSegment], List[SpeechWord]]:
    """
    Reconciles, shifts, deduplicates, and assembles multi-chunk speech recognition outputs
    into a globally consistent transcript, segment list, and word sequence.
    """
    if not chunk_results:
        return "", [], []

    all_segments: List[SpeechSegment] = []
    all_words: List[SpeechWord] = []

    for plan, segments, words in chunk_results:
        offset = plan.start_sec
        shifted_segs = shift_segment_timestamps(segments, offset)
        shifted_words = shift_word_timestamps(words, offset)

        if not all_words:
            all_words.extend(shifted_words)
            all_segments.extend(shifted_segs)
        else:
            boundary = plan.start_sec
            _, reconciled_words = deduplicate_boundary_words(
                all_words,
                shifted_words,
                boundary_time=boundary,
                temporal_window_sec=plan.overlap_sec + 1.0,
            )
            all_words.extend(reconciled_words)

            # Filter out overlapping segments if their words were entirely deduplicated
            # or if segment text directly duplicates the prior segment text
            if shifted_segs:
                for seg in shifted_segs:
                    norm_seg = _normalize_token_for_comparison(seg.text)
                    if all_segments:
                        prior_norm = _normalize_token_for_comparison(all_segments[-1].text)
                        if norm_seg == prior_norm and abs(seg.start - all_segments[-1].start) <= (plan.overlap_sec + 1.0):
                            continue
                    all_segments.append(seg)

    # Sort and ensure strict monotonicity
    all_words.sort(key=lambda w: (w.start, w.end))
    all_segments.sort(key=lambda s: (s.start, s.end))

    # Construct unified transcript
    full_transcript = " ".join(w.text for w in all_words) if all_words else " ".join(s.text for s in all_segments)

    return full_transcript, all_segments, all_words


def reconcile_speaker_catalog(
    segments: List[SpeechSegment],
    words: List[SpeechWord],
    candidate_speakers: Optional[List[SpeechSpeaker]] = None,
) -> List[SpeechSpeaker]:
    """
    Extracts and normalizes unique speakers referenced across reconciled segments and words.
    Computes total speaking time per speaker.
    """
    speaker_times: dict[str, float] = {}

    for seg in segments:
        if seg.speaker_id:
            dur = max(0.0, seg.end - seg.start)
            speaker_times[seg.speaker_id] = speaker_times.get(seg.speaker_id, 0.0) + dur

    if not speaker_times:
        for w in words:
            if w.speaker_id:
                dur = max(0.0, w.end - w.start)
                speaker_times[w.speaker_id] = speaker_times.get(w.speaker_id, 0.0) + dur

    known_speakers = {s.speaker_id: s for s in (candidate_speakers or [])}

    result: List[SpeechSpeaker] = []
    for spk_id in sorted(speaker_times.keys()):
        existing = known_speakers.get(spk_id)
        label = existing.label if existing else None
        conf = existing.confidence if existing else 0.95
        total_time = round(speaker_times[spk_id], 3)
        result.append(
            SpeechSpeaker(
                speaker_id=spk_id,
                label=label,
                confidence=conf,
                total_speaking_time_seconds=total_time,
            )
        )

    return result
