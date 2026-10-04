"""
ai/audio/benchmark/manifest.py
==============================
Benchmark dataset manifest for Audio Intelligence (S27.16 / AI-13 Rule 14).

Covers all 7 mandatory acoustic scenarios:
1. Clean speech
2. Noise (background ambient / hiss)
3. Music
4. Music + speech composite
5. Clipping (digital ceiling saturation)
6. Echo (reverberant room reflections)
7. Low volume (-30 dBFS to -45 dBFS)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class AudioBenchmarkCategory(str, Enum):
    CLEAN_SPEECH = "clean_speech"
    NOISE = "noise"
    MUSIC = "music"
    MUSIC_PLUS_SPEECH = "music_plus_speech"
    CLIPPING = "clipping"
    ECHO = "echo"
    LOW_VOLUME = "low_volume"


@dataclass(frozen=True)
class AudioBenchmarkSample:
    sample_id: str
    category: AudioBenchmarkCategory
    description: str
    duration_sec: float
    expected_clipping: bool
    expected_snr_band: str  # "high", "medium", "low"
    has_speech: bool
    has_music: bool
    has_real_recording: bool = False  # Set to False until Final Validation


PROJECT_AUDIO_BENCHMARK_CORPUS: List[AudioBenchmarkSample] = [
    AudioBenchmarkSample(
        sample_id="aud_clean_speech_001",
        category=AudioBenchmarkCategory.CLEAN_SPEECH,
        description="Studio vocal recording with high SNR (> 25 dB) and zero clipping",
        duration_sec=5.0,
        expected_clipping=False,
        expected_snr_band="high",
        has_speech=True,
        has_music=False,
    ),
    AudioBenchmarkSample(
        sample_id="aud_noise_001",
        category=AudioBenchmarkCategory.NOISE,
        description="Continuous ambient room noise / air conditioning hiss without voice",
        duration_sec=4.0,
        expected_clipping=False,
        expected_snr_band="low",
        has_speech=False,
        has_music=False,
    ),
    AudioBenchmarkSample(
        sample_id="aud_music_001",
        category=AudioBenchmarkCategory.MUSIC,
        description="Acoustic background instrumental track with steady beat grid",
        duration_sec=6.0,
        expected_clipping=False,
        expected_snr_band="high",
        has_speech=False,
        has_music=True,
    ),
    AudioBenchmarkSample(
        sample_id="aud_music_speech_001",
        category=AudioBenchmarkCategory.MUSIC_PLUS_SPEECH,
        description="Voiceover narration over mixed background music bed",
        duration_sec=5.0,
        expected_clipping=False,
        expected_snr_band="medium",
        has_speech=True,
        has_music=True,
    ),
    AudioBenchmarkSample(
        sample_id="aud_clipping_001",
        category=AudioBenchmarkCategory.CLIPPING,
        description="Overdriven audio signal saturated at full 0 dBFS ceiling",
        duration_sec=3.0,
        expected_clipping=True,
        expected_snr_band="medium",
        has_speech=True,
        has_music=False,
    ),
    AudioBenchmarkSample(
        sample_id="aud_echo_001",
        category=AudioBenchmarkCategory.ECHO,
        description="Voice spoken in reverberant empty hall with multi-tap reflections",
        duration_sec=4.0,
        expected_clipping=False,
        expected_snr_band="medium",
        has_speech=True,
        has_music=False,
    ),
    AudioBenchmarkSample(
        sample_id="aud_low_vol_001",
        category=AudioBenchmarkCategory.LOW_VOLUME,
        description="Whispered speech at very low amplitude (-36 dBFS)",
        duration_sec=5.0,
        expected_clipping=False,
        expected_snr_band="low",
        has_speech=True,
        has_music=False,
    ),
]


def get_audio_benchmark_manifest() -> List[AudioBenchmarkSample]:
    return list(PROJECT_AUDIO_BENCHMARK_CORPUS)


def get_audio_categories_summary() -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for sample in PROJECT_AUDIO_BENCHMARK_CORPUS:
        key = sample.category.value
        summary[key] = summary.get(key, 0) + 1
    return summary
