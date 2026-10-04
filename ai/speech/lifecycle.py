"""
ai/speech/lifecycle.py
======================
Thread-safe, observable model lifecycle and device selection manager for S28-M04.

Invariants:
- Thread-safe, race-safe lazy loading (concurrent initial requests initialize model ONCE).
- Persistent in-memory model reuse across requests (load_count preserved).
- Deterministic device selection (CUDA probe with graceful CPU fallback and explicit telemetry).
- Strict concurrency bounding and backpressure enforcement (bounded semaphore and queue).
- Internal Silero VAD model lifecycle management.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("clean_video.ai.speech.lifecycle")


class WhisperLifecycleManager:
    """
    Singleton lifecycle manager governing faster-whisper and Silero VAD model instances.
    Guarantees thread-safe lazy loading, model instance reuse, and device fallback.
    """

    _instance: Optional[WhisperLifecycleManager] = None
    _singleton_lock = threading.Lock()

    def __init__(
        self,
        default_model_size: str = "base",
        max_concurrency: int = 2,
        max_queue_depth: int = 10,
    ) -> None:
        self.default_model_size = default_model_size
        self.max_concurrency = max_concurrency
        self.max_queue_depth = max_queue_depth

        self._model: Optional[Any] = None
        self._vad_model: Optional[Any] = None
        self._current_model_size: Optional[str] = None
        self._device: Optional[str] = None
        self._compute_type: Optional[str] = None
        self._fallback_occurred: bool = False
        self._fallback_reason: Optional[str] = None

        self._load_count: int = 0
        self._async_load_lock: Optional[asyncio.Lock] = None
        self._sync_load_lock = threading.Lock()

        # Concurrency & Backpressure
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._queue_depth: int = 0
        self._active_requests: int = 0

    @classmethod
    def get_instance(
        cls,
        default_model_size: str = "base",
        max_concurrency: int = 2,
        max_queue_depth: int = 10,
    ) -> WhisperLifecycleManager:
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(
                    default_model_size=default_model_size,
                    max_concurrency=max_concurrency,
                    max_queue_depth=max_queue_depth,
                )
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets singleton instance for clean test isolation."""
        with cls._singleton_lock:
            if cls._instance is not None:
                cls._instance._model = None
                cls._instance._vad_model = None
                cls._instance._load_count = 0
                cls._instance = None

    @property
    def load_count(self) -> int:
        return self._load_count

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def queue_depth(self) -> int:
        return self._queue_depth

    @property
    def active_requests(self) -> int:
        return self._active_requests

    @property
    def device_info(self) -> Tuple[str, str, bool, Optional[str]]:
        dev = self._device or "cpu"
        comp = self._compute_type or "int8"
        return dev, comp, self._fallback_occurred, self._fallback_reason

    def _get_async_lock(self) -> asyncio.Lock:
        if self._async_load_lock is None:
            self._async_load_lock = asyncio.Lock()
        return self._async_load_lock

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self._semaphore

    def detect_device(self, requested_device: Optional[str] = None) -> Tuple[str, str, bool, Optional[str]]:
        """
        Determines the optimal execution device.
        Priority:
        1. Explicit requested_device if provided.
        2. WHISPER_DEVICE environment variable override.
        3. Hardware probe (CUDA if available and functional).
        4. CPU fallback (int8).
        """
        # Env override check
        env_dev = os.environ.get("WHISPER_DEVICE", "").strip().lower()
        target = requested_device.lower() if requested_device else (env_dev or "auto")

        if target == "cpu":
            return "cpu", "int8", False, None

        if target in ("cuda", "auto"):
            # Probe CUDA capabilities
            cuda_available = False
            fallback_reason: Optional[str] = None
            try:
                import ctranslate2
                cuda_count = ctranslate2.get_cuda_device_count()
                if cuda_count > 0:
                    # Test tiny dummy probe to verify cuBLAS / CUDA libraries
                    try:
                        import numpy as np
                        from faster_whisper import WhisperModel
                        probe = WhisperModel("tiny", device="cuda", compute_type="int8")
                        dummy = np.zeros(16000, dtype=np.float32)
                        _ = list(probe.transcribe(dummy)[0])
                        cuda_available = True
                    except Exception as probe_err:
                        fallback_reason = str(probe_err)
                        logger.warning("CUDA available on system but probe failed (%s) — falling back to CPU", probe_err)
                else:
                    fallback_reason = "No CUDA devices reported by CTranslate2"
            except Exception as e:
                fallback_reason = f"CTranslate2 CUDA probe error: {e}"

            if cuda_available:
                return "cuda", "int8", False, None

            # If user strictly requested CUDA without auto, record fallback
            fallback_occurred = target == "cuda" or (env_dev == "cuda")
            return "cpu", "int8", fallback_occurred, fallback_reason

        return "cpu", "int8", False, None

    def _load_model_sync(
        self,
        model_size: str,
        requested_device: Optional[str] = None,
        force_reload: bool = False,
    ) -> Tuple[Any, float]:
        """
        Synchronous model loader called under lock.
        Reuses cached instance if model_size matches and not forced.
        """
        start_time = time.perf_counter()

        if self._model is not None and self._current_model_size == model_size and not force_reload:
            logger.info("Reusing warm WhisperModel(%s) instance", model_size)
            return self._model, 0.0

        device, compute_type, fallback_occurred, fallback_reason = self.detect_device(requested_device)
        self._device = device
        self._compute_type = compute_type
        self._fallback_occurred = fallback_occurred
        self._fallback_reason = fallback_reason

        from faster_whisper import WhisperModel

        threads = min(8, os.cpu_count() or 4) if device == "cpu" else 0
        logger.info(
            "Initializing WhisperModel(%s) on device=%s, compute_type=%s, cpu_threads=%d",
            model_size,
            device,
            compute_type,
            threads,
        )

        try:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=threads,
            )
        except Exception as e:
            # If initial CUDA attempt failed during model load, execute emergency CPU fallback
            if device == "cuda":
                logger.warning("WhisperModel CUDA load failed (%s); attempting emergency CPU fallback", e)
                self._device = "cpu"
                self._compute_type = "int8"
                self._fallback_occurred = True
                self._fallback_reason = str(e)
                threads = min(8, os.cpu_count() or 4)
                model = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=threads,
                )
            else:
                raise

        load_ms = (time.perf_counter() - start_time) * 1000.0
        self._model = model
        self._current_model_size = model_size
        self._load_count += 1
        logger.info(
            "WhisperModel(%s) successfully loaded in %.2f ms (load_count=%d)",
            model_size,
            load_ms,
            self._load_count,
        )
        return self._model, load_ms

    async def get_model(
        self,
        model_size: Optional[str] = None,
        requested_device: Optional[str] = None,
        force_reload: bool = False,
    ) -> Tuple[Any, float]:
        """
        Thread-safe and race-safe async model acquisition.
        If multiple concurrent requests arrive while unloaded, only one loads the model.
        """
        size = model_size or self.default_model_size
        lock = self._get_async_lock()

        # Fast path if already loaded with matching size
        if self._model is not None and self._current_model_size == size and not force_reload:
            return self._model, 0.0

        async with lock:
            # Double check pattern after acquiring lock
            if self._model is not None and self._current_model_size == size and not force_reload:
                return self._model, 0.0

            model, load_ms = await asyncio.to_thread(
                self._load_model_sync,
                size,
                requested_device,
                force_reload,
            )
            return model, load_ms

    def get_vad_model(self) -> Any:
        """Lazy loads and caches the shared Silero VAD model instance."""
        with self._sync_load_lock:
            if self._vad_model is None:
                from faster_whisper.vad import get_vad_model as fw_get_vad_model
                logger.info("Loading shared Silero VAD model")
                self._vad_model = fw_get_vad_model()
            return self._vad_model

    async def acquire_execution_slot(self) -> None:
        """
        Enforces bounded queue and backpressure.
        Raises ResourceExhaustedError if queue depth ceiling is breached.
        """
        from ai.speech.stt_provider import ResourceExhaustedError

        if self._queue_depth >= self.max_queue_depth:
            raise ResourceExhaustedError(
                f"STT execution queue full ({self._queue_depth}/{self.max_queue_depth}). Backpressure limit reached.",
                details={
                    "queue_depth": self._queue_depth,
                    "max_queue_depth": self.max_queue_depth,
                    "active_requests": self._active_requests,
                },
            )

        self._queue_depth += 1
        sem = self._get_semaphore()
        try:
            await sem.acquire()
        finally:
            self._queue_depth = max(0, self._queue_depth - 1)
        self._active_requests += 1

    def release_execution_slot(self) -> None:
        """Releases the execution concurrency slot."""
        sem = self._get_semaphore()
        sem.release()
        self._active_requests = max(0, self._active_requests - 1)

    async def close(self) -> None:
        """Cleans up in-memory models and resets state."""
        lock = self._get_async_lock()
        async with lock:
            self._model = None
            self._vad_model = None
            self._current_model_size = None
            self._active_requests = 0
            self._queue_depth = 0
            logger.info("WhisperLifecycleManager shut down and released models")
