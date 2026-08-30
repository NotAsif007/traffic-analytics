"""
Pytest fixtures shared across all tests.

Fixture hierarchy:
    settings          — test-specific Settings (overrides DATABASE_URL etc.)
    engine            — async SQLAlchemy engine pointing at the test DB
    create_tables     — creates/drops all tables around the test session
    db_session        — isolated async session per test (rolled back after)
    test_app          — FastAPI app wired to the test DB
    client            — httpx AsyncClient for making test requests

Environment variables for integration tests:
    TEST_DATABASE_URL         — async DSN for test DB
    TEST_ALEMBIC_DATABASE_URL — sync DSN for test DB (used only if needed)

If these are not set, integration tests are skipped automatically.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

# ---------------------------------------------------------------------------
# Test database DSNs — read from environment
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://traffic_user:traffic_pass@localhost:5432/traffic_test",
)

TEST_ALEMBIC_DATABASE_URL = os.getenv(
    "TEST_ALEMBIC_DATABASE_URL",
    "postgresql+psycopg2://traffic_user:traffic_pass@localhost:5432/traffic_test",
)

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
# Tests that require a real DB are marked `integration`.
# They are skipped if the DB is not reachable.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Settings fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Test-specific settings. Overrides DATABASE_URL to point at test DB."""
    get_settings.cache_clear()  # ensure we don't use cached prod settings
    return Settings(
        APP_NAME="traffic-analytics-test",
        APP_ENV="development",
        DEBUG=True,
        LOG_LEVEL="WARNING",  # suppress noise in tests
        LOG_FORMAT="console",
        DATABASE_URL=TEST_DATABASE_URL,  # type: ignore[arg-type]
        ALEMBIC_DATABASE_URL=TEST_ALEMBIC_DATABASE_URL,
        REDIS_URL="redis://localhost:6379/1",  # type: ignore[arg-type]
        CORS_ORIGINS="",
    )


# ---------------------------------------------------------------------------
# Database fixtures (integration only)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def engine(settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create an async engine for the test database.

    Session-scoped: the engine is shared across all integration tests.
    """
    _engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=False,
        poolclass=NullPool,
    )
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def create_tables(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """
    Create all tables before the test session; drop them after.

    Note: This does NOT run Alembic migrations — it uses SQLAlchemy's
    create_all() for speed. For migration-specific tests, use Alembic directly.
    """
    async with engine.begin() as conn:
        # Enable PostGIS first (required for geometry columns)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    engine: AsyncEngine,
    create_tables: None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an isolated AsyncSession for each test.

    Uses a SAVEPOINT strategy:
    1. Begin a transaction
    2. Create a session bound to that transaction
    3. Each test runs inside a nested SAVEPOINT
    4. ROLLBACK after test — DB state is fully restored

    This is much faster than truncating tables between tests.
    """
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with engine.begin() as conn, factory(bind=conn) as session:
        await session.begin_nested()

        yield session

        await session.rollback()


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_app(settings: Settings, db_session: AsyncSession):
    """
    Return a FastAPI app wired to the test database.

    Overrides the get_db dependency to use the test session.
    """
    app = create_app(settings=settings)

    # Override the DB dependency to inject the test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    return app


@pytest_asyncio.fixture
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client pointing at the test app.

    Uses httpx.AsyncClient with ASGITransport — no real network.
    """
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Convenience fixture: client without DB (for unit-style API tests)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client_no_db(settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client with a minimal app — no real DB.

    Useful for testing error handling, schema validation, and
    endpoints that don't touch the database.
    """
    from unittest.mock import AsyncMock

    from sqlalchemy.ext.asyncio import AsyncSession

    _app = create_app(settings=settings)

    mock_session = AsyncMock(spec=AsyncSession)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    _app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=_app),
        base_url="http://test",
    ) as ac:
        yield ac
