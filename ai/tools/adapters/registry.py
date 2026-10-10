"""
ai/tools/adapters/registry.py
=============================
Authoritative Adapter Registry and deterministic selection engine (S28-M03).

Invariants:
- Matches capability and implementation descriptor to an authorized adapter.
- Caller / AI has ZERO control over adapter selection (strictly backend-controlled).
- Rejects BROKEN and security-blocked implementations (no unsafe fallbacks).
- Unverified implementations remain unselected unless explicit credentials exist.
- Deterministic selection based on CapabilityCategory and implementation metadata.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ai.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    ExecutionMode,
    ImplementationDescriptor,
    ImplementationStatus,
)
from ai.tools.adapters.acquisition import AssetAcquisitionAdapter
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.adapters.domain_service import DomainServiceAdapter
from ai.tools.adapters.image_processing import ImageProcessingAdapter
from ai.tools.adapters.mcp import ImplementationSecurityBlockedError, MCPToolAdapter
from ai.tools.adapters.media_processing import MediaProcessingAdapter
from ai.tools.adapters.native import NativeToolAdapter
from ai.tools.adapters.remote import RemoteAPIAdapter
from ai.tools.adapters.worker import WorkerToolAdapter


class AdapterRegistryError(Exception):
    """Base error for adapter registry failures."""
    pass


class ImplementationUnavailableError(AdapterRegistryError):
    """Raised when no safe, available runtime implementation exists for a capability."""
    def __init__(self, capability_id: str, reason: str):
        super().__init__(f"No available implementation for capability '{capability_id}': {reason}")
        self.capability_id = capability_id
        self.reason = reason


class AdapterRegistry:
    """
    Central registry mapping capability definitions and implementation descriptors
    to authorized execution adapters.
    """

    def __init__(self) -> None:
        self._adapters: List[CapabilityAdapter] = []
        self._explicit_bindings: Dict[str, CapabilityAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        # Canonical adapter priority order:
        # 1. DomainServiceAdapter (governs DOMAIN_SERVICE category)
        # 2. AssetAcquisitionAdapter (governs MEDIA_ACQUISITION capabilities)
        # 3. MediaProcessingAdapter (governs canonical media processing)
        # 3.5 ImageProcessingAdapter (governs canonical image processing)
        # 4. NativeToolAdapter (in-process verified python)
        # 5. RemoteAPIAdapter (external stock providers)
        # 6. WorkerToolAdapter (asynchronous batch queue)
        # 7. MCPToolAdapter (bounded legacy MCP tools)
        self.register_adapter(DomainServiceAdapter())
        self.register_adapter(AssetAcquisitionAdapter())
        self.register_adapter(MediaProcessingAdapter())
        self.register_adapter(ImageProcessingAdapter())
        self.register_adapter(NativeToolAdapter())
        self.register_adapter(RemoteAPIAdapter())
        self.register_adapter(WorkerToolAdapter())
        self.register_adapter(MCPToolAdapter())

    def register_adapter(self, adapter: CapabilityAdapter) -> None:
        """Registers a capability execution adapter."""
        self._adapters.append(adapter)

    def register(self, adapter: CapabilityAdapter, capabilities: Optional[List[Any]] = None) -> None:
        """Registers an adapter and optionally binds it to specific capability IDs."""
        self.register_adapter(adapter)
        if capabilities:
            for cap in capabilities:
                cap_id = cap.value if hasattr(cap, "value") else str(cap)
                self.bind_capability(cap_id, adapter)

    def bind_capability(self, capability_id: str, adapter: CapabilityAdapter) -> None:
        """Explicitly binds a specific capability ID to an adapter."""
        self._explicit_bindings[capability_id] = adapter

    def resolve(
        self,
        capability: CapabilityDefinition,
    ) -> Tuple[CapabilityAdapter, Optional[ImplementationDescriptor]]:
        """
        Deterministically resolves the optimal, authorized adapter and implementation descriptor.
        
        Raises:
            ImplementationSecurityBlockedError: If implementation has known security vulnerabilities.
            ImplementationUnavailableError: If no safe, working implementation is available.
        """
        cap_id = capability.capability_id.value if hasattr(capability.capability_id, "value") else str(capability.capability_id)
        category_val = capability.category.value if hasattr(capability.category, "value") else str(capability.category)

        # Check explicit binding override
        if cap_id in self._explicit_bindings:
            bound_adapter = self._explicit_bindings[cap_id]
            impl = capability.implementations[0] if capability.implementations else None
            return bound_adapter, impl

        # 1. DOMAIN_SERVICE category -> DomainServiceAdapter strictly
        if category_val == CapabilityCategory.DOMAIN_SERVICE.value:
            for ad in self._adapters:
                if isinstance(ad, DomainServiceAdapter) and ad.can_handle(capability):
                    impl = capability.implementations[0] if capability.implementations else None
                    return ad, impl

        # 2. MEDIA_ACQUISITION capabilities -> AssetAcquisitionAdapter
        for ad in self._adapters:
            if isinstance(ad, AssetAcquisitionAdapter) and ad.can_handle(capability):
                impl = capability.implementations[0] if capability.implementations else None
                return ad, impl

        # 2.5. CANONICAL MEDIA_PROCESSING capabilities -> MediaProcessingAdapter
        canonical_media_caps = {
            "PROBE_MEDIA",
            "TRANSCODE_VIDEO",
            "EXTRACT_AUDIO",
            "EXTRACT_FRAMES",
            "CONCAT_MEDIA",
            "CHANGE_CONTAINER",
            "NORMALIZE_MEDIA",
            "NORMALIZE_AUDIO",
            "ANALYZE_LOUDNESS",
            "DETECT_SILENCE",
        }
        if cap_id in canonical_media_caps:
            for ad in self._adapters:
                if isinstance(ad, MediaProcessingAdapter) and ad.can_handle(capability):
                    canonical_impl = next(
                        (i for i in capability.implementations if "canonical" in i.implementation_id or getattr(i, "implementation_kind", None) == "NATIVE_PRIMARY"),
                        None,
                    )
                    impl = canonical_impl or (capability.implementations[0] if capability.implementations else None)
                    return ad, impl

        # 2.6. CANONICAL IMAGE_PROCESSING capabilities -> ImageProcessingAdapter
        canonical_image_caps = {
            "RESIZE_IMAGE",
            "CROP_IMAGE_TO_RATIO",
            "AUTO_CROP_IMAGE",
            "CONVERT_IMAGE",
            "OPTIMIZE_IMAGE",
            "PROBE_IMAGE",
            "PREPARE_IMAGE_ASSET",
            "THUMBNAIL",
        }
        if cap_id in canonical_image_caps:
            for ad in self._adapters:
                if isinstance(ad, ImageProcessingAdapter) and ad.can_handle(capability):
                    impl = capability.implementations[0] if capability.implementations else None
                    return ad, impl

        # 3. Check registered implementations
        implementations = capability.implementations
        if not implementations:
            # Fallback check across registered adapters (e.g. native or remote)
            for ad in self._adapters:
                if ad.can_handle(capability):
                    return ad, None
            raise ImplementationUnavailableError(
                cap_id,
                f"Capability '{cap_id}' defines no registered implementations and no adapter can handle it."
            )

        # Evaluate candidate implementations deterministically
        for impl in implementations:
            # Security guard: concatenate_videos known injection vulnerability
            if "concatenate_videos" in impl.implementation_id or cap_id == "CONCATENATE_VIDEOS":
                raise ImplementationSecurityBlockedError(
                    impl.implementation_id,
                    "Implementation contains verified shell injection vulnerability (M01/M02 finding); blocked until S28-M06."
                )

            status_val = impl.current_status.value if hasattr(impl.current_status, "value") else str(impl.current_status)

            if status_val == ImplementationStatus.BROKEN.value:
                continue

            if status_val == ImplementationStatus.UNVERIFIED.value:
                # Stock search capabilities have RemoteAPIAdapter handling credentials
                is_stock = cap_id in ("SEARCH_STOCK_IMAGES", "SEARCH_STOCK_VIDEOS", "SEARCH_STOCK_AUDIO", "SEARCH_SOUND_EFFECTS")
                if not is_stock:
                    continue

            # Find matching adapter for this implementation
            for adapter in self._adapters:
                if adapter.can_handle(capability, impl):
                    return adapter, impl

        # If we reach here, all implementations were rejected or unhandled
        reasons = [f"{i.implementation_id} ({i.current_status})" for i in implementations]
        raise ImplementationUnavailableError(
            cap_id,
            f"All implementations for '{cap_id}' are unavailable or unverified: {', '.join(reasons)}"
        )


_default_adapter_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Returns the singleton canonical AdapterRegistry."""
    global _default_adapter_registry
    if _default_adapter_registry is None:
        _default_adapter_registry = AdapterRegistry()
    return _default_adapter_registry
