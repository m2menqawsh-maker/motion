"""
tests/ai/audio/test_audio_mode_engine.py
========================================
Comprehensive Unit & Negative Invariant Tests for S28-03 AudioModeEngine.

Guarantees:
- Every canonical AudioMode (MUSIC_ONLY, VO_ONLY, VO_MUSIC, SOURCE_AUDIO, SOURCE_AUDIO_MUSIC, SILENT)
  is a formal policy with typed capability requirements.
- Hard negative requirements are strictly enforced:
  • SILENT adds BGM -> FAIL (AudioPolicyViolationError)
  • MUSIC_ONLY invokes TEXT_TO_SPEECH -> FAIL (AudioPolicyViolationError)
- Recipe eligibility checking disqualifies recipes with forbidden capabilities.
"""

import pytest
from ai.audio.modes import (
    AudioMode,
    AudioModeEngine,
    AudioModePolicy,
    AudioPolicyViolationError,
    CaptionPolicy,
    DuckingPolicy,
    MixPolicy,
    MusicPolicy,
    SpeechPolicy,
)
from ai.contracts.common import CapabilityType
from ai.recipes.registry import RecipeRegistry


@pytest.fixture
def engine() -> AudioModeEngine:
    return AudioModeEngine()


# -----------------------------------------------------------------------------
# 1. Canonical Policies Verification
# -----------------------------------------------------------------------------
def test_all_canonical_modes_registered(engine: AudioModeEngine):
    """Verifies that all 6 canonical S28 audio modes have registered policies."""
    policies = engine.get_all_policies()
    assert len(policies) == 6
    for mode in AudioMode:
        policy = engine.get_policy(mode)
        assert isinstance(policy, AudioModePolicy)
        assert policy.audio_mode == mode


def test_music_only_policy_invariants(engine: AudioModeEngine):
    """Verifies MUSIC_ONLY invariants: requires beat detection, forbids TTS and diarization."""
    policy = engine.get_policy(AudioMode.MUSIC_ONLY)
    assert CapabilityType.BEAT_DETECTION in policy.required_capabilities
    assert CapabilityType.TEXT_TO_SPEECH in policy.forbidden_capabilities
    assert CapabilityType.DIARIZATION in policy.forbidden_capabilities

    assert policy.music_policy == MusicPolicy.REQUIRED
    assert policy.speech_policy == SpeechPolicy.FORBIDDEN
    assert policy.ducking_policy == DuckingPolicy.DISABLED


def test_silent_policy_invariants(engine: AudioModeEngine):
    """Verifies SILENT invariants: forbids all audio playback and generation."""
    policy = engine.get_policy(AudioMode.SILENT)
    assert CapabilityType.TEXT_TO_SPEECH in policy.forbidden_capabilities
    assert CapabilityType.MUSIC_GENERATION in policy.forbidden_capabilities
    assert CapabilityType.SPEECH_ALIGNMENT in policy.forbidden_capabilities

    assert policy.music_policy == MusicPolicy.FORBIDDEN
    assert policy.speech_policy == SpeechPolicy.FORBIDDEN
    assert policy.mix_policy == MixPolicy.NONE
    assert policy.ducking_policy == DuckingPolicy.DISABLED


def test_vo_music_policy_invariants(engine: AudioModeEngine):
    """Verifies VO_MUSIC invariants: requires TTS and speech alignment, background BGM with ducking."""
    policy = engine.get_policy(AudioMode.VO_MUSIC)
    assert CapabilityType.TEXT_TO_SPEECH in policy.required_capabilities
    assert CapabilityType.SPEECH_ALIGNMENT in policy.required_capabilities

    assert policy.music_policy == MusicPolicy.REQUIRED
    assert policy.speech_policy == SpeechPolicy.REQUIRED
    assert policy.ducking_policy == DuckingPolicy.AUTO_DUCKING


def test_source_audio_policy_invariants(engine: AudioModeEngine):
    """Verifies SOURCE_AUDIO invariants: preserves native audio, forbids TTS, no added music."""
    policy = engine.get_policy(AudioMode.SOURCE_AUDIO)
    assert CapabilityType.SPEECH_TO_TEXT in policy.required_capabilities
    assert CapabilityType.TEXT_TO_SPEECH in policy.forbidden_capabilities

    assert policy.music_policy == MusicPolicy.FORBIDDEN
    assert policy.speech_policy == SpeechPolicy.SOURCE_PRESERVED
    assert policy.ducking_policy == DuckingPolicy.DISABLED


def test_source_audio_music_policy_invariants(engine: AudioModeEngine):
    """Verifies SOURCE_AUDIO_MUSIC invariants: preserves native audio with added music bed."""
    policy = engine.get_policy(AudioMode.SOURCE_AUDIO_MUSIC)
    assert CapabilityType.SPEECH_TO_TEXT in policy.required_capabilities
    assert CapabilityType.TEXT_TO_SPEECH in policy.forbidden_capabilities

    assert policy.music_policy == MusicPolicy.REQUIRED
    assert policy.speech_policy == SpeechPolicy.SOURCE_PRESERVED
    assert policy.ducking_policy == DuckingPolicy.AUTO_DUCKING


# -----------------------------------------------------------------------------
# 2. Hard Negative Requirements Enforcement
# -----------------------------------------------------------------------------
def test_negative_silent_adds_bgm_fails(engine: AudioModeEngine):
    """Negative Requirement: SILENT adds BGM -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.enforce_audio_action(AudioMode.SILENT, "add_background_music")
    assert "violated SILENT audio policy" in str(exc_info.value)


def test_negative_music_only_invokes_tts_fails(engine: AudioModeEngine):
    """Negative Requirement: MUSIC_ONLY invokes TTS -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.assert_capability_allowed(AudioMode.MUSIC_ONLY, CapabilityType.TEXT_TO_SPEECH)
    assert "strictly FORBIDDEN under audio mode 'MUSIC_ONLY'" in str(exc_info.value)


def test_negative_silent_invokes_tts_fails(engine: AudioModeEngine):
    """Negative Requirement: SILENT invokes TTS -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.assert_capability_allowed(AudioMode.SILENT, CapabilityType.TEXT_TO_SPEECH)
    assert "strictly FORBIDDEN under audio mode 'SILENT'" in str(exc_info.value)


def test_negative_vo_only_adds_bgm_fails(engine: AudioModeEngine):
    """Negative Requirement: VO_ONLY adds BGM -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.enforce_audio_action(AudioMode.VO_ONLY, "add_background_music")
    assert "violated VO_ONLY audio policy" in str(exc_info.value)


def test_negative_source_audio_invokes_tts_fails(engine: AudioModeEngine):
    """Negative Requirement: SOURCE_AUDIO invokes TTS -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.assert_capability_allowed(AudioMode.SOURCE_AUDIO, CapabilityType.TEXT_TO_SPEECH)
    assert "strictly FORBIDDEN under audio mode 'SOURCE_AUDIO'" in str(exc_info.value)

    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.enforce_audio_action(AudioMode.SOURCE_AUDIO, "invoke_tts")
    assert "violated SOURCE_AUDIO audio policy" in str(exc_info.value)


def test_negative_source_audio_adds_bgm_fails(engine: AudioModeEngine):
    """Negative Requirement: SOURCE_AUDIO adds BGM -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.enforce_audio_action(AudioMode.SOURCE_AUDIO, "add_background_music")
    assert "violated SOURCE_AUDIO audio policy" in str(exc_info.value)


def test_negative_source_audio_music_invokes_tts_fails(engine: AudioModeEngine):
    """Negative Requirement: SOURCE_AUDIO_MUSIC invokes TTS -> FAIL."""
    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.assert_capability_allowed(AudioMode.SOURCE_AUDIO_MUSIC, CapabilityType.TEXT_TO_SPEECH)
    assert "strictly FORBIDDEN under audio mode 'SOURCE_AUDIO_MUSIC'" in str(exc_info.value)

    with pytest.raises(AudioPolicyViolationError) as exc_info:
        engine.enforce_audio_action(AudioMode.SOURCE_AUDIO_MUSIC, "synthesize_speech")
    assert "violated SOURCE_AUDIO_MUSIC audio policy" in str(exc_info.value)


def test_vo_music_policy_allowances(engine: AudioModeEngine):
    """Verifies VO_MUSIC allows TTS and speech alignment, and permits BGM."""
    assert engine.is_capability_allowed(AudioMode.VO_MUSIC, CapabilityType.TEXT_TO_SPEECH)
    assert engine.is_capability_allowed(AudioMode.VO_MUSIC, CapabilityType.SPEECH_ALIGNMENT)
    # Should not raise
    engine.assert_capability_allowed(AudioMode.VO_MUSIC, CapabilityType.TEXT_TO_SPEECH)


def test_exhaustive_six_modes_policy_matrix(engine: AudioModeEngine):
    """
    Exhaustively verifies that all 6 canonical modes define the complete 8-dimension policy:
    1. required_capabilities
    2. optional_capabilities
    3. forbidden_capabilities
    4. caption_policy
    5. music_policy
    6. mix_policy
    7. ducking_policy
    8. speech_policy
    """
    for mode in AudioMode:
        policy = engine.get_policy(mode)
        assert isinstance(policy.required_capabilities, list)
        assert isinstance(policy.optional_capabilities, list)
        assert isinstance(policy.forbidden_capabilities, list)
        assert policy.caption_policy in CaptionPolicy
        assert policy.music_policy in MusicPolicy
        assert policy.mix_policy in MixPolicy
        assert policy.ducking_policy in DuckingPolicy
        assert policy.speech_policy in SpeechPolicy


# -----------------------------------------------------------------------------
# 3. Recipe Eligibility Enforcement
# -----------------------------------------------------------------------------
def test_recipe_eligibility_music_only_disqualifies_tts(engine: AudioModeEngine):
    """Verifies that a recipe requiring TEXT_TO_SPEECH (like avatar-explainer) is ineligible under MUSIC_ONLY."""
    registry = RecipeRegistry()
    avatar_recipe = registry.get("avatar-explainer")

    is_eligible, reason = engine.check_recipe_eligibility(AudioMode.MUSIC_ONLY, avatar_recipe)
    assert not is_eligible
    assert "does not support audio mode 'MUSIC_ONLY'" in reason or "requires capability 'TEXT_TO_SPEECH' which is forbidden" in reason


def test_recipe_eligibility_unsupported_audio_mode(engine: AudioModeEngine):
    """Verifies that a recipe listing only VO_MUSIC is ineligible under SILENT."""
    registry = RecipeRegistry()
    review_recipe = registry.get("review-conquest-compilation")

    is_eligible, reason = engine.check_recipe_eligibility(AudioMode.SILENT, review_recipe)
    assert not is_eligible
    assert "does not support audio mode 'SILENT'" in reason

