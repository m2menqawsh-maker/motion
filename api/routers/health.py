"""
api/routers/health.py — Health, Liveness & Readiness Probing Router (S23 - LED-073).

Endpoints:
- GET /health/live: Ultra-fast process liveness probe (200 OK).
- GET /health/ready: Deep, bounded dependency readiness probe (200 OK when ready, 503 when degraded/missing dependencies).
- GET /health: Backward-compatible legacy adapter.
"""

from fastapi import APIRouter, Response, status
from api.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Process Liveness Probe",
)
async def liveness_probe():
    """
    Lightweight probe: Returns 200 if the API process is alive and responsive.
    Does not perform external or filesystem operations.
    """
    return HealthService.check_liveness()


@router.get(
    "/health/ready",
    summary="Workload Readiness Probe",
)
async def readiness_probe(response: Response):
    """
    Readiness probe: Deep dependency health check.
    Returns 200 when ready to accept video workloads, 503 when critical dependencies fail.
    """
    is_ready, details = HealthService.check_readiness()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response.status_code = status.HTTP_200_OK
    return details


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Legacy Health Endpoint Adapter",
)
async def legacy_health_adapter():
    """
    Backwards-compatible legacy health adapter.
    """
    live = HealthService.check_liveness()
    is_ready, _ = HealthService.check_readiness()
    return {
        "status": "healthy" if is_ready else "degraded",
        "version": live["version"],
        "live": True,
        "ready": is_ready,
    }
