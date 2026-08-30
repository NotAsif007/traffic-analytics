"""
FastAPI application factory.

The application is created by create_app() — a factory function, not a module-level
singleton. This enables clean test isolation: each test can call create_app()
to get a fresh application instance with its own DI context.

The module-level `app` variable is used by uvicorn in production.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Startup:
    1. Configure structured logging
    2. Initialise database connection pool
    3. Log startup banner

    Shutdown:
    1. Dispose database connection pool
    """
    settings: Settings = app.state.settings
    configure_logging(settings)
    logger = get_logger(__name__)

    # Startup
    logger.info(
        "application.starting",
        name=settings.APP_NAME,
        env=settings.APP_ENV,
        version="0.1.0",
    )
    init_db(settings)
    logger.info("database.pool.initialised", url=str(settings.DATABASE_URL).split("@")[-1])

    yield  # Application runs here

    # Shutdown
    logger.info("application.stopping")
    await close_db()
    logger.info("database.pool.disposed")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Application factory.

    Parameters
    ----------
    settings : Settings | None
        If provided, these settings override the default get_settings() singleton.
        Used in tests to inject test-specific configuration.
    """
    _settings = settings or get_settings()

    app = FastAPI(
        title="Traffic Analytics API",
        description=(
            "City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking "
            "and Urban Traffic Analytics.\n\n"
            "PS 26127 — SIH 2026"
        ),
        version="0.1.0",
        docs_url=f"{_settings.API_V1_PREFIX}/docs",
        redoc_url=f"{_settings.API_V1_PREFIX}/redoc",
        openapi_url=f"{_settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # Store settings on app.state for access in lifespan and middleware
    app.state.settings = _settings

    # -----------------------------------------------------------------------
    # Middleware
    # -----------------------------------------------------------------------
    if _settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # -----------------------------------------------------------------------
    # Exception handlers
    # -----------------------------------------------------------------------
    register_exception_handlers(app)

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    app.include_router(v1_router, prefix=_settings.API_V1_PREFIX)

    return app


# ---------------------------------------------------------------------------
# Module-level app instance for uvicorn
# ---------------------------------------------------------------------------
# uvicorn app.main:app
# Production: uvicorn app.main:app --workers 4
# ---------------------------------------------------------------------------
app = create_app()
