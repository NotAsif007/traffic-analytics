"""
Health check endpoints.

GET /api/v1/health
    Full health check including DB connectivity and latency.
    Used by load balancers and monitoring systems to determine service health.

GET /api/v1/health/ready
    Lightweight readiness probe — just verifies the app is up.
    Used by Kubernetes/Docker readiness probes (does not hit DB).

No business logic here — all logic is in app.services.health.HealthService.
"""

from fastapi import APIRouter

from app.api.deps import AppSettings, HealthServiceDep
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Full health check",
    description=(
        "Returns the operational status of the API and all its infrastructure "
        "dependencies (database, etc.). Measures latency of each component."
    ),
    responses={
        200: {"description": "Health status (may be ok, degraded, or unavailable)"},
    },
)
async def health_check(
    service: HealthServiceDep,
) -> HealthResponse:
    """
    Run a full health check against all infrastructure dependencies.

    Always returns HTTP 200 — the 'status' field indicates actual health.
    This allows monitoring tools to read the JSON body rather than relying
    on HTTP status codes.
    """
    return await service.check()


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Lightweight readiness probe. Returns 200 if the application process is running.",
    responses={
        200: {"description": "Application is ready"},
    },
)
async def readiness_probe(settings: AppSettings) -> dict:
    """
    Kubernetes/Docker readiness probe.

    Does not test DB connectivity — just confirms the application process
    is alive and accepting requests. Use /health for full dependency checks.
    """
    return {
        "status": "ready",
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "environment": settings.APP_ENV,
    }
