"""
FastAPI dependency injection definitions.

All shared dependencies (database sessions, settings, services) are
defined here and injected into route handlers via Depends().

Route handlers must NEVER import these modules directly — only through DI.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.services.health import HealthService

# ---------------------------------------------------------------------------
# Type aliases for injected dependencies (cleaner route signatures)
# ---------------------------------------------------------------------------

DBSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Service factories
# ---------------------------------------------------------------------------


def get_health_service(
    session: DBSession,
    settings: AppSettings,
) -> HealthService:
    """Construct and return a HealthService with injected dependencies."""
    return HealthService(session=session, settings=settings)


# Annotated type for cleaner injection in route handlers
HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
