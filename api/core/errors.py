from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from scripts.core.security.permissions import AccessDeniedError, AuthenticationRequiredError
from scripts.core.lifecycle_service import (
    LifecycleError,
    InvalidLifecycleTransitionError,
    LifecyclePreconditionFailedError,
)
from scripts.core.state_store import StateConflictError, StateLockTimeoutError

logger = logging.getLogger("api.errors")

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
    return JSONResponse(
        status_code=403,
        content={
            "status": "error",
            "error": "AccessDenied",
            "message": str(exc),
            "details": {
                "principal_id": exc.principal_id,
                "action": exc.action.value,
                "project_id": exc.project_id,
                "reason": exc.reason
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
            "details": {"reason": str(exc)}
        }
    )
