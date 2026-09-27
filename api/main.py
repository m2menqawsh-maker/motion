import os
import logging
from contextlib import asynccontextmanager
from scripts.security.path_security import validate_project_id
from scripts.security.security import safe_subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import projects, gates, render, brand, blueprint
from api.core.errors import (
    APIError,
    api_error_handler,
    global_exception_handler,
    authentication_required_handler,
    access_denied_handler,
)
from scripts.core.security.permissions import AccessDeniedError, AuthenticationRequiredError
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


app = FastAPI(title="Clean Video Workspace API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(gates.router, prefix="/gates", tags=["gates"])
app.include_router(render.router, prefix="/render", tags=["render"])
app.include_router(brand.router, prefix="/brand", tags=["brand"])
app.include_router(blueprint.router, prefix="/blueprint", tags=["blueprint"])

# Security & Exception Handlers
app.add_exception_handler(AuthenticationRequiredError, authentication_required_handler)
app.add_exception_handler(AccessDeniedError, access_denied_handler)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, global_exception_handler)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
