"""
tests/ai/capabilities/test_capability_registry.py
=================================================
Verification suite for S27.2 Capability Registry.

Invariants:
- All required canonical capabilities are registered and uniquely identified.
- Definitions enforce strict typed metadata (version, contracts, cache, privacy, cost).
- Provider-specific capability tokens are strictly forbidden.
- Unknown and duplicate capabilities trigger structured errors.
- Immutability and deterministic serialization are guaranteed.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from ai.contracts.common import CapabilityType, ExecutionClass
from ai.capabilities import (
    CachePolicy,
    CapabilityDefinition,
    CapabilityPrivacyClass,
    CapabilityRegistry,
    ContractBindingRef,
    CostUnit,
    DuplicateCapabilityError,
    InvalidCapabilityError,
    UnknownCapabilityError,
    create_empty_capability_registry,
    get_capability_registry,
)

REQUIRED_S27_CAPABILITIES = {
    # Core Language & Reasoning
    CapabilityType.REASONING,
    CapabilityType.PLANNING,
    CapabilityType.TEXT_GENERATION,
    CapabilityType.SUMMARIZATION,
    CapabilityType.TRANSLATION,
    # Representation & Retrieval
    CapabilityType.EMBEDDING,
    CapabilityType.MULTIMODAL_EMBEDDING,
    # Audio & Speech
    CapabilityType.SPEECH_TO_TEXT,
    CapabilityType.LANGUAGE_DETECTION,
    CapabilityType.DIARIZATION,
    CapabilityType.SPEECH_ALIGNMENT,
    CapabilityType.TEXT_TO_SPEECH,
    CapabilityType.AUDIO_DENOISE,
    CapabilityType.AUDIO_ENHANCE,
    CapabilityType.VOCAL_ISOLATION,
    CapabilityType.BEAT_DETECTION,
    CapabilityType.MUSIC_GENERATION,
    CapabilityType.VOICE_ANALYSIS,
    # Vision & Visual Understanding
    CapabilityType.VISION,
    CapabilityType.VIDEO_UNDERSTANDING,
    CapabilityType.OCR,
    CapabilityType.SHOT_DETECTION,
    CapabilityType.OBJECT_DETECTION,
    CapabilityType.PERSON_DETECTION,
    CapabilityType.SCENE_CLASSIFICATION,
    CapabilityType.CAPTIONING,
    # Visual Synthesis & Manipulation
    CapabilityType.IMAGE_GENERATION,
    CapabilityType.VIDEO_GENERATION,
    CapabilityType.PERSON_SEGMENTATION,
    CapabilityType.BACKGROUND_REMOVAL,
    CapabilityType.LIP_SYNC,
    CapabilityType.UPSCALE,
}


class TestCapabilityRegistry:

    def test_all_canonical_capabilities_registered(self):
        """Validates that all required S27 capabilities are present in the canonical registry."""
        registry = get_capability_registry()
        assert len(registry) == 32
        for required_cap in REQUIRED_S27_CAPABILITIES:
            assert registry.exists(required_cap), f"Missing required capability: {required_cap}"
            defn = registry.get(required_cap)
            assert defn.id == required_cap

    def test_unique_canonical_ids(self):
        """Ensures that all registered capabilities have strictly unique IDs."""
        registry = get_capability_registry()
        registered_list = registry.list()
        unique_ids = {d.id for d in registered_list}
        assert len(unique_ids) == len(registered_list) == 32

    def test_definitions_have_valid_metadata(self):
        """Verifies that every definition adheres to contract and metadata requirements."""
        registry = get_capability_registry()
        for defn in registry.list():
            # Version
            assert defn.version == "1.0.0"
            # Description
            assert len(defn.description) > 10
            # Contracts
            assert defn.input_contract.contract_id.startswith("ai.contracts.")
            assert defn.input_contract.version == "1.0.0"
            assert defn.output_contract.contract_id.startswith("ai.contracts.")
            assert defn.output_contract.version == "1.0.0"
            # Enums
            assert isinstance(defn.cache_policy, CachePolicy)
            assert isinstance(defn.privacy_class, CapabilityPrivacyClass)
            assert isinstance(defn.cost_unit, CostUnit)
            assert isinstance(defn.execution_tier, ExecutionClass)
            # Media types
            assert len(defn.media_types) >= 1
            for mt in defn.media_types:
                assert mt in {"text", "audio", "image", "video"}

    def test_unknown_capability_fails_clearly(self):
        """Looking up or validating an unknown capability raises UnknownCapabilityError."""
        registry = get_capability_registry()
        with pytest.raises(UnknownCapabilityError) as exc_info:
            registry.get("SUPER_TELEPORTATION")
        assert "Unknown capability 'SUPER_TELEPORTATION'" in str(exc_info.value)
        assert exc_info.value.capability_id == "SUPER_TELEPORTATION"

        assert not registry.exists("SUPER_TELEPORTATION")

    def test_duplicate_registration_rejected(self):
        """Attempting to register a capability with an existing ID raises DuplicateCapabilityError."""
        reg = create_empty_capability_registry()
        defn1 = CapabilityDefinition(
            id=CapabilityType.REASONING,
            version="1.0.0",
            description="First definition",
            input_contract=ContractBindingRef(contract_id="ai.contracts.reasoning.input", version="1.0.0"),
            output_contract=ContractBindingRef(contract_id="ai.contracts.reasoning.output", version="1.0.0"),
            cache_policy=CachePolicy.DETERMINISTIC,
            privacy_class=CapabilityPrivacyClass.PUBLIC_SAFE,
            cost_unit=CostUnit.TOKENS,
            media_types=["text"],
            execution_tier=ExecutionClass.INTERACTIVE,
        )
        defn2 = CapabilityDefinition(
            id=CapabilityType.REASONING,
            version="1.0.0",
            description="Second definition",
            input_contract=ContractBindingRef(contract_id="ai.contracts.reasoning.input", version="1.0.0"),
            output_contract=ContractBindingRef(contract_id="ai.contracts.reasoning.output", version="1.0.0"),
            cache_policy=CachePolicy.DETERMINISTIC,
            privacy_class=CapabilityPrivacyClass.PUBLIC_SAFE,
            cost_unit=CostUnit.TOKENS,
            media_types=["text"],
            execution_tier=ExecutionClass.INTERACTIVE,
        )
        reg.register(defn1)
        with pytest.raises(DuplicateCapabilityError) as exc_info:
            reg.register(defn2)
        assert "REASONING" in str(exc_info.value)

    @pytest.mark.parametrize(
        "vendor_token",
        [
            "openai_chat",
            "anthropic_claude",
            "gemini_flash",
            "elevenlabs_tts",
            "fal_seedance",
            "replicate_sdxl",
            "whisper_transcribe",
        ],
    )
    def test_provider_specific_capability_names_rejected(self, vendor_token: str):
        """Registry actively rejects attempts to register vendor-branded capabilities."""
        reg = create_empty_capability_registry()
        
        # Creating a dynamic mock definition with vendor string
        class MockVendorDef:
            id = vendor_token
            description = "Vendor branded task"

        with pytest.raises(InvalidCapabilityError) as exc_info:
            reg.register(MockVendorDef())  # type: ignore
        assert "violates provider neutrality" in str(exc_info.value)

    def test_frozen_registry_immutability(self):
        """Once frozen, registration mutations are completely blocked."""
        registry = get_capability_registry()
        assert registry.is_frozen
        sample_defn = registry.get(CapabilityType.PLANNING)
        with pytest.raises(RuntimeError) as exc_info:
            registry.register(sample_defn)
        assert "frozen and immutable" in str(exc_info.value)

    def test_deterministic_serialization(self):
        """Capability definitions serialize to JSON deterministically."""
        registry = get_capability_registry()
        all_caps = registry.list()
        
        dump1 = json.dumps([c.model_dump(mode="json") for c in all_caps], sort_keys=True)
        dump2 = json.dumps([c.model_dump(mode="json") for c in all_caps], sort_keys=True)
        assert dump1 == dump2

    def test_contract_binding_semver_validation(self):
        """ContractBindingRef rejects invalid SemVer strings."""
        with pytest.raises(ValidationError):
            ContractBindingRef(contract_id="ai.contracts.test", version="v1.0")

        with pytest.raises(ValidationError):
            ContractBindingRef(contract_id="ai.contracts.test", version="1.0")

        valid = ContractBindingRef(contract_id="ai.contracts.test", version="1.2.3")
        assert valid.version == "1.2.3"
