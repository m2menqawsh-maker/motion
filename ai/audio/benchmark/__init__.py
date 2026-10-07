"""
ai/audio/benchmark/__init__.py
==============================
"""

from ai.audio.benchmark.manifest import (
    AudioBenchmarkCategory,
    AudioBenchmarkSample,
    PROJECT_AUDIO_BENCHMARK_CORPUS,
    get_audio_benchmark_manifest,
    get_audio_categories_summary,
)
from ai.audio.benchmark.fixtures import (
    generate_clean_speech_fixture,
    generate_clipping_fixture,
    generate_echo_fixture,
    generate_low_volume_fixture,
    generate_music_and_speech_fixture,
    generate_music_fixture,
    generate_noise_fixture,
)
from ai.audio.benchmark.metrics import (
    evaluate_clipping_detection,
    evaluate_snr_band,
)
from ai.audio.benchmark.runner import (
    AudioBenchmarkReport,
    AudioBenchmarkRunner,
)

__all__ = [
    "AudioBenchmarkCategory",
    "AudioBenchmarkSample",
    "PROJECT_AUDIO_BENCHMARK_CORPUS",
    "get_audio_benchmark_manifest",
    "get_audio_categories_summary",
    "generate_clean_speech_fixture",
    "generate_clipping_fixture",
    "generate_echo_fixture",
    "generate_low_volume_fixture",
    "generate_music_and_speech_fixture",
    "generate_music_fixture",
    "generate_noise_fixture",
    "evaluate_clipping_detection",
    "evaluate_snr_band",
    "AudioBenchmarkReport",
    "AudioBenchmarkRunner",
]
