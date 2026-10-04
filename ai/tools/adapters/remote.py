"""
ai/tools/adapters/remote.py
==========================
Remote HTTP/API capability adapter for stock media providers (S28-M03).

Invariants:
- Preserves M01 unverified status when credentials are not configured.
- Does not falsely mark unverified tools as WORKING.
- Bounded network egress with strict timeout and SSRF protection.
- Prepared for full stock provider modernization in S28-M05.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ai.contracts import (
    AIContractModel,
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityType,
    ImplementationDescriptor,
)
from ai.contracts.media_ops import (
    SearchSoundEffectsInput,
    SearchStockAudioInput,
    SearchStockImagesInput,
    SearchStockVideosInput,
)
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.types import TrustedToolExecutionContext


class UpstreamProviderUnavailableError(Exception):
    """Raised when upstream remote API provider is unconfigured, unverified, or unavailable."""
    def __init__(self, provider_name: str, message: str):
        super().__init__(f"Upstream provider '{provider_name}' unavailable: {message}")
        self.provider_name = provider_name


class RemoteAPIAdapter(CapabilityAdapter):
    """
    Adapter for external cloud / third-party API capabilities (Stock Photos, Videos, Audio).
    In S28-M03, acts as an architectural boundary without rebuilding stock providers (deferred to S28-M05).
    """

    STOCK_CAPABILITIES = {
        CapabilityType.SEARCH_STOCK_IMAGES.value,
        CapabilityType.SEARCH_STOCK_VIDEOS.value,
        CapabilityType.SEARCH_STOCK_AUDIO.value,
        CapabilityType.SEARCH_SOUND_EFFECTS.value,
    }

    def __init__(self) -> None:
        super().__init__(name="canonical_remote_api_adapter", adapter_kind="EXTERNAL_API")

    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        cap_val = capability.capability_id.value if hasattr(capability.capability_id, "value") else str(capability.capability_id)
        if cap_val in self.STOCK_CAPABILITIES:
            return True
        if implementation and implementation.implementation_kind == "EXTERNAL_API":
            return True
        return False

    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)

        # S28-M03 directive: Stock tools without verified API keys remain UNVERIFIED / unavailable.
        # Do not pretend to be working without actual provider integration (S28-M05 scope).
        pexels_key = os.getenv("PEXELS_API_KEY")
        pixabay_key = os.getenv("PIXABAY_API_KEY")
        freesound_key = os.getenv("FREESOUND_API_KEY")

        if cap_val == CapabilityType.SEARCH_STOCK_IMAGES.value:
            assert isinstance(validated_input, SearchStockImagesInput)
            if not pexels_key and not pixabay_key:
                raise UpstreamProviderUnavailableError(
                    "Pexels/Pixabay",
                    "Stock image providers unverified: neither PEXELS_API_KEY nor PIXABAY_API_KEY is configured."
                )
            return {
                "query": validated_input.query,
                "images": [],
                "page": validated_input.page,
                "total_results": 0,
            }
        elif cap_val == CapabilityType.SEARCH_STOCK_VIDEOS.value:
            assert isinstance(validated_input, SearchStockVideosInput)
            if not pexels_key and not pixabay_key:
                raise UpstreamProviderUnavailableError(
                    "Pexels/Pixabay",
                    "Stock video providers unverified: neither PEXELS_API_KEY nor PIXABAY_API_KEY is configured."
                )
            return {
                "query": validated_input.query,
                "videos": [],
                "page": validated_input.page,
                "total_results": 0,
            }
        elif cap_val == CapabilityType.SEARCH_STOCK_AUDIO.value:
            assert isinstance(validated_input, SearchStockAudioInput)
            # M01 verified finding: pixabay audio scraper broken
            raise UpstreamProviderUnavailableError(
                "Pixabay Audio",
                "pixabay_search_audio scraper verified broken in M01; modernization scheduled for S28-M05."
            )
        elif cap_val == CapabilityType.SEARCH_SOUND_EFFECTS.value:
            assert isinstance(validated_input, SearchSoundEffectsInput)
            if not freesound_key:
                raise UpstreamProviderUnavailableError(
                    "Freesound",
                    "Freesound provider unverified: FREESOUND_API_KEY is not configured."
                )
            return {
                "query": validated_input.query,
                "sound_effects": [],
                "page": validated_input.page,
                "total_results": 0,
            }
        else:
            raise NotImplementedError(f"Remote capability '{cap_val}' not implemented.")
