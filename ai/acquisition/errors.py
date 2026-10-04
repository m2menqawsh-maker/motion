"""
ai/acquisition/errors.py
========================
Structured domain errors and failure classification for media acquisition (S28-M05).

Invariants:
- Taxonomy distinguishes credential, rate-limit, network, validation, and domain failures.
- Failure codes map directly to canonical AIErrorCode.
- Never reveals sensitive API keys or headers in exception messages or details.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from ai.contracts.errors import AIError, AIErrorCode


class AcquisitionErrorCode(str, Enum):
    """Categorized domain error codes for acquisition subsystem."""
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_AUTH_FAILED = "PROVIDER_AUTH_FAILED"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    INVALID_PROVIDER_RESPONSE = "INVALID_PROVIDER_RESPONSE"
    NO_ELIGIBLE_RESULTS = "NO_ELIGIBLE_RESULTS"
    UNSAFE_DOWNLOAD_SOURCE = "UNSAFE_DOWNLOAD_SOURCE"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    MEDIA_VALIDATION_FAILED = "MEDIA_VALIDATION_FAILED"
    ASSET_IMPORT_FAILED = "ASSET_IMPORT_FAILED"
    STORAGE_FAILED = "STORAGE_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"


class AcquisitionError(Exception):
    """Base domain exception for media acquisition operations."""

    def __init__(
        self,
        code: AcquisitionErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable

    def to_ai_error(self) -> AIError:
        """Converts domain acquisition error to client-safe AIError contract."""
        mapping = {
            AcquisitionErrorCode.PROVIDER_UNAVAILABLE: AIErrorCode.UPSTREAM_UNAVAILABLE,
            AcquisitionErrorCode.PROVIDER_AUTH_FAILED: AIErrorCode.POLICY_DENIED,
            AcquisitionErrorCode.PROVIDER_RATE_LIMITED: AIErrorCode.RESOURCE_EXHAUSTED,
            AcquisitionErrorCode.INVALID_PROVIDER_RESPONSE: AIErrorCode.INVALID_MODEL_OUTPUT,
            AcquisitionErrorCode.NO_ELIGIBLE_RESULTS: AIErrorCode.CAPABILITY_UNAVAILABLE,
            AcquisitionErrorCode.UNSAFE_DOWNLOAD_SOURCE: AIErrorCode.POLICY_DENIED,
            AcquisitionErrorCode.DOWNLOAD_FAILED: AIErrorCode.DEPENDENCY_FAILED,
            AcquisitionErrorCode.MEDIA_VALIDATION_FAILED: AIErrorCode.SCHEMA_VALIDATION_FAILED,
            AcquisitionErrorCode.ASSET_IMPORT_FAILED: AIErrorCode.DEPENDENCY_FAILED,
            AcquisitionErrorCode.STORAGE_FAILED: AIErrorCode.DEPENDENCY_FAILED,
            AcquisitionErrorCode.AUTHORIZATION_FAILED: AIErrorCode.POLICY_DENIED,
        }
        ai_code = mapping.get(self.code, AIErrorCode.INTERNAL_ERROR)
        safe_details = {k: v for k, v in self.details.items() if "key" not in k.lower() and "token" not in k.lower() and "secret" not in k.lower()}
        safe_details["acquisition_error_code"] = self.code.value
        return AIError(
            code=ai_code,
            message=self.message,
            retryable=self.retryable,
            details=safe_details,
        )


class ProviderUnavailableError(AcquisitionError):
    def __init__(self, provider: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=AcquisitionErrorCode.PROVIDER_UNAVAILABLE,
            message=f"Stock provider '{provider}' is unavailable: {reason}",
            details={"provider": provider, "reason": reason, **(details or {})},
            retryable=True,
        )


class ProviderAuthError(AcquisitionError):
    def __init__(self, provider: str, reason: str):
        super().__init__(
            code=AcquisitionErrorCode.PROVIDER_AUTH_FAILED,
            message=f"Authentication failed for provider '{provider}': {reason}",
            details={"provider": provider, "reason": reason},
            retryable=False,
        )


class ProviderRateLimitError(AcquisitionError):
    def __init__(self, provider: str, retry_after_sec: Optional[float] = None):
        super().__init__(
            code=AcquisitionErrorCode.PROVIDER_RATE_LIMITED,
            message=f"Provider '{provider}' rate limit exceeded.",
            details={"provider": provider, "retry_after_sec": retry_after_sec},
            retryable=True,
        )


class InvalidProviderResponseError(AcquisitionError):
    def __init__(self, provider: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=AcquisitionErrorCode.INVALID_PROVIDER_RESPONSE,
            message=f"Provider '{provider}' returned malformed response: {reason}",
            details={"provider": provider, "reason": reason, **(details or {})},
            retryable=False,
        )


class NoEligibleResultsError(AcquisitionError):
    def __init__(self, query: str, total_checked: int, rejection_summary: Dict[str, int]):
        super().__init__(
            code=AcquisitionErrorCode.NO_ELIGIBLE_RESULTS,
            message=f"No candidates satisfied hard constraints for query '{query}'. (Checked {total_checked} items)",
            details={"query": query, "total_checked": total_checked, "rejections": rejection_summary},
            retryable=False,
        )


class UnsafeDownloadSourceError(AcquisitionError):
    def __init__(self, url: str, reason: str):
        super().__init__(
            code=AcquisitionErrorCode.UNSAFE_DOWNLOAD_SOURCE,
            message=f"Refusing download from unsafe source '{url}': {reason}",
            details={"url": url, "reason": reason},
            retryable=False,
        )


class DownloadFailedError(AcquisitionError):
    def __init__(self, url: str, reason: str, status_code: Optional[int] = None):
        super().__init__(
            code=AcquisitionErrorCode.DOWNLOAD_FAILED,
            message=f"Download failed for '{url}': {reason}",
            details={"url": url, "reason": reason, "status_code": status_code},
            retryable=status_code in (500, 502, 503, 504) if status_code else False,
        )


class MediaValidationError(AcquisitionError):
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=AcquisitionErrorCode.MEDIA_VALIDATION_FAILED,
            message=f"Downloaded media payload failed validation: {reason}",
            details={"reason": reason, **(details or {})},
            retryable=False,
        )


class AssetImportError(AcquisitionError):
    def __init__(self, project_id: str, reason: str):
        super().__init__(
            code=AcquisitionErrorCode.ASSET_IMPORT_FAILED,
            message=f"AssetService import failed for project '{project_id}': {reason}",
            details={"project_id": project_id, "reason": reason},
            retryable=False,
        )


class AcquisitionAuthorizationError(AcquisitionError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=AcquisitionErrorCode.AUTHORIZATION_FAILED,
            message=message,
            details=details or {},
            retryable=False,
        )
