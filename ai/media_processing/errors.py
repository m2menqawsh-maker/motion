"""
ai/media_processing/errors.py
=============================
Structured failure model and error taxonomy for Media Processing (S28-M06).

Invariants:
- Replaces raw "ffmpeg failed" strings with structured, typed domain exceptions.
- Differentiates specific failure domains (validation, authorization, timeouts, corruption, storage).
- Sanitizes stderr diagnostics to prevent leakage of host paths, environment variables, or credentials.
- Seamlessly maps to canonical AIError and AIErrorCode models.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from ai.contracts.errors import AIError, AIErrorCode


def sanitize_diagnostic_message(msg: str) -> str:
    """Sanitizes diagnostic messages, stripping absolute host paths and credentials."""
    if not msg:
        return ""
    # Strip absolute home paths
    sanitized = re.sub(r"/(?:home|Users|root)/[a-zA-Z0-9_\-\.\u0600-\u06FF/]+", "[INTERNAL_PATH]", msg)
    # Strip Windows absolute paths
    sanitized = re.sub(r"[a-zA-Z]:\\[a-zA-Z0-9_\-\.\\]+", "[INTERNAL_PATH]", sanitized)
    # Strip potential secrets/keys
    sanitized = re.sub(r"(?:api[_-]?key|token|secret)\s*[:=]\s*\S+", "[REDACTED_SECRET]", sanitized, flags=re.IGNORECASE)
    # Cap length to 1000 characters
    if len(sanitized) > 1000:
        sanitized = sanitized[:997] + "..."
    return sanitized


class MediaProcessingError(Exception):
    """Base exception for all media processing operations."""
    DEFAULT_CODE: str = "PROCESS_EXECUTION_FAILED"
    DEFAULT_AI_CODE: AIErrorCode = AIErrorCode.INTERNAL_ERROR
    RETRYABLE: bool = False

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        ai_code: Optional[AIErrorCode] = None,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.DEFAULT_CODE
        self.ai_code = ai_code or self.DEFAULT_AI_CODE
        self.details = details or {}
        self.retryable = retryable if retryable is not None else self.RETRYABLE

    def to_ai_error(self) -> AIError:
        """Converts this exception to a canonical client-safe AIError."""
        safe_msg = sanitize_diagnostic_message(self.message)
        safe_details = {k: str(v) for k, v in self.details.items()} if self.details else None
        return AIError.create(
            code=self.ai_code,
            message=safe_msg,
            retryable=self.retryable,
            details=safe_details,
            dependency_reference="ffmpeg_media_processing",
        )


class InvalidMediaRequestError(MediaProcessingError):
    """Raised when an operation request fails contract or parameter validation."""
    DEFAULT_CODE = "INVALID_MEDIA_REQUEST"
    DEFAULT_AI_CODE = AIErrorCode.SCHEMA_VALIDATION_FAILED
    RETRYABLE = False


class UnsupportedMediaOperationError(MediaProcessingError):
    """Raised when a requested media operation or profile is unsupported."""
    DEFAULT_CODE = "UNSUPPORTED_MEDIA_OPERATION"
    DEFAULT_AI_CODE = AIErrorCode.CAPABILITY_UNAVAILABLE
    RETRYABLE = False


class MediaSourceNotFoundError(MediaProcessingError):
    """Raised when a source media asset cannot be found in storage."""
    DEFAULT_CODE = "SOURCE_NOT_FOUND"
    DEFAULT_AI_CODE = AIErrorCode.POLICY_DENIED
    RETRYABLE = False


class MediaSourceUnauthorizedError(MediaProcessingError):
    """Raised when access to a media asset violates workspace or project tenant boundaries."""
    DEFAULT_CODE = "SOURCE_NOT_AUTHORIZED"
    DEFAULT_AI_CODE = AIErrorCode.TENANT_ACCESS_DENIED
    RETRYABLE = False


class InvalidMediaFileError(MediaProcessingError):
    """Raised when an input media file is malformed, corrupt, or missing expected streams."""
    DEFAULT_CODE = "INVALID_MEDIA"
    DEFAULT_AI_CODE = AIErrorCode.INVALID_MODEL_OUTPUT
    RETRYABLE = False


class FFmpegUnavailableError(MediaProcessingError):
    """Raised when the ffmpeg or ffprobe executable is not found in PATH or environment."""
    DEFAULT_CODE = "FFMPEG_UNAVAILABLE"
    DEFAULT_AI_CODE = AIErrorCode.PROVIDER_UNAVAILABLE
    RETRYABLE = False


class FFprobeFailedError(MediaProcessingError):
    """Raised when ffprobe execution fails or yields unparseable output."""
    DEFAULT_CODE = "FFPROBE_FAILED"
    DEFAULT_AI_CODE = AIErrorCode.DEPENDENCY_FAILED
    RETRYABLE = False


class ProcessTimeoutError(MediaProcessingError):
    """Raised when an FFmpeg process exceeds its allocated execution deadline."""
    DEFAULT_CODE = "PROCESS_TIMEOUT"
    DEFAULT_AI_CODE = AIErrorCode.TIMEOUT
    RETRYABLE = True


class ProcessCancelledError(MediaProcessingError):
    """Raised when an FFmpeg process is cancelled midway by cooperative cancellation."""
    DEFAULT_CODE = "PROCESS_CANCELLED"
    DEFAULT_AI_CODE = AIErrorCode.CANCELLED
    RETRYABLE = False


class ProcessExecutionFailedError(MediaProcessingError):
    """Raised when FFmpeg process exits with non-zero status."""
    DEFAULT_CODE = "PROCESS_EXECUTION_FAILED"
    DEFAULT_AI_CODE = AIErrorCode.DEPENDENCY_FAILED
    RETRYABLE = False


class OutputValidationError(MediaProcessingError):
    """Raised when output file was produced but fails ffprobe deep verification."""
    DEFAULT_CODE = "OUTPUT_VALIDATION_FAILED"
    DEFAULT_AI_CODE = AIErrorCode.INVALID_MODEL_OUTPUT
    RETRYABLE = False


class OutputTooLargeError(MediaProcessingError):
    """Raised when output file size exceeds configured resource limits."""
    DEFAULT_CODE = "OUTPUT_TOO_LARGE"
    DEFAULT_AI_CODE = AIErrorCode.BUDGET_EXCEEDED
    RETRYABLE = False


class StorageFetchFailedError(MediaProcessingError):
    """Raised when fetching source media from StorageService fails."""
    DEFAULT_CODE = "STORAGE_FETCH_FAILED"
    DEFAULT_AI_CODE = AIErrorCode.DEPENDENCY_FAILED
    RETRYABLE = True


class StoragePublishFailedError(MediaProcessingError):
    """Raised when publishing processed media back to StorageService fails."""
    DEFAULT_CODE = "STORAGE_PUBLISH_FAILED"
    DEFAULT_AI_CODE = AIErrorCode.DEPENDENCY_FAILED
    RETRYABLE = True


class ResourceLimitExceededError(MediaProcessingError):
    """Raised when system resource limits (concurrency, memory, disk) are exceeded."""
    DEFAULT_CODE = "RESOURCE_LIMIT_EXCEEDED"
    DEFAULT_AI_CODE = AIErrorCode.BUDGET_EXCEEDED
    RETRYABLE = True


class ProtocolSecurityViolationError(MediaProcessingError):
    """Raised when an unsafe protocol, URL, or traversal path is detected."""
    DEFAULT_CODE = "PROTOCOL_SECURITY_VIOLATION"
    DEFAULT_AI_CODE = AIErrorCode.POLICY_DENIED
    RETRYABLE = False


class CommandInjectionDetectedError(MediaProcessingError):
    """Raised when shell metacharacters or arbitrary flags are passed."""
    DEFAULT_CODE = "COMMAND_INJECTION_DETECTED"
    DEFAULT_AI_CODE = AIErrorCode.POLICY_DENIED
    RETRYABLE = False
