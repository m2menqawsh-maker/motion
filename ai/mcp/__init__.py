"""
ai/mcp/__init__.py
==================
Model Context Protocol (MCP) Rationalization and Boundary Subsystem (S27.10).

Provides:
- Authoritative MCP Catalog & Registry of all 6 servers and their operations.
- Security Policy engine enforcing anti-injection, path confinement, anti-SSRF,
  and tenant identity isolation.
- Structured errors mapping to client-safe AIError contracts.
- Safe bounded audit recording.
- Hardened typed adapters for retained media tools.
"""

from __future__ import annotations

from ai.mcp.audit import (
    MCPAuditRecord,
    MCPAuditRecorder,
    default_mcp_audit_recorder,
)
from ai.mcp.catalog import (
    MCPCatalog,
    default_mcp_catalog,
)
from ai.mcp.contracts import (
    AutoCropInput,
    AutoCropOutput,
    CropRatioInput,
    CropRatioOutput,
    DetectBlackFramesInput,
    DetectBlackFramesOutput,
    ExtendAudioInput,
    ExtendAudioOutput,
    ExtendVideoInput,
    ExtendVideoOutput,
    MCPDisposition,
    MCPOperationCategory,
    MCPOperationDefinition,
    MCPOwnershipClass,
    MCPServerDefinition,
    NormalizeLoudnessInput,
    NormalizeLoudnessOutput,
    ResizeVideoInput,
    ResizeVideoOutput,
    TrimAudioInput,
    TrimAudioOutput,
    TrimSilenceInput,
    TrimSilenceOutput,
    TrimVideoInput,
    TrimVideoOutput,
    UpscaleImageInput,
    UpscaleImageOutput,
)
from ai.mcp.errors import (
    MCPDisabledError,
    MCPError,
    MCPException,
    MCPExecutionError,
    MCPNotFoundError,
    MCPOperationNotAllowedError,
    MCPPathTraversalError,
    MCPSecurityViolationError,
    MCPShellInjectionError,
    MCPTimeoutError,
)
from ai.mcp.policy import (
    FORBIDDEN_MODEL_IDENTITY_FIELDS,
    MCPSecurityPolicy,
)
from ai.mcp.adapters import (
    AudioExtendAdapter,
    AudioNormalizeAdapter,
    AudioSilenceAdapter,
    AudioTrimAdapter,
    BaseMCPAdapter,
    ImageAutoCropAdapter,
    ImageCropRatioAdapter,
    ImageUpscaleAdapter,
    VideoBlackFramesAdapter,
    VideoExtendAdapter,
    VideoResizeAdapter,
    VideoTrimAdapter,
    verify_asset_status_parity,
    verify_cache_check_parity,
)
from ai.mcp.compatibility import (
    CompatibilityMCPServer,
    CompatibilityRegistry,
    CompatibilityRequest,
    CompatibilityResponse,
    LegacyToolDescriptor,
    MCPCompatibilityFacade,
    MCPCompatibilityStatus,
    default_compatibility_registry,
    default_compatibility_server,
    get_mcp_compatibility_facade,
)

__all__ = [
    # Catalog & Contracts
    "MCPCatalog",
    "default_mcp_catalog",
    "MCPServerDefinition",
    "MCPOperationDefinition",
    "MCPDisposition",
    "MCPOwnershipClass",
    "MCPOperationCategory",
    # Input/Output Contracts
    "TrimAudioInput",
    "TrimAudioOutput",
    "NormalizeLoudnessInput",
    "NormalizeLoudnessOutput",
    "TrimSilenceInput",
    "TrimSilenceOutput",
    "ExtendAudioInput",
    "ExtendAudioOutput",
    "TrimVideoInput",
    "TrimVideoOutput",
    "ResizeVideoInput",
    "ResizeVideoOutput",
    "ExtendVideoInput",
    "ExtendVideoOutput",
    "DetectBlackFramesInput",
    "DetectBlackFramesOutput",
    "UpscaleImageInput",
    "UpscaleImageOutput",
    "CropRatioInput",
    "CropRatioOutput",
    "AutoCropInput",
    "AutoCropOutput",
    # Policy
    "MCPSecurityPolicy",
    "FORBIDDEN_MODEL_IDENTITY_FIELDS",
    # Audit
    "MCPAuditRecord",
    "MCPAuditRecorder",
    "default_mcp_audit_recorder",
    # Errors
    "MCPError",
    "MCPException",
    "MCPNotFoundError",
    "MCPDisabledError",
    "MCPOperationNotAllowedError",
    "MCPTimeoutError",
    "MCPPathTraversalError",
    "MCPShellInjectionError",
    "MCPSecurityViolationError",
    "MCPExecutionError",
    # Adapters
    "BaseMCPAdapter",
    "AudioTrimAdapter",
    "AudioNormalizeAdapter",
    "AudioSilenceAdapter",
    "AudioExtendAdapter",
    "VideoTrimAdapter",
    "VideoResizeAdapter",
    "VideoExtendAdapter",
    "VideoBlackFramesAdapter",
    "ImageUpscaleAdapter",
    "ImageCropRatioAdapter",
    "ImageAutoCropAdapter",
    "verify_cache_check_parity",
    "verify_asset_status_parity",
    # S28-M09 Compatibility Layer
    "CompatibilityMCPServer",
    "CompatibilityRegistry",
    "CompatibilityRequest",
    "CompatibilityResponse",
    "LegacyToolDescriptor",
    "MCPCompatibilityFacade",
    "MCPCompatibilityStatus",
    "default_compatibility_registry",
    "default_compatibility_server",
    "get_mcp_compatibility_facade",
]
