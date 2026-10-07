"""
ai/speech/preparation.py
========================
Canonical SpeechPreparationService (S28-M07).

Invariants:
- Deterministic text and speech segmentation without external network dependencies.
- Handles multilingual text (Arabic, English, mixed), punctuation nuances, and speech constraints.
- Employs zero model ownership (delegates STT to ModelRouter and media execution to MediaProcessingService).
- Strictly bounded execution: handles empty text, whitespace, abbreviations, numbers, and long paragraphs.
- Outputs strongly-typed contracts conforming to AI platform architecture.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional

from ai.contracts.media_ops import (
    AlignAudioMetadataInput,
    AlignAudioMetadataOutput,
    AlignedSegmentItem,
    AlignedWordItem,
    PrepareVoSegmentsInput,
    PrepareVoSegmentsOutput,
    PreparedVoSegmentItem,
    SpeechTextSegmentItem,
    SplitSpeechTextInput,
    SplitSpeechTextOutput,
)

logger = logging.getLogger("ai.speech.preparation")

STRONG_PUNCTUATION = {'.', '!', '؟', '?', '…', '۔'}
WEAK_PUNCTUATION = {',', '،', ';', '؛', ':'}
ALL_SPLIT_PUNCTUATION = STRONG_PUNCTUATION.union(WEAK_PUNCTUATION)

# Common abbreviations in EN and AR to prevent false sentence breaks
ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "etc.", "vs.", "e.g.", "i.e.",
    "u.s.", "u.k.", "u.a.e.", "st.", "ave.", "approx.", "dept.",
    "د.", "أ.", "م.", "إلخ", "ش.م.", "ج.م."
}


def get_punctuation_strength(token: str) -> int:
    """Returns 2 for strong terminal punctuation, 1 for weak pause punctuation, 0 otherwise."""
    cleaned = token.strip()
    if not cleaned:
        return 0
    # Check last character
    last_char = cleaned[-1]
    if last_char in STRONG_PUNCTUATION:
        # Check if entire token is an abbreviation (e.g. 'Dr.', 'etc.')
        if cleaned.lower() in ABBREVIATIONS:
            return 0
        return 2
    if last_char in WEAK_PUNCTUATION:
        return 1
    return 0


def detect_dominant_language(text: str) -> str:
    """Determines dominant language (Arabic 'ar' vs English/Latin 'en') based on script frequency."""
    arabic_chars = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text))
    latin_chars = len(re.findall(r"[a-zA-Z]", text))
    if arabic_chars > latin_chars:
        return "ar"
    return "en"


class SpeechPreparationService:
    """
    Canonical domain service governing speech text preparation, segmentation,
    and voiceover metadata alignment.
    """

    @classmethod
    def split_speech_text(
        cls,
        req: Optional[SplitSpeechTextInput] = None,
        **kwargs: Any,
    ) -> SplitSpeechTextOutput:
        """
        Deterministically segments speech text into typed sentence segments.
        Respects punctuation boundaries, duration constraints, and word limits.
        """
        if req is None:
            req = SplitSpeechTextInput(**kwargs)
        raw_text = req.text.strip()
        if not raw_text:
            return SplitSpeechTextOutput(
                segments=[],
                total_segments=0,
                total_words=0,
                language=req.language or "en",
            )

        detected_lang = req.language or detect_dominant_language(raw_text)

        # Tokenize by whitespace into words
        words = raw_text.split()
        if not words or not any(c.isalnum() for c in raw_text):
            return SplitSpeechTextOutput(
                segments=[],
                total_segments=0,
                total_words=0,
                language=detected_lang,
            )

        # Average speaking rate estimate: ~2.5 words per second
        est_words_per_sec = 2.5
        min_words = max(1, int(req.min_sentence_duration * est_words_per_sec))
        max_words = max(min_words + 1, int(req.max_sentence_duration * est_words_per_sec))

        segments: List[SpeechTextSegmentItem] = []
        current_segment_words: List[str] = []

        for idx, word in enumerate(words):
            current_segment_words.append(word)
            punct_strength = get_punctuation_strength(word)
            word_count = len(current_segment_words)
            is_last = idx == len(words) - 1

            split_reason: Optional[str] = None

            if is_last:
                split_reason = "end_of_text"
            elif word_count >= max_words:
                split_reason = "duration_limit"
            elif punct_strength == 2 and word_count >= min_words:
                split_reason = "strong_punctuation"
            elif punct_strength == 1 and word_count >= (min_words * 1.5):
                split_reason = "weak_punctuation"

            if split_reason:
                seg_text = " ".join(current_segment_words)
                seg_idx = len(segments) + 1
                est_duration = round(word_count / est_words_per_sec, 2)
                segments.append(
                    SpeechTextSegmentItem(
                        index=seg_idx,
                        text=seg_text,
                        duration_seconds=est_duration,
                        split_reason=split_reason,
                        word_count=word_count,
                    )
                )
                current_segment_words = []

        # If any lingering words remain
        if current_segment_words:
            seg_text = " ".join(current_segment_words)
            word_count = len(current_segment_words)
            est_duration = round(word_count / est_words_per_sec, 2)
            segments.append(
                SpeechTextSegmentItem(
                    index=len(segments) + 1,
                    text=seg_text,
                    duration_seconds=est_duration,
                    split_reason="end_of_text",
                    word_count=word_count,
                )
            )

        return SplitSpeechTextOutput(
            segments=segments,
            total_segments=len(segments),
            total_words=len(words),
            language=detected_lang,
        )

    @classmethod
    def split_timestamped_words(
        cls,
        words: List[Dict[str, Any]],
        min_sentence_duration: float = 2.0,
        max_sentence_duration: float = 10.0,
        silence_threshold: float = 0.30,
    ) -> List[Dict[str, Any]]:
        """
        Deterministically segments a sequence of timestamped words into sentences
        based on punctuation, silence intervals, and duration bounds.
        """
        if not words:
            return []

        sentences_raw: List[Dict[str, Any]] = []
        current_words: List[Dict[str, Any]] = []

        total_words = len(words)
        word_index = 0

        while word_index < total_words:
            word = words[word_index]
            current_words.append(word)

            is_last_word = word_index == total_words - 1
            next_word = words[word_index + 1] if not is_last_word else None

            w_start = float(word.get("start", 0.0))
            w_end = float(word.get("end", w_start))
            curr_start = float(current_words[0].get("start", 0.0))
            curr_duration = w_end - curr_start

            gap_to_next = (float(next_word.get("start", 0.0)) - w_end) if next_word else float("inf")
            punct_level = get_punctuation_strength(str(word.get("word") or word.get("text", "")))
            is_long_silence = gap_to_next > silence_threshold
            is_segment_end = bool(word.get("is_segment_end", False))

            split_reason: Optional[str] = None

            if is_last_word:
                split_reason = "end_of_file"
            elif curr_duration > max_sentence_duration:
                split_reason = "duration_limit"
            else:
                if punct_level == 2 and gap_to_next > 0.1:
                    split_reason = "strong_punctuation"
                elif is_segment_end and curr_duration >= min_sentence_duration:
                    split_reason = "whisper_segment_end"
                elif curr_duration >= min_sentence_duration:
                    if is_long_silence and punct_level > 0:
                        split_reason = "silence_and_punctuation"
                    elif is_long_silence:
                        split_reason = "silence"
                    elif punct_level == 2:
                        split_reason = "strong_punctuation"

            if split_reason == "duration_limit":
                # Backtrack to find the best internal break
                best_idx = -1
                best_score = -1

                for i in range(len(current_words) - 1):
                    cw = current_words[i]
                    nw = current_words[i + 1]
                    cg = float(nw.get("start", 0.0)) - float(cw.get("end", 0.0))
                    cp = get_punctuation_strength(str(cw.get("word") or cw.get("text", "")))

                    score = 0
                    if cw.get("is_segment_end", False):
                        score += 50
                    if cg > silence_threshold:
                        score += 10
                    score += cp * 3
                    if cg > 0.1:
                        score += 1

                    if score >= best_score:
                        best_score = score
                        best_idx = i

                if best_idx != -1 and best_score > 0:
                    split_w = current_words[: best_idx + 1]
                    rem_w = current_words[best_idx + 1 :]
                    cw = split_w[-1]
                    nw = rem_w[0]
                    cg = float(nw.get("start", 0.0)) - float(cw.get("end", 0.0))
                    cp = get_punctuation_strength(str(cw.get("word") or cw.get("text", "")))

                    if cg > silence_threshold:
                        s_reason = "max_duration_backtrack_silence"
                    elif cp > 0:
                        s_reason = "max_duration_backtrack_punctuation"
                    else:
                        s_reason = "max_duration_fallback"

                    sentences_raw.append({"words": split_w, "reason": s_reason})
                    current_words = rem_w
                else:
                    if len(current_words) > 1:
                        split_w = current_words[:-1]
                        rem_w = [current_words[-1]]
                        sentences_raw.append({"words": split_w, "reason": "duration_limit_forced"})
                        current_words = rem_w
                    else:
                        sentences_raw.append({"words": current_words, "reason": "duration_limit_forced_single_word"})
                        current_words = []
            elif split_reason:
                sentences_raw.append({"words": list(current_words), "reason": split_reason})
                current_words = []

            word_index += 1

        # Format compiled sentences
        result_sentences: List[Dict[str, Any]] = []
        for idx, sent in enumerate(sentences_raw):
            sw = sent["words"]
            r_start = float(sw[0].get("start", 0.0))
            r_end = float(sw[-1].get("end", r_start))
            text_tokens = [str(w.get("word") or w.get("text", "")).strip() for w in sw]
            sent_text = " ".join([t for t in text_tokens if t])

            gap_prev = 0.0
            if idx > 0:
                prev_end = float(sentences_raw[idx - 1]["words"][-1].get("end", 0.0))
                gap_prev = max(0.0, r_start - prev_end)

            result_sentences.append({
                "index": idx + 1,
                "text": sent_text,
                "split_reason": sent["reason"],
                "start": round(r_start, 3),
                "end": round(r_end, 3),
                "duration": round(r_end - r_start, 3),
                "source_timing": {
                    "start": round(r_start, 3),
                    "end": round(r_end, 3),
                    "duration": round(r_end - r_start, 3),
                },
                "inter_sentence_gap": round(gap_prev, 3),
                "words": sw,
            })

        return result_sentences

    @classmethod
    def prepare_vo_segments(
        cls,
        req: Optional[PrepareVoSegmentsInput] = None,
        **kwargs: Any,
    ) -> PrepareVoSegmentsOutput:
        """
        Constructs a structured voiceover segment plan from text segments,
        calculating speaking rate adjustments and audio mode tags.
        """
        if req is None:
            req = PrepareVoSegmentsInput(**kwargs)

        words_per_sec = 2.5 * req.speaking_rate
        prepared: List[PreparedVoSegmentItem] = []
        total_est_duration = 0.0

        for i, text in enumerate(req.text_segments):
            clean_text = text.strip()
            word_count = len(clean_text.split())
            dur = max(0.5, round(word_count / words_per_sec, 2)) if word_count > 0 else 0.5
            total_est_duration += dur

            prepared.append(
                PreparedVoSegmentItem(
                    segment_id=f"vo_seg_{i+1:03d}",
                    index=i + 1,
                    text=clean_text,
                    estimated_duration_seconds=dur,
                    voice_id=req.voice_id,
                    audio_mode=req.audio_mode,
                )
            )

        return PrepareVoSegmentsOutput(
            project_id=req.project_id,
            segments=prepared,
            total_segments=len(prepared),
            total_estimated_duration_seconds=round(total_est_duration, 2),
            audio_mode=req.audio_mode,
        )

    @classmethod
    def align_audio_metadata(
        cls,
        req: Optional[AlignAudioMetadataInput] = None,
        **kwargs: Any,
    ) -> AlignAudioMetadataOutput:
        """
        Validates and aligns timestamped words with source audio duration,
        ensuring monotonic chronology and non-overlapping intervals.
        """
        if req is None:
            raw_words = kwargs.get("words", [])
            norm_words = []
            for w in raw_words:
                if isinstance(w, dict):
                    s = float(w.get("start_seconds", w.get("start", 0.0)))
                    e = float(w.get("end_seconds", w.get("end", s)))
                    dur = float(w.get("duration_seconds", w.get("duration", max(0.0, e - s))))
                    conf = w.get("confidence")
                    norm_words.append(
                        AlignedWordItem(
                            word=str(w.get("word", "")),
                            start_seconds=round(s, 3),
                            end_seconds=round(e, 3),
                            duration_seconds=round(dur, 3),
                            confidence=float(conf) if conf is not None else None,
                        )
                    )
                elif isinstance(w, AlignedWordItem):
                    norm_words.append(w)
            kwargs["words"] = norm_words
            req = AlignAudioMetadataInput(**kwargs)

        if not req.words:
            return AlignAudioMetadataOutput(
                project_id=req.project_id,
                segments=[],
                total_words=0,
                covered_duration_seconds=0.0,
                audio_duration_seconds=req.audio_duration_seconds,
                coverage_ratio=0.0,
                is_valid=True,
            )

        # Validate monotonic timestamps
        is_valid = True
        prev_end = 0.0
        covered_duration = 0.0

        for w in req.words:
            if w.start_seconds < prev_end - 0.05:  # Tolerance threshold
                is_valid = False
            if w.end_seconds > req.audio_duration_seconds + 0.1:
                is_valid = False
            prev_end = max(prev_end, w.end_seconds)
            covered_duration += max(0.0, w.duration_seconds)

        # Segment words into sentences
        raw_words_dict = [
            {"word": w.word, "start": w.start_seconds, "end": w.end_seconds, "confidence": w.confidence}
            for w in req.words
        ]
        split_results = cls.split_timestamped_words(raw_words_dict)

        aligned_segments: List[AlignedSegmentItem] = []
        for s in split_results:
            seg_words = [
                AlignedWordItem(
                    word=str(w["word"]),
                    start_seconds=float(w["start"]),
                    end_seconds=float(w["end"]),
                    duration_seconds=round(float(w["end"]) - float(w["start"]), 3),
                    confidence=w.get("confidence"),
                )
                for w in s["words"]
            ]
            aligned_segments.append(
                AlignedSegmentItem(
                    segment_id=f"seg_{s['index']:03d}",
                    index=s["index"],
                    text=s["text"],
                    start_seconds=s["source_timing"]["start"],
                    end_seconds=s["source_timing"]["end"],
                    duration_seconds=s["source_timing"]["duration"],
                    words=seg_words,
                )
            )

        cov_ratio = min(1.0, max(0.0, covered_duration / req.audio_duration_seconds)) if req.audio_duration_seconds > 0 else 0.0

        return AlignAudioMetadataOutput(
            project_id=req.project_id,
            segments=aligned_segments,
            total_words=len(req.words),
            covered_duration_seconds=round(covered_duration, 3),
            audio_duration_seconds=req.audio_duration_seconds,
            coverage_ratio=round(cov_ratio, 4),
            is_valid=is_valid,
        )
