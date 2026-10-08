import os
import logging
from contextlib import asynccontextmanager
from scripts.security.path_security import validate_project_id
from scripts.security.security import safe_subprocess
from fastapi import FastAPI
from api.routers import projects, gates, render, brand, blueprint, runs, assets, artifacts, outputs, health, candidate_reviews, candidate_promotions, authoring
from fastapi.exceptions import RequestValidationError
from api.core.errors import (
    APIError,
    api_error_handler,
    validation_error_handler,
    global_exception_handler,
    authentication_required_handler,
    access_denied_handler,
    tenant_security_error_handler,
    lifecycle_error_handler,
    state_conflict_handler,
    state_lock_timeout_handler,
)
from scripts.core.lifecycle_service import LifecycleError
from scripts.core.state_store import StateConflictError, StateLockTimeoutError
from scripts.core.security.permissions import AccessDeniedError, AuthenticationRequiredError
from scripts.core.database import TenantSecurityError
from scripts.core.security.env_policy import EnvironmentPolicyAuditor

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Production Environment Audit at startup (Item 15)
    target_env = os.environ.get("MOTION_ENV", "development").lower()
    violations = EnvironmentPolicyAuditor.audit_environment(dict(os.environ), target_env=target_env)
    if violations:
        if target_env in ("production", "prod"):
            raise RuntimeError(
                f"FATAL: Production environment contains forbidden variables: {'; '.join(violations)}"
            )
        else:
            logger.warning("Environment audit violations in non-production mode: %s", violations)
    yield


from api.core.config import get_api_settings, DynamicCORSMiddleware

app = FastAPI(title="Clean Video Workspace API", version="1.0.0", lifespan=lifespan)

api_settings = get_api_settings()

app.add_middleware(
    DynamicCORSMiddleware,
    allow_origins=api_settings.cors_allowed_origins,
    allow_credentials=api_settings.cors_allow_credentials,
    allow_methods=api_settings.cors_allow_methods,
    allow_headers=api_settings.cors_allow_headers,
)

app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(runs.router, prefix="/projects", tags=["runs"])
app.include_router(assets.router, prefix="/projects", tags=["assets"])
app.include_router(artifacts.router, prefix="/projects", tags=["artifacts", "review"])
app.include_router(outputs.router, prefix="/projects", tags=["outputs"])
app.include_router(gates.router, prefix="/gates", tags=["gates"])
app.include_router(render.router, prefix="/render", tags=["render"])
app.include_router(brand.router, prefix="/brand", tags=["brand"])
app.include_router(blueprint.router, prefix="/blueprint", tags=["blueprint"])
app.include_router(authoring.router, prefix="/projects", tags=["authoring"])
app.include_router(candidate_reviews.router, prefix="/candidates", tags=["candidates", "review"])
app.include_router(candidate_promotions.router, prefix="/candidates", tags=["candidates", "promotion"])
app.include_router(health.router)

# Security & Exception Handlers
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StateConflictError, state_conflict_handler)
app.add_exception_handler(StateLockTimeoutError, state_lock_timeout_handler)
app.add_exception_handler(LifecycleError, lifecycle_error_handler)
app.add_exception_handler(AuthenticationRequiredError, authentication_required_handler)
app.add_exception_handler(AccessDeniedError, access_denied_handler)
app.add_exception_handler(TenantSecurityError, tenant_security_error_handler)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, global_exception_handler)
