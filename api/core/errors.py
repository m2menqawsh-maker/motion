from typing import Optional, List, Any, Dict
import re
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from scripts.core.security.permissions import AccessDeniedError, AuthenticationRequiredError
from scripts.core.database import TenantSecurityError
from scripts.core.lifecycle_service import (
    LifecycleError,
    InvalidLifecycleTransitionError,
    LifecyclePreconditionFailedError,
)
from scripts.core.state_store import StateConflictError, StateLockTimeoutError

logger = logging.getLogger("api.errors")

_WORKSPACE_ID_RE = re.compile(r"ws_[a-zA-Z0-9_\-]+")

def sanitize_denial_text(text: Optional[str]) -> Optional[str]:
    """Redacts internal workspace IDs from user-facing error details."""
    if not text:
        return text
    return _WORKSPACE_ID_RE.sub("[REDACTED_WORKSPACE]", text)

class APIError(Exception):
    """Base class for all API errors."""
    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ProjectNotFoundError(APIError):
    def __init__(self, project_id: str):
        super().__init__(
            message=f"Project {project_id} not found",
            status_code=404,
            details={"project_id": project_id}
        )

class InvalidGateError(APIError):
    def __init__(self, gate: str):
        super().__init__(
            message=f"Invalid gate identifier: '{gate}'",
            status_code=422,
            details={"code": "INVALID_GATE", "gate": gate}
        )

class InvalidStageError(APIError):
    def __init__(self, stage: str):
        super().__init__(
            message=f"Invalid stage identifier: '{stage}'",
            status_code=422,
            details={"code": "INVALID_STAGE", "stage": stage}
        )

class UnsupportedGateOperationError(APIError):
    def __init__(self, operation: str, reason: str = None):
        msg = f"Gate operation '{operation}' is unsupported."
        if reason:
            msg += f" {reason}"
        super().__init__(
            message=msg,
            status_code=422,
            details={"code": "UNSUPPORTED_GATE_OPERATION", "operation": operation, "reason": reason}
        )

class PipelineRunningError(APIError):
    def __init__(self, project_id: str):
        super().__init__(
            message=f"Pipeline is already running for {project_id}",
            status_code=409,
            details={"project_id": project_id}
        )

class RunNotFoundError(APIError):
    def __init__(self, run_id: str, project_id: str = None):
        super().__init__(
            message=f"Run '{run_id}' not found",
            status_code=404,
            details={"code": "RUN_NOT_FOUND", "run_id": run_id, "project_id": project_id}
        )

class IdempotencyConflictError(APIError):
    def __init__(self, idempotency_key: str, message: str = "Idempotency conflict: request payload does not match existing run"):
        super().__init__(
            message=message,
            status_code=409,
            details={"code": "IDEMPOTENCY_CONFLICT", "idempotency_key": idempotency_key}
        )

class RunNotCancellableError(APIError):
    def __init__(self, run_id: str, status: str, message: str = "Run cannot be cancelled in its current state"):
        super().__init__(
            message=message,
            status_code=409,
            details={"code": "RUN_NOT_CANCELLABLE", "run_id": run_id, "status": status}
        )

class RevisionConflictError(APIError):
    def __init__(self, expected_revision: Any, actual_revision: Any, message: str = "Revision conflict detected"):
        super().__init__(
            message=message,
            status_code=409,
            details={"code": "REVISION_CONFLICT", "expected_revision": expected_revision, "actual_revision": actual_revision}
        )

class AssetNotFoundError(APIError):
    def __init__(self, asset_id: str, project_id: Optional[str] = None):
        super().__init__(
            message=f"Asset '{asset_id}' not found",
            status_code=404,
            details={"code": "ASSET_NOT_FOUND", "asset_id": asset_id, "project_id": project_id}
        )

class ArtifactNotFoundError(APIError):
    def __init__(self, artifact_kind: str, project_id: Optional[str] = None):
        super().__init__(
            message=f"Artifact '{artifact_kind}' not found",
            status_code=404,
            details={"code": "ARTIFACT_NOT_FOUND", "artifact_kind": artifact_kind, "project_id": project_id}
        )

class InvalidRangeError(APIError):
    def __init__(self, range_header: str, total_size: int):
        super().__init__(
            message=f"Invalid Range '{range_header}' for content length {total_size}",
            status_code=416,
            details={"code": "INVALID_RANGE", "range": range_header, "total_size": total_size}
        )

class MediaKindNotAllowedError(APIError):
    def __init__(self, media_kind: str, allowed_kinds: List[str]):
        super().__init__(
            message=f"Media kind '{media_kind}' is not allowed. Allowed kinds: {allowed_kinds}",
            status_code=422,
            details={"code": "MEDIA_KIND_NOT_ALLOWED", "media_kind": media_kind, "allowed_kinds": allowed_kinds}
        )

class PayloadTooLargeError(APIError):
    def __init__(self, max_bytes: int, actual_bytes: int):
        super().__init__(
            message=f"Upload payload size ({actual_bytes} bytes) exceeds limit ({max_bytes} bytes)",
            status_code=413,
            details={"code": "PAYLOAD_TOO_LARGE", "max_bytes": max_bytes, "actual_bytes": actual_bytes}
        )


async def authentication_required_handler(request: Request, exc: AuthenticationRequiredError):
    return JSONResponse(
        status_code=401,
        content={
            "status": "error",
            "error": "AuthenticationRequired",
            "message": str(exc),
            "details": {}
        }
    )

async def access_denied_handler(request: Request, exc: AccessDeniedError):
    safe_msg = sanitize_denial_text(str(exc))
    safe_reason = sanitize_denial_text(exc.reason)
    return JSONResponse(
        status_code=403,
        content={
            "status": "error",
            "error": "AccessDenied",
            "message": safe_msg,
            "details": {
                "principal_id": exc.principal_id,
                "action": exc.action.value,
                "project_id": exc.project_id,
                "reason": safe_reason
            }
        }
    )

async def tenant_security_error_handler(request: Request, exc: TenantSecurityError):
    safe_reason = sanitize_denial_text(str(exc))
    return JSONResponse(
        status_code=403,
        content={
            "status": "error",
            "error": "AccessDenied",
            "message": "Access denied across tenant boundary.",
            "details": {
                "reason": safe_reason
            }
        }
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error": "ValidationError",
            "message": "Validation failed for request parameters.",
            "details": {"errors": exc.errors()}
        }
    )

async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

async def lifecycle_error_handler(request: Request, exc: LifecycleError):
    if isinstance(exc, InvalidLifecycleTransitionError):
        status_code = 409
    elif isinstance(exc, LifecyclePreconditionFailedError):
        status_code = 422
    else:
        status_code = 400

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": exc.__class__.__name__,
            "message": str(exc),
            "details": getattr(exc, "__dict__", {}),
        }
    )

async def state_conflict_handler(request: Request, exc: StateConflictError):
    return JSONResponse(
        status_code=409,
        content={
            "status": "error",
            "error": "StateConflict",
            "message": str(exc),
            "details": {
                "code": "STATE_CONFLICT",
                "expected_revision": exc.expected_revision,
                "actual_revision": exc.actual_revision,
            }
        }
    )

async def state_lock_timeout_handler(request: Request, exc: StateLockTimeoutError):
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "error": "StateLockTimeout",
            "message": str(exc),
            "details": {
                "code": "STATE_LOCK_TIMEOUT"
            }
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": "InternalServerError",
            "message": "An unexpected error occurred on the server.",
            "details": {}
        }
    )
