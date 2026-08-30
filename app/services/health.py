"""
Health check service.

Encapsulates all health check logic. The route handler delegates
entirely to this service — no logic in the route itself.

Checks:
- Database connectivity (via raw SQL ping)
- (Phase 2) Redis connectivity
"""

from __future__ import annotations

import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.logging import get_logger
from app.schemas.health import ComponentStatus, HealthResponse

logger = get_logger(__name__)

# Application version — in production, read from a VERSION file or VCS tag.
APP_VERSION = "0.1.0"


class HealthService:
    """
    Performs liveness and readiness checks for the application.

    Injected with an AsyncSession for database connectivity testing.
    """

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def check(self) -> HealthResponse:
        """
        Run all health checks and return a consolidated HealthResponse.

        The overall status is:
        - "ok"          if all components are ok
        - "degraded"    if any component is degraded
        - "unavailable" if any component is unavailable
        """
        db_status = await self._check_database()

        components: dict[str, ComponentStatus] = {
            "database": db_status,
        }

        # Determine overall status based on worst component
        statuses = [c.status for c in components.values()]
        if "unavailable" in statuses:
            overall = "unavailable"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "ok"

        return HealthResponse(
            status=overall,
            version=APP_VERSION,
            environment=self._settings.APP_ENV,
            components=components,
        )

    async def _check_database(self) -> ComponentStatus:
        """
        Ping the database with a trivial query and measure latency.

        Returns ComponentStatus with latency_ms on success, or
        status="unavailable" with an error detail on failure.
        """
        start = time.perf_counter()
        try:
            await self._session.execute(text("SELECT 1"))
            latency_ms = (time.perf_counter() - start) * 1000
            logger.debug("health.database.ok", latency_ms=round(latency_ms, 2))
            return ComponentStatus(
                status="ok",
                latency_ms=round(latency_ms, 2),
                detail="PostgreSQL connection established.",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.warning("health.database.unavailable", error=str(exc))
            return ComponentStatus(
                status="unavailable",
                latency_ms=round(latency_ms, 2),
                detail=f"Database unreachable: {exc}",
            )
