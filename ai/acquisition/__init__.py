"""
ai/acquisition package.
Canonical Stock Media Acquisition Platform (S28-M05).
"""

from ai.acquisition.contracts import (
    AcquiredAssetResult,
    AcquisitionDescriptor,
    CommercialUseStatus,
    DownloadVariant,
    LicenseClassification,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)
from ai.acquisition.errors import (
    AcquisitionAuthorizationError,
    AcquisitionError,
    AcquisitionErrorCode,
    AssetImportError,
    DownloadFailedError,
    InvalidProviderResponseError,
    MediaValidationError,
    NoEligibleResultsError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    UnsafeDownloadSourceError,
)
from ai.acquisition.service import (
    AssetAcquisitionService,
    get_asset_acquisition_service,
)

__all__ = [
    "StockMediaType",
    "LicenseClassification",
    "CommercialUseStatus",
    "DownloadVariant",
    "StockCandidate",
    "StockSearchQuery",
    "AcquisitionDescriptor",
    "AcquiredAssetResult",
    "AcquisitionError",
    "AcquisitionErrorCode",
    "ProviderUnavailableError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "InvalidProviderResponseError",
    "NoEligibleResultsError",
    "UnsafeDownloadSourceError",
    "DownloadFailedError",
    "MediaValidationError",
    "AssetImportError",
    "AcquisitionAuthorizationError",
    "AssetAcquisitionService",
    "get_asset_acquisition_service",
]
