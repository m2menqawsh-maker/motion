"""
ai/audio/modes.py
=================
Authoritative Audio Mode Engine and Policy Enforcement (S28-03 DEC-09 / DEC-14).

Guarantees:
- Every canonical AudioMode (MUSIC_ONLY, VO_ONLY, VO_MUSIC, SOURCE_AUDIO, SOURCE_AUDIO_MUSIC, SILENT)
  is a formal, machine-enforced policy defining required, optional, and forbidden capabilities.
- Negative invariants are hard-enforced:
  • MUSIC_ONLY cannot invoke TEXT_TO_SPEECH or DIARIZATION.
  • SILENT cannot add BGM, invoke TTS, or generate music.
- Pre-LLM recipe eligibility check: recipes requiring forbidden capabilities are disqualified before AI reasoning.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
from pydantic import Field

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.recipe import RecipeDefinition


class CaptionPolicy(str, Enum):
    """Governed caption generation and styling policy."""
    FORBIDDEN = "FORBIDDEN"                    # No speech subtitles/captions permitted
    OPTIONAL = "OPTIONAL"                      # Captions may be generated if requested
    REQUIRED = "REQUIRED"                      # Captions are mandatory
    FROM_TRANSCRIPTION = "FROM_TRANSCRIPTION"  # Captions extracted directly from source audio


class MusicPolicy(str, Enum):
    """Governed background music (BGM) policy."""
    FORBIDDEN = "FORBIDDEN"  # Background music is strictly prohibited
    OPTIONAL = "OPTIONAL"    # Background music may be included
    REQUIRED = "REQUIRED"    # Background music must be present


class MixPolicy(str, Enum):
    """Governed audio bus and mix architecture policy."""
    NONE = "NONE"                          # Completely muted master track
    MUSIC_BED_ONLY = "MUSIC_BED_ONLY"      # Single normalized music track (no speech bus)
    SPEECH_ONLY = "SPEECH_ONLY"            # Spoken voiceover without background music
    SPEECH_AND_MUSIC = "SPEECH_AND_MUSIC"  # Dual-bus speech + background music
    SOURCE_DIRECT = "SOURCE_DIRECT"        # Native source audio channel direct
    SOURCE_AND_MUSIC = "SOURCE_AND_MUSIC"  # Native source audio + background music bed


class DuckingPolicy(str, Enum):
    """Governed dynamic audio ducking policy."""
    DISABLED = "DISABLED"          # No ducking applied
    AUTO_DUCKING = "AUTO_DUCKING"  # Music ducks (-12dB to -18dB) dynamically during speech


class SpeechPolicy(str, Enum):
    """Governed speech track handling policy."""
    FORBIDDEN = "FORBIDDEN"                # Speech or voiceover synthesis strictly prohibited
    OPTIONAL = "OPTIONAL"                  # Speech may or may not be present
    REQUIRED = "REQUIRED"                  # Spoken voiceover is mandatory
    SOURCE_PRESERVED = "SOURCE_PRESERVED"  # Source video speech track is preserved and transcribed


class AudioPolicyViolationError(ValueError):
    """Raised when an audio operation or recipe violates the active AudioMode policy."""
    pass


class AudioModePolicy(AIContractModel):
    """Authoritative policy governing capability access, mix architecture, and gating for an AudioMode."""
    audio_mode: strict_enum(AudioMode) = Field(description="Canonical audio mode identifier")
    description: str = Field(description="Human-readable specification of this audio mode")
    required_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Capabilities strictly required by this mode"
    )
    optional_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Capabilities permitted but optional"
    )
    forbidden_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Capabilities strictly forbidden from invocation under this mode"
    )
    caption_policy: strict_enum(CaptionPolicy) = Field(description="Caption generation policy")
    music_policy: strict_enum(MusicPolicy) = Field(description="Background music policy")
    mix_policy: strict_enum(MixPolicy) = Field(description="Master bus mix policy")
    ducking_policy: strict_enum(DuckingPolicy) = Field(description="Audio ducking policy")
    speech_policy: strict_enum(SpeechPolicy) = Field(description="Speech and voiceover policy")


class AudioModeEngine:
    """
    Authoritative runtime engine governing Audio Mode policies, capability validation,
    recipe eligibility, and negative constraint enforcement.
    """

    def __init__(self) -> None:
        self._policies: Dict[AudioMode, AudioModePolicy] = self._build_canonical_policies()

    def _build_canonical_policies(self) -> Dict[AudioMode, AudioModePolicy]:
        """Assembles the canonical S28 audio mode policies."""
        return {
            AudioMode.MUSIC_ONLY: AudioModePolicy(
                audio_mode=AudioMode.MUSIC_ONLY,
                description="Background music-driven visual montage or kinetic typography. Speech and TTS are strictly forbidden.",
                required_capabilities=[CapabilityType.BEAT_DETECTION],
                optional_capabilities=[
                    CapabilityType.MUSIC_GENERATION,
                    CapabilityType.AUDIO_ENHANCE,
                    CapabilityType.AUDIO_DENOISE,
                ],
                forbidden_capabilities=[
                    CapabilityType.TEXT_TO_SPEECH,
                    CapabilityType.DIARIZATION,
                    CapabilityType.SPEECH_ALIGNMENT,
                    CapabilityType.SPEECH_TO_TEXT,
                    CapabilityType.VOICE_ANALYSIS,
                    CapabilityType.LIP_SYNC,
                ],
                caption_policy=CaptionPolicy.FORBIDDEN,
                music_policy=MusicPolicy.REQUIRED,
                mix_policy=MixPolicy.MUSIC_BED_ONLY,
                ducking_policy=DuckingPolicy.DISABLED,
                speech_policy=SpeechPolicy.FORBIDDEN,
            ),
            AudioMode.VO_ONLY: AudioModePolicy(
                audio_mode=AudioMode.VO_ONLY,
                description="Clean, voiceover-only presentation without background music.",
                required_capabilities=[
                    CapabilityType.TEXT_TO_SPEECH,
                    CapabilityType.SPEECH_ALIGNMENT,
                ],
                optional_capabilities=[
                    CapabilityType.AUDIO_ENHANCE,
                    CapabilityType.AUDIO_DENOISE,
                    CapabilityType.VOICE_ANALYSIS,
                ],
                forbidden_capabilities=[
                    CapabilityType.MUSIC_GENERATION,
                ],
                caption_policy=CaptionPolicy.OPTIONAL,
                music_policy=MusicPolicy.FORBIDDEN,
                mix_policy=MixPolicy.SPEECH_ONLY,
                ducking_policy=DuckingPolicy.DISABLED,
                speech_policy=SpeechPolicy.REQUIRED,
            ),
            AudioMode.VO_MUSIC: AudioModePolicy(
                audio_mode=AudioMode.VO_MUSIC,
                description="Standard commercial mix: spoken voiceover with ducked background music.",
                required_capabilities=[
                    CapabilityType.TEXT_TO_SPEECH,
                    CapabilityType.SPEECH_ALIGNMENT,
                ],
                optional_capabilities=[
                    CapabilityType.BEAT_DETECTION,
                    CapabilityType.MUSIC_GENERATION,
                    CapabilityType.AUDIO_ENHANCE,
                    CapabilityType.AUDIO_DENOISE,
                    CapabilityType.VOICE_ANALYSIS,
                    CapabilityType.LIP_SYNC,
                ],
                forbidden_capabilities=[],
                caption_policy=CaptionPolicy.OPTIONAL,
                music_policy=MusicPolicy.REQUIRED,
                mix_policy=MixPolicy.SPEECH_AND_MUSIC,
                ducking_policy=DuckingPolicy.AUTO_DUCKING,
                speech_policy=SpeechPolicy.REQUIRED,
            ),
            AudioMode.SOURCE_AUDIO: AudioModePolicy(
                audio_mode=AudioMode.SOURCE_AUDIO,
                description="Direct preservation of source media spoken audio without external music.",
                required_capabilities=[
                    CapabilityType.SPEECH_TO_TEXT,
                ],
                optional_capabilities=[
                    CapabilityType.AUDIO_DENOISE,
                    CapabilityType.AUDIO_ENHANCE,
                    CapabilityType.SPEECH_ALIGNMENT,
                    CapabilityType.DIARIZATION,
                ],
                forbidden_capabilities=[
                    CapabilityType.TEXT_TO_SPEECH,
                    CapabilityType.MUSIC_GENERATION,
                ],
                caption_policy=CaptionPolicy.FROM_TRANSCRIPTION,
                music_policy=MusicPolicy.FORBIDDEN,
                mix_policy=MixPolicy.SOURCE_DIRECT,
                ducking_policy=DuckingPolicy.DISABLED,
                speech_policy=SpeechPolicy.SOURCE_PRESERVED,
            ),
            AudioMode.SOURCE_AUDIO_MUSIC: AudioModePolicy(
                audio_mode=AudioMode.SOURCE_AUDIO_MUSIC,
                description="Source media spoken audio with background music bed and automatic ducking.",
                required_capabilities=[
                    CapabilityType.SPEECH_TO_TEXT,
                ],
                optional_capabilities=[
                    CapabilityType.BEAT_DETECTION,
                    CapabilityType.MUSIC_GENERATION,
                    CapabilityType.AUDIO_ENHANCE,
                    CapabilityType.AUDIO_DENOISE,
                    CapabilityType.SPEECH_ALIGNMENT,
                    CapabilityType.DIARIZATION,
                ],
                forbidden_capabilities=[
                    CapabilityType.TEXT_TO_SPEECH,
                ],
                caption_policy=CaptionPolicy.FROM_TRANSCRIPTION,
                music_policy=MusicPolicy.REQUIRED,
                mix_policy=MixPolicy.SOURCE_AND_MUSIC,
                ducking_policy=DuckingPolicy.AUTO_DUCKING,
                speech_policy=SpeechPolicy.SOURCE_PRESERVED,
            ),
            AudioMode.SILENT: AudioModePolicy(
                audio_mode=AudioMode.SILENT,
                description="Completely silent visual composition. All audio generation and BGM are strictly prohibited.",
                required_capabilities=[],
                optional_capabilities=[],
                forbidden_capabilities=[
                    CapabilityType.TEXT_TO_SPEECH,
                    CapabilityType.MUSIC_GENERATION,
                    CapabilityType.BEAT_DETECTION,
                    CapabilityType.AUDIO_ENHANCE,
                    CapabilityType.AUDIO_DENOISE,
                    CapabilityType.VOCAL_ISOLATION,
                    CapabilityType.SPEECH_ALIGNMENT,
                    CapabilityType.DIARIZATION,
                    CapabilityType.SPEECH_TO_TEXT,
                    CapabilityType.VOICE_ANALYSIS,
                    CapabilityType.LIP_SYNC,
                ],
                caption_policy=CaptionPolicy.FORBIDDEN,
                music_policy=MusicPolicy.FORBIDDEN,
                mix_policy=MixPolicy.NONE,
                ducking_policy=DuckingPolicy.DISABLED,
                speech_policy=SpeechPolicy.FORBIDDEN,
            ),
        }

    def get_policy(self, mode: AudioMode) -> AudioModePolicy:
        """Retrieves the authoritative AudioModePolicy for the given mode."""
        if mode not in self._policies:
            raise KeyError(f"Unknown audio mode '{mode}'")
        return self._policies[mode]

    def get_all_policies(self) -> Dict[AudioMode, AudioModePolicy]:
        """Returns all configured canonical policies."""
        return dict(self._policies)

    def is_capability_allowed(self, mode: AudioMode, capability: CapabilityType) -> bool:
        """Determines if a capability is permitted under the given AudioMode."""
        policy = self.get_policy(mode)
        return capability not in policy.forbidden_capabilities

    def assert_capability_allowed(self, mode: AudioMode, capability: CapabilityType) -> None:
        """Raises AudioPolicyViolationError if capability is forbidden in the given mode."""
        policy = self.get_policy(mode)
        if capability in policy.forbidden_capabilities:
            raise AudioPolicyViolationError(
                f"Capability '{capability.value}' is strictly FORBIDDEN under audio mode '{mode.value}'. "
                f"Policy constraint: {policy.description}"
            )

    def enforce_audio_action(self, mode: AudioMode, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Enforces runtime audio action invariants (e.g. SILENT adds BGM -> FAIL, MUSIC_ONLY invokes TTS -> FAIL).
        """
        policy = self.get_policy(mode)
        normalized_action = action.lower().strip()

        # Invariant 1: SILENT adds BGM -> FAIL
        if mode == AudioMode.SILENT:
            if normalized_action in ("add_bgm", "add_music", "add_background_music", "bgm", "generate_music", "play_audio", "load_audio"):
                raise AudioPolicyViolationError(
                    f"Action '{action}' violated SILENT audio policy: Background music and audio playback are strictly prohibited."
                )
            if normalized_action in ("invoke_tts", "text_to_speech", "synthesize_speech", "voiceover"):
                raise AudioPolicyViolationError(
                    f"Action '{action}' violated SILENT audio policy: Spoken voiceover is strictly prohibited."
                )

        # Invariant 2: MUSIC_ONLY invokes TTS -> FAIL
        if mode == AudioMode.MUSIC_ONLY:
            if normalized_action in ("invoke_tts", "text_to_speech", "synthesize_speech", "voiceover", "align_speech"):
                raise AudioPolicyViolationError(
                    f"Action '{action}' violated MUSIC_ONLY audio policy: Spoken voiceover and TTS are strictly prohibited."
                )

        # Invariant 3: VO_ONLY & SOURCE_AUDIO forbid background music -> FAIL
        if mode in (AudioMode.VO_ONLY, AudioMode.SOURCE_AUDIO):
            if normalized_action in ("add_bgm", "add_music", "add_background_music", "bgm", "generate_music"):
                raise AudioPolicyViolationError(
                    f"Action '{action}' violated {mode.value} audio policy: Background music is prohibited."
                )

        # Invariant 4: SOURCE_AUDIO adds TTS -> FAIL
        if mode in (AudioMode.SOURCE_AUDIO, AudioMode.SOURCE_AUDIO_MUSIC):
            if normalized_action in ("invoke_tts", "text_to_speech", "synthesize_speech"):
                raise AudioPolicyViolationError(
                    f"Action '{action}' violated {mode.value} audio policy: Source audio modes preserve native speech and forbid TTS."
                )

    def check_recipe_eligibility(
        self,
        mode: AudioMode,
        recipe: RecipeDefinition,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines whether a RecipeDefinition is eligible under the given AudioMode.
        Returns (is_eligible, failure_reason).
        Runs deterministically BEFORE any AI reasoning or ranking.
        """
        policy = self.get_policy(mode)

        # 1. Mode declared in recipe's supported_audio_modes (if explicitly specified)
        if recipe.supported_audio_modes:
            if mode not in recipe.supported_audio_modes:
                return False, f"Recipe '{recipe.recipe_id}' does not support audio mode '{mode.value}' (supported: {[m.value for m in recipe.supported_audio_modes]})"

        # 2. Check forbidden capabilities: if recipe requires any capability forbidden by mode -> INELIGIBLE
        forbidden_set = set(policy.forbidden_capabilities)
        for req_cap in recipe.required_capabilities:
            if req_cap in forbidden_set:
                return False, f"Recipe '{recipe.recipe_id}' requires capability '{req_cap.value}' which is strictly forbidden under audio mode '{mode.value}'"

        # Check stage-level required capabilities
        for stage in recipe.stages:
            for stage_cap in stage.required_capabilities:
                if stage_cap in forbidden_set:
                    return False, f"Recipe '{recipe.recipe_id}' stage '{stage.stage_id}' requires capability '{stage_cap.value}' which is strictly forbidden under audio mode '{mode.value}'"

        return True, None
