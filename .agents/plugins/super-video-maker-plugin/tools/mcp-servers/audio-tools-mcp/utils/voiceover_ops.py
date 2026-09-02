import asyncio
import os
import sys
import time
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Device capability cache file — persists CUDA probe result across MCP restarts
# so we never re-run the expensive (and failing) CUDA probe again.
# ---------------------------------------------------------------------------
_DEVICE_CACHE_PATH = Path(__file__).parent.parent / ".device_capability.json"

def _load_cached_device() -> Tuple[Optional[str], Optional[str]]:
    try:
        if _DEVICE_CACHE_PATH.exists():
            data = json.loads(_DEVICE_CACHE_PATH.read_text(encoding="utf-8"))
            return data.get("device"), data.get("compute_type")
    except Exception:
        pass
    return None, None

def _save_device_cache(device: str, compute_type: str):
    try:
        _DEVICE_CACHE_PATH.write_text(
            json.dumps({"device": device, "compute_type": compute_type}, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"Could not save device cache: {e}")


class WhisperModelManager:
    _instance = None
    _model = None
    _vad_model = None
    _current_model_size = None
    _verified_device = None
    _verified_compute_type = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _detect_device(self) -> Tuple[str, str]:
        """Determine best device for inference.

        Priority order:
        1. In-process singleton cache (fastest — already determined this session)
        2. Persistent file cache (skip probe on MCP restart)
        3. WHISPER_DEVICE env var override (set to 'cuda' to force GPU)
        4. Quick cuBLAS DLL check — only attempts GPU if cublas64_12.dll is loadable
        5. CPU fallback (always works)
        """
        if self._verified_device is not None:
            return self._verified_device, self._verified_compute_type

        # --- 1. Persistent file cache ---
        cached_device, cached_compute = _load_cached_device()
        if cached_device is not None:
            logger.info(f"[device] Using cached device: {cached_device} / {cached_compute}")
            self._verified_device = cached_device
            self._verified_compute_type = cached_compute
            return cached_device, cached_compute

        # --- 2. Env var override ---
        env_device = os.environ.get("WHISPER_DEVICE", "").strip().lower()
        if env_device in ("cuda", "gpu"):
            logger.info("[device] WHISPER_DEVICE=cuda override active")
            self._verified_device = "cuda"
            self._verified_compute_type = "int8"
            _save_device_cache("cuda", "int8")
            return "cuda", "int8"

        # --- 3. Quick cuBLAS DLL check (no model loading — just ctypes) ---
        #     If cublas64_12.dll is missing the CUDA probe would fail anyway.
        #     Skip the expensive WhisperModel() probe entirely.
        _cuda_ok = False
        try:
            import ctranslate2
            import ctypes
            if ctranslate2.get_cuda_device_count() > 0:
                try:
                    ctypes.CDLL("cublas64_12.dll")
                    _cuda_ok = True
                    logger.info("[device] cublas64_12.dll found — CUDA eligible")
                except OSError:
                    logger.warning("[device] cublas64_12.dll NOT found — skipping CUDA (install CUDA 12 toolkit or copy the DLL)")
        except Exception as e:
            logger.warning(f"[device] ctranslate2 check error: {e}")

        if _cuda_ok:
            # Only run the full model probe when cuBLAS is actually present
            try:
                import numpy as np
                from faster_whisper import WhisperModel
                logger.info("[device] Probing CUDA with tiny dummy inference...")
                test_model = WhisperModel("tiny", device="cuda", compute_type="int8")
                dummy = np.zeros(16000, dtype=np.float32)
                _ = list(test_model.transcribe(dummy)[0])
                logger.info("[device] CUDA probe succeeded — using GPU")
                self._verified_device = "cuda"
                self._verified_compute_type = "int8"
                _save_device_cache("cuda", "int8")
                return "cuda", "int8"
            except Exception as e:
                logger.warning(f"[device] CUDA model probe failed ({e}) — falling back to CPU")

        # --- 4. CPU fallback ---
        logger.info("[device] Using CPU for Whisper inference")
        self._verified_device = "cpu"
        self._verified_compute_type = "int8"
        _save_device_cache("cpu", "int8")
        return "cpu", "int8"

    def get_model(self, model_size: str = "base", force_device: str = None, force_compute: str = None):
        """Load (or reuse) a WhisperModel.

        Default model changed from 'small' to 'base':
        - 'base' is ~3x faster than 'small' on CPU with acceptable accuracy
        - 'small' takes ~50s on CPU for a 52s VO file (causes MCP timeout)
        - 'base' takes ~15-20s for the same file
        Use model_size='small' explicitly when accuracy matters more than speed.
        """
        device, compute_type = self._detect_device()
        if force_device:
            device = force_device
        if force_compute:
            compute_type = force_compute

        if self._model is None or self._current_model_size != model_size or force_device is not None:
            from faster_whisper import WhisperModel
            threads = min(8, os.cpu_count() or 4) if device == "cpu" else 0
            logger.info(f"[model] Loading WhisperModel({model_size}) on {device}/{compute_type} cpu_threads={threads}")
            self._model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=threads,
            )
            self._current_model_size = model_size
        return self._model, device, compute_type

    def get_vad_model(self):
        if self._vad_model is None:
            from faster_whisper.vad import get_vad_model as fw_get_vad_model
            logger.info("[model] Loading Silero VAD model")
            self._vad_model = fw_get_vad_model()
        return self._vad_model


def _compute_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_audio_duration_ffmpeg(audio_path: str) -> float:
    try:
        import subprocess
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0:
            return float(res.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe duration check failed: {e}")
    return 10.0


def _fallback_analysis(audio_path: str, reason: str) -> Dict[str, Any]:
    """Graceful Fallback if Whisper fails completely"""
    logger.warning(f"[analyze_voiceover] Triggering Fallback Analysis due to: {reason}")
    dur = _get_audio_duration_ffmpeg(audio_path)
    
    # Simple single-segment fallback structure
    return {
        "full_text": "[Audio Voiceover Track]",
        "language": "ar",
        "language_probability": 1.0,
        "model_device": "fallback_engine",
        "compute_type": "none",
        "model_size": "fallback",
        "duration": round(dur, 3),
        "speech_periods": [{"start": 0.0, "end": round(dur, 3)}],
        "silence_periods": [],
        "segments": [{
            "start": 0.0,
            "end": round(dur, 3),
            "text": "[Voiceover Speech]",
            "confidence": 1.0,
            "words": []
        }],
        "_fallback_reason": reason
    }


def _analyze_voiceover_sync(audio_path: str, language: Optional[str] = None, model_size: Optional[str] = None) -> Dict[str, Any]:
    # Check cache first
    try:
        f_hash = _compute_file_hash(audio_path)
        cache_file = Path(audio_path).parent / f".{Path(audio_path).stem}_{f_hash[:8]}.analysis.json"
        if cache_file.exists():
            logger.info(f"[analyze_voiceover] Cache HIT: {cache_file}")
            return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")

    try:
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        from faster_whisper.audio import decode_audio
        import math
    except ImportError as e:
        return _fallback_analysis(audio_path, f"faster_whisper not imported: {e}")
    
    start_time = time.time()
    logger.info(f"[analyze_voiceover] Starting analysis for file: {audio_path}")
    
    manager = WhisperModelManager.get_instance()
    # Default to 'base' (3x faster than 'small' on CPU, ~15-20s vs ~50s for 52s VO)
    # Pass model_size='small' explicitly when higher accuracy is required
    ms = model_size or "base"
    
    try:
        model, device, compute_type = manager.get_model(ms)
        vad_model = manager.get_vad_model()
    except Exception as e:
        logger.error(f"Failed to load Whisper/VAD model: {e}")
        return _fallback_analysis(audio_path, f"Model loading failed: {e}")
    
    # 1. Decode audio
    try:
        sampling_rate = 16000
        audio_array = decode_audio(audio_path, sampling_rate=sampling_rate)
        audio_duration = len(audio_array) / sampling_rate
    except Exception as e:
        logger.error(f"Audio decoding failed: {e}")
        return _fallback_analysis(audio_path, f"Audio decoding failed: {e}")
    
    # 2. Get VAD speech timestamps
    try:
        vad_options = VadOptions()
        speech_chunks = get_speech_timestamps(audio_array, vad_options, vad_model=vad_model)
        speech_periods = []
        for chunk in speech_chunks:
            start_val = chunk['start']
            end_val = chunk['end']
            if isinstance(start_val, int) and (start_val > 1000 or end_val > 1000):
                start_sec = float(start_val) / sampling_rate
                end_sec = float(end_val) / sampling_rate
            else:
                start_sec = float(start_val) / sampling_rate if isinstance(start_val, int) else float(start_val)
                end_sec = float(end_val) / sampling_rate if isinstance(end_val, int) else float(end_val)
                
            speech_periods.append({
                "start": round(start_sec, 3),
                "end": round(end_sec, 3)
            })
    except Exception as e:
        logger.warning(f"VAD calculation error: {e}")
        speech_periods = [{"start": 0.0, "end": round(audio_duration, 3)}]
        
    # 3. Calculate silence periods
    silence_periods = []
    last_end = 0.0
    for chunk in speech_periods:
        if chunk['start'] > last_end:
            silence_periods.append({
                "start": round(last_end, 3),
                "end": round(chunk['start'], 3)
            })
        last_end = chunk['end']
        
    if last_end < audio_duration:
        silence_periods.append({
            "start": round(last_end, 3),
            "end": round(audio_duration, 3)
        })
        
    # 4. Transcribe using Whisper
    try:
        segments_gen, info = model.transcribe(
            audio_array,
            language=language,
            vad_filter=True,
            word_timestamps=True
        )
        segments_list = []
        full_text_parts = []
        for segment in segments_gen:
            words = []
            if segment.words:
                for w in segment.words:
                    words.append({
                        "start": round(float(w.start), 3),
                        "end": round(float(w.end), 3),
                        "word": w.word,
                        "probability": float(w.probability)
                    })
                
            segments_list.append({
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": segment.text.strip(),
                "confidence": math.exp(segment.avg_logprob) if segment.avg_logprob < 0 else 1.0,
                "words": words
            })
            full_text_parts.append(segment.text.strip())
            
        result = {
            "full_text": " ".join(full_text_parts).strip(),
            "language": info.language if info else "ar",
            "language_probability": float(info.language_probability) if info else 1.0,
            "model_device": device,
            "compute_type": compute_type,
            "model_size": ms,
            "duration": round(float(audio_duration), 3),
            "speech_periods": speech_periods,
            "silence_periods": silence_periods,
            "segments": segments_list
        }
        
        # Save to cache
        try:
            cache_file = Path(audio_path).parent / f".{Path(audio_path).stem}_{f_hash[:8]}.analysis.json"
            cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as ce:
            logger.warning(f"Failed to write cache: {ce}")
            
        return result
        
    except Exception as e:
        logger.error(f"[analyze_voiceover] Whisper transcription failed: {e}")
        return _fallback_analysis(audio_path, str(e))


async def analyze_voiceover_file(audio_path: str, language: Optional[str] = None, model_size: Optional[str] = None) -> Dict[str, Any]:
    logger.info(f"[analyze_voiceover] Tool invoked. Validating input: {audio_path}")
    if not os.path.exists(audio_path):
        logger.error(f"[analyze_voiceover] Validation failed: Audio file not found: {audio_path}")
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
    try:
        result = await asyncio.to_thread(_analyze_voiceover_sync, audio_path, language, model_size)
        return result
    except Exception as e:
        logger.error(f"[analyze_voiceover] Tool execution failed: {e}")
        return _fallback_analysis(audio_path, str(e))
