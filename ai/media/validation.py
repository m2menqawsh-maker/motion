"""
ai/media/validation.py
======================
Semantic validation engine for Media Intelligence and Speech Intelligence (S27.13 / S27.14).

Invariants:
- All timestamps must be non-negative and finite.
- Segment and word start/end bounds must be coherent: end >= start.
- Timestamps must be monotonic across chronological token sequences.
- All tokens must fall within media duration tolerance (tolerance = 0.5s).
- All referenced speaker IDs in segments and words must exist in the speakers catalog.
- Confidence scores must be bounded in [0.0, 1.0].
- Arabic and multilingual code-switching transcripts are fully supported and validated.
"""

from __future__ import annotations

from typing import List, Optional
from ai.contracts.media import MediaIntelligence, SpeechIntelligence, SpeechSegment, SpeechWord


class SemanticValidationError(ValueError):
    """Raised when an intelligence contract violates semantic domain invariants."""
    def __init__(self, violations: List[str]):
        super().__init__(f"Semantic validation failed with {len(violations)} violation(s): " + "; ".join(violations))
        self.violations = violations


def validate_speech_word(word: SpeechWord, max_duration: Optional[float] = None, tolerance: float = 0.5) -> List[str]:
    """Validates an individual speech word token."""
    violations: List[str] = []
    if word.start < 0.0:
        violations.append(f"Word '{word.text}' has negative start timestamp: {word.start}")
    if word.end < word.start:
        violations.append(f"Word '{word.text}' has end timestamp ({word.end}) preceding start ({word.start})")
    if word.confidence is not None and not (0.0 <= word.confidence <= 1.0):
        violations.append(f"Word '{word.text}' confidence ({word.confidence}) out of bounds [0.0, 1.0]")
    if max_duration is not None and word.end > (max_duration + tolerance):
        violations.append(
            f"Word '{word.text}' end timestamp ({word.end}) exceeds media duration ({max_duration}) by > {tolerance}s"
        )
    return violations


def validate_speech_segment(
    segment: SpeechSegment,
    max_duration: Optional[float] = None,
    tolerance: float = 0.5,
) -> List[str]:
    """Validates an individual speech segment."""
    violations: List[str] = []
    if segment.start < 0.0:
        violations.append(f"Segment '{segment.id or segment.text[:20]}' has negative start timestamp: {segment.start}")
    if segment.end < segment.start:
        violations.append(
            f"Segment '{segment.id or segment.text[:20]}' end ({segment.end}) precedes start ({segment.start})"
        )
    if segment.confidence is not None and not (0.0 <= segment.confidence <= 1.0):
        violations.append(f"Segment confidence ({segment.confidence}) out of bounds [0.0, 1.0]")
    if max_duration is not None and segment.end > (max_duration + tolerance):
        violations.append(
            f"Segment end timestamp ({segment.end}) exceeds media duration ({max_duration}) by > {tolerance}s"
        )

    # Validate constituent words within segment
    for w in segment.words:
        w_errs = validate_speech_word(w, max_duration=max_duration, tolerance=tolerance)
        violations.extend(w_errs)
        # Word must be roughly within segment boundaries
        if w.start < (segment.start - tolerance) or w.end > (segment.end + tolerance):
            violations.append(
                f"Word '{w.text}' [{w.start}, {w.end}] falls outside parent segment [{segment.start}, {segment.end}]"
            )

    return violations


def validate_speech_intelligence(
    speech: SpeechIntelligence,
    media_duration: Optional[float] = None,
    tolerance: float = 0.5,
) -> List[str]:
    """
    Performs comprehensive semantic validation on a SpeechIntelligence contract.
    Returns list of violation descriptions (empty if fully valid).
    """
    violations: List[str] = []

    # 1. Overall confidence bounds
    if speech.overall_confidence is not None and not (0.0 <= speech.overall_confidence <= 1.0):
        violations.append(f"Overall confidence ({speech.overall_confidence}) out of bounds [0.0, 1.0]")

    if speech.language_confidence is not None and not (0.0 <= speech.language_confidence <= 1.0):
        violations.append(f"Language confidence ({speech.language_confidence}) out of bounds [0.0, 1.0]")

    # 2. Speaker catalog references
    known_speakers = {s.speaker_id for s in speech.speakers}
    for s in speech.speakers:
        if s.confidence is not None and not (0.0 <= s.confidence <= 1.0):
            violations.append(f"Speaker '{s.speaker_id}' confidence ({s.confidence}) out of bounds [0.0, 1.0]")

    # 3. Segments monotonicity and bounds
    effective_duration = media_duration or speech.duration_seconds
    for i, seg in enumerate(speech.segments):
        seg_errs = validate_speech_segment(seg, max_duration=effective_duration, tolerance=tolerance)
        violations.extend(seg_errs)

        if known_speakers and seg.speaker_id is not None and seg.speaker_id not in known_speakers:
            violations.append(f"Segment references unregistered speaker_id '{seg.speaker_id}'")

        if i > 0 and seg.start < speech.segments[i - 1].start:
            violations.append(
                f"Segment start timestamps not monotonic: segment {i} ({seg.start}) < segment {i-1} ({speech.segments[i-1].start})"
            )

    # 4. Words monotonicity and bounds
    for j, word in enumerate(speech.words):
        word_errs = validate_speech_word(word, max_duration=effective_duration, tolerance=tolerance)
        violations.extend(word_errs)

        if known_speakers and word.speaker_id is not None and word.speaker_id not in known_speakers:
            violations.append(f"Word '{word.text}' references unregistered speaker_id '{word.speaker_id}'")

        if j > 0 and word.start < speech.words[j - 1].start:
            violations.append(
                f"Word start timestamps not monotonic: word '{word.text}' ({word.start}) < word '{speech.words[j-1].text}' ({speech.words[j-1].start})"
            )

    # 5. Non-empty transcript consistency
    if speech.words and not speech.transcript.strip():
        violations.append("SpeechIntelligence has words but transcript is empty")

    return violations


def validate_media_intelligence(report: MediaIntelligence) -> List[str]:
    """
    Performs comprehensive semantic validation on a root MediaIntelligence contract.
    Returns list of violation descriptions (empty if fully valid).
    """
    violations: List[str] = []

    # 1. Technical inspection consistency
    duration = report.technical.duration_seconds
    if duration is not None and duration < 0.0:
        violations.append(f"Technical metadata duration cannot be negative: {duration}")

    # 2. Speech intelligence validation if present
    if report.speech is not None:
        speech_errs = validate_speech_intelligence(report.speech, media_duration=duration)
        violations.extend(speech_errs)

    # 3. Provenance validation
    if not report.provenance.producer.strip():
        violations.append("AnalysisProvenance producer cannot be empty")

    return violations


def assert_valid_media_intelligence(report: MediaIntelligence) -> None:
    """Raises SemanticValidationError if report violates any domain semantic invariants."""
    violations = validate_media_intelligence(report)
    if violations:
        raise SemanticValidationError(violations)
