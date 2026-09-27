from fastapi import Request
from fastapi.responses import JSONResponse
import logging
from scripts.core.security.permissions import AccessDeniedError, AuthenticationRequiredError
from scripts.core.lifecycle_service import (
    LifecycleError,
    InvalidLifecycleTransitionError,
    LifecyclePreconditionFailedError,
)

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
            message=f"Invalid stage or gate: {gate}",
            status_code=400,
            details={"gate": gate}
        )

class PipelineRunningError(APIError):
    def __init__(self, project_id: str):
        super().__init__(
            message=f"Pipeline is already running for {project_id}",
            status_code=409,
            details={"project_id": project_id}
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
