"""
ai/speech/local_provider.py
===========================
Authoritative LocalSTTProvider implementation for S28-M04.

Invariants:
- Implements abstract STTProvider interface.
- Executes real local faster-whisper inference on CTranslate2 engine.
- Silero VAD integration for speech/silence period demarcation.
- Strict bounded concurrency and queue backpressure.
- Deterministic device selection (CUDA probe with explicit CPU fallback and telemetry).
- Distinction between valid silence (clean empty transcript) and corrupt audio (structured failure).
- Normalizes output strictly into canonical SpeechIntelligence / TranscriptArtifact contracts.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ai.contracts.media import (
    AnalysisProvenance,
    SpeechIntelligence,
    SpeechSegment,
    SpeechSpeaker,
    SpeechWord,
)
from ai.speech.lifecycle import WhisperLifecycleManager
from ai.speech.stt_provider import (
    AudioDecodeError,
    DeviceUnavailableError,
    InvalidAudioError,
    ModelInferenceError,
    ModelLoadError,
    ModelNotAvailableError,
    OutputValidationError,
    ResourceExhaustedError,
    STTCapabilities,
    STTConfig,
    STTError,
    STTHealth,
    STTProvider,
    STTRequest,
    STTResponse,
    STTTimeoutError,
)

logger = logging.getLogger("clean_video.ai.speech.local_provider")


class LocalSTTProvider(STTProvider):
    """
    Official local Speech-to-Text provider backed by faster-whisper (CTranslate2)
    and Silero VAD.
    """

    def __init__(
        self,
        provider_id: str = "local",
        default_model_size: str = "base",
        lifecycle_manager: Optional[WhisperLifecycleManager] = None,
        max_concurrency: int = 2,
        max_queue_depth: int = 10,
    ) -> None:
        self._provider_id = provider_id
        self.default_model_size = default_model_size
        self.lifecycle_manager = lifecycle_manager or WhisperLifecycleManager.get_instance(
            default_model_size=default_model_size,
            max_concurrency=max_concurrency,
            max_queue_depth=max_queue_depth,
        )

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_health(self) -> STTHealth:
        """Inspects operational state without triggering heavy model load."""
        dev, comp, _, _ = self.lifecycle_manager.device_info
        return STTHealth(
            provider_id=self._provider_id,
            model_id=f"faster-whisper-{self.default_model_size}",
            model_version="1.2.1",
            registered=True,
            weights_available=True,
            loaded=self.lifecycle_manager.is_loaded,
            device=dev,
            compute_type=comp,
            ready=True,
            queue_depth=self.lifecycle_manager.queue_depth,
            active_requests=self.lifecycle_manager.active_requests,
            load_count=self.lifecycle_manager.load_count,
        )

    def get_capabilities(self) -> STTCapabilities:
        """Returns declarative capabilities."""
        return STTCapabilities(
            provider_id=self._provider_id,
            model_family="whisper",
            engine="faster-whisper / CTranslate2",
            supported_model_sizes=["tiny", "base", "small", "medium", "large-v3"],
            supported_devices=["cpu", "cuda"],
            supported_compute_types=["int8", "float16", "float32"],
            word_timestamps_supported=True,
            language_detection_supported=True,
            vad_supported=True,
            batch_supported=True,
            streaming_supported=False,
            languages=["*"],
        )

    def _decode_audio_file(self, audio_path: str) -> Tuple[np.ndarray, float]:
        """Decodes audio file into 16 kHz mono float32 numpy array."""
        p = Path(audio_path)
        if not p.exists() or p.stat().st_size == 0:
            raise InvalidAudioError(
                f"Audio file is missing or zero-bytes: {audio_path}",
                details={"audio_path": audio_path, "file_size": 0},
            )

        try:
            from faster_whisper.audio import decode_audio
            sampling_rate = 16000
            audio_array = decode_audio(str(p), sampling_rate=sampling_rate)
            duration = len(audio_array) / float(sampling_rate)
            return audio_array, duration
        except Exception as e:
            raise AudioDecodeError(
                f"Failed to decode audio file '{audio_path}': {e}",
                details={"audio_path": audio_path, "error": str(e)},
            )

    def _extract_vad_periods(
        self,
        audio_array: np.ndarray,
        duration: float,
        config: STTConfig,
    ) -> Tuple[List[Dict[str, float]], List[Dict[str, float]]]:
        """Runs Silero VAD to calculate speech and silence intervals."""
        if not config.vad_filter:
            return [{"start": 0.0, "end": round(duration, 3)}], []

        try:
            from faster_whisper.vad import VadOptions, get_speech_timestamps
            vad_model = self.lifecycle_manager.get_vad_model()
            vad_options = VadOptions(
                threshold=config.vad_threshold,
                min_speech_duration_ms=config.min_speech_duration_ms,
                min_silence_duration_ms=config.min_silence_duration_ms,
            )
            raw_chunks = get_speech_timestamps(audio_array, vad_options, vad_model=vad_model)

            sampling_rate = 16000
            speech_periods: List[Dict[str, float]] = []
            for chunk in raw_chunks:
                start_val = chunk["start"]
                end_val = chunk["end"]
                s_sec = float(start_val) / sampling_rate if isinstance(start_val, int) else float(start_val)
                e_sec = float(end_val) / sampling_rate if isinstance(end_val, int) else float(end_val)
                speech_periods.append({
                    "start": round(s_sec, 3),
                    "end": round(e_sec, 3),
                })

            silence_periods: List[Dict[str, float]] = []
            last_end = 0.0
            for sp in speech_periods:
                if sp["start"] > last_end:
                    silence_periods.append({
                        "start": round(last_end, 3),
                        "end": round(sp["start"], 3),
                    })
                last_end = sp["end"]

            if last_end < duration:
                silence_periods.append({
                    "start": round(last_end, 3),
                    "end": round(duration, 3),
                })

            return speech_periods, silence_periods
        except Exception as e:
            logger.warning("Silero VAD calculation encountered an error (%s); falling back to full audio interval", e)
            return [{"start": 0.0, "end": round(duration, 3)}], []

    async def transcribe(self, request: STTRequest) -> STTResponse:
        """
        Executes real transcription on the materialized audio file.
        Enforces concurrency limit, lazy loading, and output validation.
        """
        config = request.config
        config_hash = config.compute_config_hash()

        # Step 1: Decode audio
        audio_array, duration = self._decode_audio_file(request.audio_path)

        # Step 2: Handle Digital Silence Edge Case
        max_amplitude = float(np.max(np.abs(audio_array))) if len(audio_array) > 0 else 0.0
        if max_amplitude < 1e-4:
            logger.info("Detected digital silence for audio (max amp: %e); returning clean empty transcript", max_amplitude)
            dev, comp, fb_occ, fb_reason = self.lifecycle_manager.device_info
            return STTResponse(
                request_id=request.request_id,
                transcript="",
                language=config.language or "en",
                language_confidence=1.0,
                duration_seconds=round(duration, 3),
                segments=[],
                words=[],
                speakers=[],
                model_device=dev,
                compute_type=comp,
                model_id=f"faster-whisper-{config.model_size}",
                model_version="1.2.1",
                engine="faster-whisper / CTranslate2",
                fallback_occurred=fb_occ,
                fallback_reason=fb_reason,
                queue_wait_ms=0.0,
                model_load_ms=0.0,
                inference_ms=0.0,
                real_time_factor=0.0,
                speech_periods=[],
                silence_periods=[{"start": 0.0, "end": round(duration, 3)}],
                config_hash=config_hash,
            )

        # Step 3: Run Silero VAD
        speech_periods, silence_periods = self._extract_vad_periods(audio_array, duration, config)

        # Step 4: Concurrency slot acquisition & backpressure
        q_start = time.perf_counter()
        await self.lifecycle_manager.acquire_execution_slot()
        queue_wait_ms = (time.perf_counter() - q_start) * 1000.0

        try:
            # Step 5: Acquire (or warm reuse) model instance
            model, load_ms = await self.lifecycle_manager.get_model(
                model_size=config.model_size,
            )
            dev, comp, fb_occ, fb_reason = self.lifecycle_manager.device_info

            # Step 6: Execute Model Inference synchronously in worker thread
            def _inference_worker() -> Tuple[Any, Any]:
                vad_opts = dict(
                    threshold=config.vad_threshold,
                    min_speech_duration_ms=config.min_speech_duration_ms,
                    min_silence_duration_ms=config.min_silence_duration_ms,
                ) if config.vad_filter else None

                segments_gen, info = model.transcribe(
                    audio_array,
                    language=config.language,
                    beam_size=config.beam_size,
                    temperature=config.temperature,
                    vad_filter=config.vad_filter,
                    vad_parameters=vad_opts,
                    word_timestamps=config.word_timestamps,
                    condition_on_previous_text=config.condition_on_previous_text,
                    initial_prompt=config.initial_prompt,
                )
                return list(segments_gen), info

            inf_start = time.perf_counter()
            try:
                raw_segments, info = await asyncio.wait_for(
                    asyncio.to_thread(_inference_worker),
                    timeout=request.timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise STTTimeoutError(
                    f"STT inference timed out after {request.timeout_seconds} seconds.",
                    details={"timeout_seconds": request.timeout_seconds},
                )
            except Exception as e:
                raise ModelInferenceError(
                    f"Faster-whisper inference failed: {e}",
                    details={"error": str(e), "model_size": config.model_size},
                )
            inf_ms = (time.perf_counter() - inf_start) * 1000.0

            # Step 7: Normalize Segments & Words
            segments: List[SpeechSegment] = []
            all_words: List[SpeechWord] = []
            full_text_parts: List[str] = []

            last_seg_start = -1.0
            last_word_start = -1.0

            for i, seg in enumerate(raw_segments):
                seg_text = seg.text.strip()
                if not seg_text:
                    continue

                seg_start = max(0.0, float(seg.start))
                seg_end = max(seg_start, float(seg.end))

                # Enforce chronological monotonicity
                if seg_start < last_seg_start:
                    seg_start = last_seg_start
                    seg_end = max(seg_start, seg_end)
                last_seg_start = seg_start

                seg_conf = math.exp(seg.avg_logprob) if seg.avg_logprob < 0 else 1.0
                seg_conf = min(1.0, max(0.0, seg_conf))

                seg_words: List[SpeechWord] = []
                if seg.words:
                    for w in seg.words:
                        w_text = w.word.strip()
                        if not w_text:
                            continue
                        w_start = max(seg_start, float(w.start))
                        w_end = max(w_start, float(w.end))

                        if w_start < last_word_start:
                            w_start = last_word_start
                            w_end = max(w_start, w_end)
                        last_word_start = w_start

                        w_prob = float(w.probability) if w.probability is not None else seg_conf
                        w_prob = min(1.0, max(0.0, w_prob))

                        word_obj = SpeechWord(
                            text=w_text,
                            start=round(w_start, 3),
                            end=round(w_end, 3),
                            confidence=round(w_prob, 3),
                            language=info.language if info else config.language,
                        )
                        seg_words.append(word_obj)
                        all_words.append(word_obj)

                segment_obj = SpeechSegment(
                    id=f"seg_{i:03d}",
                    start=round(seg_start, 3),
                    end=round(seg_end, 3),
                    text=seg_text,
                    confidence=round(seg_conf, 3),
                    language=info.language if info else config.language,
                    words=seg_words,
                )
                segments.append(segment_obj)
                full_text_parts.append(seg_text)

            consolidated_text = " ".join(full_text_parts).strip()
            detected_lang = info.language if info else (config.language or "en")
            lang_prob = float(info.language_probability) if (info and info.language_probability is not None) else 0.95
            rtf = (inf_ms / 1000.0) / max(0.001, duration)

            response = STTResponse(
                request_id=request.request_id,
                transcript=consolidated_text,
                language=detected_lang,
                language_confidence=round(lang_prob, 3),
                duration_seconds=round(duration, 3),
                segments=segments,
                words=all_words,
                speakers=[],
                model_device=dev,
                compute_type=comp,
                model_id=f"faster-whisper-{config.model_size}",
                model_version="1.2.1",
                engine="faster-whisper / CTranslate2",
                fallback_occurred=fb_occ,
                fallback_reason=fb_reason,
                queue_wait_ms=round(queue_wait_ms, 2),
                model_load_ms=round(load_ms, 2),
                inference_ms=round(inf_ms, 2),
                real_time_factor=round(rtf, 4),
                speech_periods=speech_periods,
                silence_periods=silence_periods,
                config_hash=config_hash,
            )

            # Step 8: Strict Output Contract Verification
            try:
                test_intel = response.to_speech_intelligence()
            except Exception as val_err:
                raise OutputValidationError(
                    f"Generated STT response failed SpeechIntelligence contract validation: {val_err}",
                    details={"error": str(val_err)},
                )

            return response

        finally:
            self.lifecycle_manager.release_execution_slot()

    async def close(self) -> None:
        """Releases underlying model instances and clears lifecycle state."""
        await self.lifecycle_manager.close()
