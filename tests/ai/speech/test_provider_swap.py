"""
tests/ai/speech/test_provider_swap.py
=====================================
Mandatory Provider Neutrality Swap Test (S27.14 Rule 9).

Invariants:
- Swapping Provider A with Provider B produces the exact same canonical contract
  without modifying MediaIntelligenceService, domain code, or consumer code.
"""

import io
import math
import struct
import wave
import pytest

from ai.contracts.media import MediaIntelligence, SpeechIntelligence
from ai.media.service import MediaIntelligenceService
from ai.media.technical_probe import TechnicalMediaProbe
from ai.speech.adapter import FakeSpeechProviderA, FakeSpeechProviderB
from scripts.core.media_intelligence_repository import InMemoryMediaIntelligenceRepository
from scripts.core.storage.storage_service import LocalStorageBackend


def create_sample_audio_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        num_samples = 44100 * 5
        frames = bytearray()
        for i in range(num_samples):
            val = int(10000 * math.sin(2 * math.pi * 440 * (i / 44100)))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_provider_swap_produces_same_canonical_contract(tmp_path):
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repository = InMemoryMediaIntelligenceRepository()
    service = MediaIntelligenceService(
        storage_service=storage,
        repository=repository,
        technical_probe=TechnicalMediaProbe(),
    )

    audio_bytes = create_sample_audio_bytes()

    # Step 1: Execute with Provider A (Whisper-style wire format)
    provider_a = FakeSpeechProviderA()
    report_a = await service.analyze_media(
        workspace_id="ws_neutral",
        asset_id="ast_swap_test_a",
        media_bytes=audio_bytes,
        provider_override=provider_a,
    )

    # Step 2: Swap to Provider B (Google-style wire format)
    # Notice: service, domain code, and caller assertions remain identical!
    provider_b = FakeSpeechProviderB()
    report_b = await service.analyze_media(
        workspace_id="ws_neutral",
        asset_id="ast_swap_test_b",
        media_bytes=audio_bytes,
        provider_override=provider_b,
    )

    # Invariant: Both reports are instances of canonical MediaIntelligence
    assert isinstance(report_a, MediaIntelligence)
    assert isinstance(report_b, MediaIntelligence)

    # Invariant: Both contain valid SpeechIntelligence
    assert isinstance(report_a.speech, SpeechIntelligence)
    assert isinstance(report_b.speech, SpeechIntelligence)

    # Invariant: Core semantic fields match canonical types regardless of provider wire differences
    assert report_a.speech.language in ["ar", "ar-EG"]
    assert report_b.speech.language in ["ar", "ar-EG"]

    assert len(report_a.speech.words) > 0
    assert len(report_b.speech.words) > 0

    assert report_a.speech.words[0].text == "الموبايل"
    assert report_b.speech.words[0].text == "الموبايل"

    assert len(report_a.speech.speakers) > 0
    assert len(report_b.speech.speakers) > 0

    # Speaker tags are canonically normalized to neutral SPEAKER_00
    assert report_a.speech.speakers[0].speaker_id == "SPEAKER_00"
    assert report_b.speech.speakers[0].speaker_id == "SPEAKER_00"

    # Both conform to identical serialization schemas
    assert set(report_a.model_dump().keys()) == set(report_b.model_dump().keys())
    assert set(report_a.speech.model_dump().keys()) == set(report_b.speech.model_dump().keys())
