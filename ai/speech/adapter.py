"""
ai/speech/adapter.py
====================
Provider-neutral speech recognition adapter layer (S27.13 / S27.14).

Invariants:
- All speech providers normalize into the single canonical SpeechIntelligence contract.
- Domain Services must never import concrete provider wire APIs.
- Supports SPEECH_TO_TEXT, LANGUAGE_DETECTION, DIARIZATION, and SPEECH_ALIGNMENT capabilities.
- Demonstrates seamless swappability between diverse wire schemas (e.g. Provider A vs Provider B).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import JsonValue

from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, PrivacyRequirement, ProvenanceRecord
from ai.contracts.media import (
    AnalysisProvenance,
    SpeechIntelligence,
    SpeechQuality,
    SpeechSegment,
    SpeechSpeaker,
    SpeechWord,
)
from ai.contracts.usage import UsageRecord
from ai.providers.base import AIProvider, ProviderDefinition
from ai.speech.reconciliation import reconcile_speaker_catalog


class SpeechProviderAdapter(ABC):
    """
    Abstract adapter translating raw provider wire payloads into canonical SpeechIntelligence.
    """

    @abstractmethod
    def canonicalize_speech_output(
        self,
        raw_output: Dict[str, JsonValue],
        provenance: AnalysisProvenance,
    ) -> SpeechIntelligence:
        """Transforms provider-specific payload into canonical SpeechIntelligence contract."""
        raise NotImplementedError


# =============================================================================
# Provider A (Whisper-Style Wire Format Simulation)
# =============================================================================

class WhisperStyleAdapter(SpeechProviderAdapter):
    """
    Adapter for providers returning Whisper-like JSON schemas:
    {
      "text": "...",
      "language": "ar",
      "language_probability": 0.99,
      "segments": [
        {"start": 0.0, "end": 1.5, "text": "...", "speaker": "SPEAKER_00", "confidence": 0.98,
         "words": [{"word": "...", "start": 0.0, "end": 0.5, "confidence": 0.99, "speaker": "SPEAKER_00"}]}
      ]
    }
    """

    def canonicalize_speech_output(
        self,
        raw_output: Dict[str, JsonValue],
        provenance: AnalysisProvenance,
    ) -> SpeechIntelligence:
        transcript = str(raw_output.get("text", "")).strip()
        language = raw_output.get("language")
        lang_str = str(language) if language is not None else None
        lang_conf_val = raw_output.get("language_probability") or raw_output.get("language_confidence")
        lang_conf = float(lang_conf_val) if lang_conf_val is not None else None

        raw_segments = raw_output.get("segments", [])
        segments: List[SpeechSegment] = []
        words: List[SpeechWord] = []

        if isinstance(raw_segments, list):
            for i, seg in enumerate(raw_segments):
                if isinstance(seg, dict):
                    start = float(seg.get("start", 0.0))
                    end = float(seg.get("end", start))
                    text = str(seg.get("text", "")).strip()
                    spk = seg.get("speaker") or seg.get("speaker_id")
                    spk_id = str(spk) if spk is not None else None
                    conf_val = seg.get("confidence")
                    conf = float(conf_val) if conf_val is not None else None

                    seg_words: List[SpeechWord] = []
                    raw_words = seg.get("words", [])
                    if isinstance(raw_words, list):
                        for rw in raw_words:
                            if isinstance(rw, dict):
                                w_start = float(rw.get("start", start))
                                w_end = float(rw.get("end", w_start))
                                w_text = str(rw.get("word") or rw.get("text", "")).strip()
                                w_spk = rw.get("speaker") or rw.get("speaker_id") or spk_id
                                w_conf_val = rw.get("confidence")
                                w_conf = float(w_conf_val) if w_conf_val is not None else None
                                if w_text:
                                    w_obj = SpeechWord(
                                        text=w_text,
                                        start=w_start,
                                        end=w_end,
                                        speaker_id=str(w_spk) if w_spk is not None else None,
                                        confidence=w_conf,
                                        language=lang_str,
                                    )
                                    seg_words.append(w_obj)
                                    words.append(w_obj)

                    segments.append(
                        SpeechSegment(
                            id=f"seg_{i:03d}",
                            start=start,
                            end=end,
                            text=text,
                            speaker_id=spk_id,
                            confidence=conf,
                            language=lang_str,
                            words=seg_words,
                        )
                    )

        # Fallback if no words inside segments but top-level words exist
        if not words and isinstance(raw_output.get("words"), list):
            for rw in raw_output["words"]:  # type: ignore
                if isinstance(rw, dict):
                    w_start = float(rw.get("start", 0.0))
                    w_end = float(rw.get("end", w_start))
                    w_text = str(rw.get("word") or rw.get("text", "")).strip()
                    w_spk = rw.get("speaker") or rw.get("speaker_id")
                    if w_text:
                        words.append(
                            SpeechWord(
                                text=w_text,
                                start=w_start,
                                end=w_end,
                                speaker_id=str(w_spk) if w_spk is not None else None,
                                language=lang_str,
                            )
                        )

        # Extract speakers
        speakers = reconcile_speaker_catalog(segments, words)

        # Duration
        dur_val = raw_output.get("duration")
        duration = float(dur_val) if dur_val is not None else (words[-1].end if words else None)

        overall_conf = float(raw_output.get("overall_confidence", 0.95))

        return SpeechIntelligence(
            language=lang_str,
            language_confidence=lang_conf,
            transcript=transcript,
            segments=segments,
            words=words,
            speakers=speakers,
            duration_seconds=duration,
            overall_confidence=overall_conf,
            provenance=provenance,
        )


# =============================================================================
# Provider B (Google STT-Style Wire Format Simulation)
# =============================================================================

class GoogleStyleAdapter(SpeechProviderAdapter):
    """
    Adapter for providers returning alternative nested JSON schemas:
    {
      "results": [
        {
          "languageCode": "ar-XA",
          "alternatives": [
            {
              "transcript": "...",
              "confidence": 0.98,
              "words": [
                {"word": "...", "startTime": "0.0s", "endTime": "0.5s", "speakerTag": 1}
              ]
            }
          ]
        }
      ]
    }
    """

    def _parse_time_str(self, val: Any) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            clean = val.rstrip("s").strip()
            return float(clean) if clean else 0.0
        return 0.0

    def canonicalize_speech_output(
        self,
        raw_output: Dict[str, JsonValue],
        provenance: AnalysisProvenance,
    ) -> SpeechIntelligence:
        results = raw_output.get("results", [])
        transcripts: List[str] = []
        words: List[SpeechWord] = []
        segments: List[SpeechSegment] = []
        primary_lang: Optional[str] = None
        overall_conf: Optional[float] = None

        if isinstance(results, list):
            seg_idx = 0
            for res in results:
                if isinstance(res, dict):
                    lang = res.get("languageCode")
                    if lang and primary_lang is None:
                        primary_lang = str(lang).split("-")[0]

                    alternatives = res.get("alternatives", [])
                    if isinstance(alternatives, list) and alternatives:
                        alt = alternatives[0]
                        if isinstance(alt, dict):
                            alt_transcript = str(alt.get("transcript", "")).strip()
                            if alt_transcript:
                                transcripts.append(alt_transcript)

                            alt_conf = float(alt.get("confidence", 0.95))
                            if overall_conf is None:
                                overall_conf = alt_conf

                            raw_words = alt.get("words", [])
                            seg_words: List[SpeechWord] = []
                            seg_start: Optional[float] = None
                            seg_end: Optional[float] = None
                            seg_speaker: Optional[str] = None

                            if isinstance(raw_words, list):
                                for rw in raw_words:
                                    if isinstance(rw, dict):
                                        w_text = str(rw.get("word", "")).strip()
                                        start_t = self._parse_time_str(rw.get("startTime", 0.0))
                                        end_t = self._parse_time_str(rw.get("endTime", start_t))
                                        spk_tag = rw.get("speakerTag")
                                        spk_id = f"SPEAKER_{int(spk_tag):02d}" if spk_tag is not None else None

                                        if seg_start is None:
                                            seg_start = start_t
                                        seg_end = end_t
                                        if spk_id and not seg_speaker:
                                            seg_speaker = spk_id

                                        if w_text:
                                            w_obj = SpeechWord(
                                                text=w_text,
                                                start=start_t,
                                                end=end_t,
                                                speaker_id=spk_id,
                                                confidence=alt_conf,
                                                language=primary_lang,
                                            )
                                            seg_words.append(w_obj)
                                            words.append(w_obj)

                            if alt_transcript and seg_start is not None and seg_end is not None:
                                segments.append(
                                    SpeechSegment(
                                        id=f"seg_{seg_idx:03d}",
                                        start=seg_start,
                                        end=seg_end,
                                        text=alt_transcript,
                                        speaker_id=seg_speaker,
                                        confidence=alt_conf,
                                        language=primary_lang,
                                        words=seg_words,
                                    )
                                )
                                seg_idx += 1

        full_transcript = " ".join(transcripts)
        speakers = reconcile_speaker_catalog(segments, words)
        dur = words[-1].end if words else None

        return SpeechIntelligence(
            language=primary_lang,
            language_confidence=0.98 if primary_lang else None,
            transcript=full_transcript,
            segments=segments,
            words=words,
            speakers=speakers,
            duration_seconds=dur,
            overall_confidence=overall_conf or 0.95,
            provenance=provenance,
        )


# =============================================================================
# Concrete Provider Implementations for Testing & Swapping
# =============================================================================

class FakeSpeechProviderA(AIProvider):
    """
    Simulated Speech Provider A (Whisper-style wire responses).
    Used for contract verification, fault injection, and provider swap tests.
    """

    def __init__(
        self,
        provider_id: str = "fake-speech-a",
        display_name: str = "Fake Speech Provider A (Whisper Wire)",
        model_id: str = "whisper-large-v3",
        custom_payload: Optional[Dict[str, JsonValue]] = None,
    ):
        definition = ProviderDefinition(
            provider_id=provider_id,
            display_name=display_name,
            supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
            enabled=True,
            description="Offline mock speech provider generating Whisper-like payloads",
        )
        super().__init__(definition)
        self.model_id = model_id
        self.adapter = WhisperStyleAdapter()
        self.custom_payload = custom_payload
        self.invocation_count = 0

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self.invocation_count += 1
        now = datetime.now(timezone.utc)
        provenance = ProvenanceRecord(
            source="fake_speech_provider_a",
            model_id=self.model_id,
            provider_id=self.provider_id,
            timestamp=now,
            latency_ms=45,
        )

        default_output: Dict[str, JsonValue] = {
            "text": "الموبايل الي بايدك أقوى من كمبيوترات ناسا",
            "language": "ar",
            "language_probability": 0.99,
            "duration": 4.5,
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "الموبايل الي بايدك",
                    "speaker": "SPEAKER_00",
                    "confidence": 0.98,
                    "words": [
                        {"word": "الموبايل", "start": 0.0, "end": 0.7, "speaker": "SPEAKER_00", "confidence": 0.99},
                        {"word": "الي", "start": 0.75, "end": 1.1, "speaker": "SPEAKER_00", "confidence": 0.97},
                        {"word": "بايدك", "start": 1.15, "end": 2.0, "speaker": "SPEAKER_00", "confidence": 0.98},
                    ],
                },
                {
                    "start": 2.1,
                    "end": 4.5,
                    "text": "أقوى من كمبيوترات ناسا",
                    "speaker": "SPEAKER_00",
                    "confidence": 0.97,
                    "words": [
                        {"word": "أقوى", "start": 2.1, "end": 2.7, "speaker": "SPEAKER_00", "confidence": 0.98},
                        {"word": "من", "start": 2.75, "end": 3.0, "speaker": "SPEAKER_00", "confidence": 0.96},
                        {"word": "كمبيوترات", "start": 3.05, "end": 3.9, "speaker": "SPEAKER_00", "confidence": 0.97},
                        {"word": "ناسا", "start": 3.95, "end": 4.5, "speaker": "SPEAKER_00", "confidence": 0.98},
                    ],
                },
            ],
        }

        output_data = self.custom_payload if self.custom_payload is not None else default_output

        return CapabilityResult(
            capability=request.capability,
            status=CapabilityStatus.SUCCESS,
            output_data=output_data,
            confidence=0.98,
            provenance=provenance,
            usage=UsageRecord(audio_seconds="4.5"),
        )


class FakeSpeechProviderB(AIProvider):
    """
    Simulated Speech Provider B (Google STT-style wire responses).
    Used for contract verification, fault injection, and provider swap tests.
    """

    def __init__(
        self,
        provider_id: str = "fake-speech-b",
        display_name: str = "Fake Speech Provider B (Google Wire)",
        model_id: str = "chirp-v2",
        custom_payload: Optional[Dict[str, JsonValue]] = None,
    ):
        definition = ProviderDefinition(
            provider_id=provider_id,
            display_name=display_name,
            supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
            enabled=True,
            description="Offline mock speech provider generating Google STT-like payloads",
        )
        super().__init__(definition)
        self.model_id = model_id
        self.adapter = GoogleStyleAdapter()
        self.custom_payload = custom_payload
        self.invocation_count = 0

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self.invocation_count += 1
        now = datetime.now(timezone.utc)
        provenance = ProvenanceRecord(
            source="fake_speech_provider_b",
            model_id=self.model_id,
            provider_id=self.provider_id,
            timestamp=now,
            latency_ms=60,
        )

        default_output: Dict[str, JsonValue] = {
            "results": [
                {
                    "languageCode": "ar-EG",
                    "alternatives": [
                        {
                            "transcript": "الموبايل الي بايدك",
                            "confidence": 0.97,
                            "words": [
                                {"word": "الموبايل", "startTime": "0.0s", "endTime": "0.7s", "speakerTag": 0},
                                {"word": "الي", "startTime": "0.75s", "endTime": "1.1s", "speakerTag": 0},
                                {"word": "بايدك", "startTime": "1.15s", "endTime": "2.0s", "speakerTag": 0},
                            ],
                        }
                    ],
                },
                {
                    "languageCode": "ar-EG",
                    "alternatives": [
                        {
                            "transcript": "أقوى من كمبيوترات ناسا",
                            "confidence": 0.96,
                            "words": [
                                {"word": "أقوى", "startTime": "2.1s", "endTime": "2.7s", "speakerTag": 0},
                                {"word": "من", "startTime": "2.75s", "endTime": "3.0s", "speakerTag": 0},
                                {"word": "كمبيوترات", "startTime": "3.05s", "endTime": "3.9s", "speakerTag": 0},
                                {"word": "ناسا", "startTime": "3.95s", "endTime": "4.5s", "speakerTag": 0},
                            ],
                        }
                    ],
                },
            ]
        }

        output_data = self.custom_payload if self.custom_payload is not None else default_output

        return CapabilityResult(
            capability=request.capability,
            status=CapabilityStatus.SUCCESS,
            output_data=output_data,
            confidence=0.965,
            provenance=provenance,
            usage=UsageRecord(audio_seconds="4.5"),
        )
