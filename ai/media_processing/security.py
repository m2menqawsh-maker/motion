"""
ai/media_processing/security.py
===============================
Security guards, protocol verification, and path confinement for Media Processing (S28-M06).

Invariants:
- Blocks arbitrary protocol injection (SSRF / network egress / pipe escapes).
- Blocks shell metacharacters and command injection attempts.
- Enforces strict path confinement and traversal defenses.
- Prevents cross-tenant access to unauthorized assets.
- Sanitizes concat manifests so they are constructed solely from verified worker paths.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import List, Sequence

from ai.media_processing.errors import (
    CommandInjectionDetectedError,
    ProtocolSecurityViolationError,
    MediaSourceUnauthorizedError,
)
from scripts.security.path_security import validate_project_id


# Protocols strictly prohibited from entering FFmpeg inputs
FORBIDDEN_PROTOCOLS = (
    "http://",
    "https://",
    "ftp://",
    "ftps://",
    "file://",
    "file:",
    "concat:",
    "pipe:",
    "pipe",
    "data:",
    "gopher://",
    "rtmp://",
    "rtmps://",
    "rtsp://",
    "tcp://",
    "udp://",
    "hls://",
    "subfile:",
    "crypto:",
)

# Shell metacharacters forbidden in any input argument
SHELL_METACHAR_PATTERN = re.compile(r"[;&|`$<>\n\r]")


def assert_safe_protocol(value: str, field_name: str = "input") -> None:
    """
    Validates that a string does not contain or start with an unauthorized protocol.
    Raises ProtocolSecurityViolationError if any forbidden scheme is detected.
    """
    if not value:
        return
    lower_val = value.lower().strip()
    for proto in FORBIDDEN_PROTOCOLS:
        if lower_val.startswith(proto) or f"://{proto}" in lower_val or f" {proto}" in lower_val:
            raise ProtocolSecurityViolationError(
                f"Protocol violation in {field_name}: scheme '{proto}' is forbidden.",
                details={"field": field_name, "value": value, "violating_protocol": proto},
            )


def assert_no_shell_injection(value: str, field_name: str = "input") -> None:
    """
    Checks that the string contains zero shell metacharacters.
    Raises CommandInjectionDetectedError if shell metacharacters are found.
    """
    if not value:
        return
    if SHELL_METACHAR_PATTERN.search(value):
        raise CommandInjectionDetectedError(
            f"Shell metacharacters detected in {field_name}.",
            details={"field": field_name, "value": value},
        )


def validate_storage_key_confinement(storage_key: str, project_id: str) -> None:
    """
    Validates that a storage key is well-formed, contains no traversal, and belongs to the project.
    """
    validate_project_id(project_id)
    if not storage_key:
        raise ProtocolSecurityViolationError("Storage key cannot be empty.")

    # Check for null byte
    if "\0" in storage_key:
        raise ProtocolSecurityViolationError(
            f"Null byte detected in storage key '{repr(storage_key)}'.",
            details={"storage_key": storage_key},
        )

    # Check for absolute path
    if storage_key.startswith("/"):
        raise ProtocolSecurityViolationError(
            f"Absolute path forbidden in storage key '{storage_key}'.",
            details={"storage_key": storage_key},
        )

    # Check for traversal
    if ".." in storage_key or "\\" in storage_key:
        raise ProtocolSecurityViolationError(
            f"Path traversal detected in storage key '{storage_key}'.",
            details={"storage_key": storage_key},
        )

    # Check protocols
    assert_safe_protocol(storage_key, "storage_key")
    assert_no_shell_injection(storage_key, "storage_key")

    # If key contains project segment, verify it matches authorized project_id
    segments = storage_key.split("/")
    for idx, seg in enumerate(segments):
        if seg == "projects" and idx + 1 < len(segments):
            key_project = segments[idx + 1]
            if key_project != project_id:
                raise MediaSourceUnauthorizedError(
                    f"Storage key belongs to project '{key_project}', but context project is '{project_id}'.",
                    details={"storage_key": storage_key, "authorized_project": project_id, "key_project": key_project},
                )



def assert_safe_local_path(path: Path | str, allowed_root: Path) -> Path:
    """
    Resolves local file path and ensures it remains strictly confined within allowed_root.
    Protects against symlink escapes and directory traversal.
    """
    p = Path(path).resolve()
    root = allowed_root.resolve()

    try:
        p.relative_to(root)
    except ValueError:
        raise ProtocolSecurityViolationError(
            f"Path '{p}' escapes authorized root '{root}'.",
            details={"path": str(p), "allowed_root": str(root)},
        )

    # Check if any component is a symlink pointing outside allowed_root
    curr = p
    while curr != root and curr != curr.parent:
        if curr.is_symlink():
            target = curr.resolve()
            try:
                target.relative_to(root)
            except ValueError:
                raise ProtocolSecurityViolationError(
                    f"Symlink '{curr}' points outside authorized root to '{target}'.",
                    details={"symlink": str(curr), "target": str(target)},
                )
        curr = curr.parent

    return p


def format_safe_concat_manifest_content(file_paths: Sequence[Path | str]) -> str:
    """
    Validates and formats lines for an internal safe FFmpeg concat demuxer manifest.
    Escapes single quotes and validates all input file paths.
    Does not perform filesystem writes directly.
    """
    lines: List[str] = []
    for fp in file_paths:
        p = Path(fp).resolve()
        if not p.exists():
            raise ProtocolSecurityViolationError(f"Concat input file does not exist: '{p}'")
        # Format: file 'path' with single quote escaping
        escaped_str = str(p).replace("'", "'\\''")
        lines.append(f"file '{escaped_str}'")

    return "\n".join(lines) + "\n"

