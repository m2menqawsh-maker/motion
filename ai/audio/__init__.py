"""
ai/audio/__init__.py
====================
Audio Intelligence package for S27.16 (AI-13).
"""

from ai.audio.dsp import (
    NativeAudioDSP,
)
from ai.audio.pipeline import (
    AudioIntelligencePipeline,
)
from ai.contracts.creative.brief import AudioMode
from ai.audio.modes import (
    AudioModeEngine,
    AudioModePolicy,
    AudioPolicyViolationError,
    CaptionPolicy,
    MusicPolicy,
    MixPolicy,
    DuckingPolicy,
    SpeechPolicy,
)

__all__ = [
    "NativeAudioDSP",
    "AudioIntelligencePipeline",
    "AudioMode",
    "AudioModeEngine",
    "AudioModePolicy",
    "AudioPolicyViolationError",
    "CaptionPolicy",
    "MusicPolicy",
    "MixPolicy",
    "DuckingPolicy",
    "SpeechPolicy",
]
