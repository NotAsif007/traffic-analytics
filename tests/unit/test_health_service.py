"""
Unit tests for HealthService.

These tests do NOT require a real database — the session is mocked.
They verify:
- HealthService returns "ok" when DB responds
- HealthService returns "unavailable" when DB raises an exception
- HealthService correctly sets component latency
- Overall status reflects the worst component status
- Version and environment are correctly propagated

Marked as `unit` — run without any infrastructure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import Settings
from app.schemas.health import HealthResponse
from app.services.health import HealthService


@pytest.fixture
def test_settings() -> Settings:
    """Minimal Settings for unit tests — no real DSNs needed."""
    return Settings(
        APP_NAME="traffic-analytics-test",
        APP_ENV="development",
        DEBUG=False,
        LOG_LEVEL="WARNING",
        LOG_FORMAT="console",
        DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/test",  # type: ignore
        ALEMBIC_DATABASE_URL="postgresql+psycopg2://u:p@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",  # type: ignore
        CORS_ORIGINS="",
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock AsyncSession for unit tests."""
    session = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_ok_when_db_responds(
    test_settings: Settings,
    mock_session: AsyncMock,
) -> None:
    """When the database responds to SELECT 1, overall status should be 'ok'."""
    # Arrange: session.execute() succeeds without raising
    mock_session.execute = AsyncMock(return_value=MagicMock())

    service = HealthService(session=mock_session, settings=test_settings)

    # Act
    result = await service.check()

    # Assert
    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
    assert "database" in result.components
    assert result.components["database"].status == "ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_unavailable_when_db_raises(
    test_settings: Settings,
    mock_session: AsyncMock,
) -> None:
    """When the database raises an exception, component status should be 'unavailable'."""
    # Arrange: session.execute() raises a connection error
    mock_session.execute = AsyncMock(
        side_effect=Exception("could not connect to server")
    )

    service = HealthService(session=mock_session, settings=test_settings)

    # Act
    result = await service.check()

    # Assert
    assert result.status == "unavailable"
    assert result.components["database"].status == "unavailable"
    assert result.components["database"].detail is not None
    assert "could not connect" in result.components["database"].detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_records_latency(
    test_settings: Settings,
    mock_session: AsyncMock,
) -> None:
    """Latency should be recorded and be a non-negative float."""
    mock_session.execute = AsyncMock(return_value=MagicMock())

    service = HealthService(session=mock_session, settings=test_settings)
    result = await service.check()

    latency = result.components["database"].latency_ms
    assert latency is not None
    assert latency >= 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_propagates_version_and_environment(
    test_settings: Settings,
    mock_session: AsyncMock,
) -> None:
    """Version and environment should be passed through from settings."""
    mock_session.execute = AsyncMock(return_value=MagicMock())

    service = HealthService(session=mock_session, settings=test_settings)
    result = await service.check()

    assert result.version == "0.1.0"
    assert result.environment == "development"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_db_is_called_with_select_1(
    test_settings: Settings,
    mock_session: AsyncMock,
) -> None:
    """Verify that the health check executes a real SQL query, not just a no-op."""
    mock_session.execute = AsyncMock(return_value=MagicMock())

    service = HealthService(session=mock_session, settings=test_settings)
    await service.check()

    # The session must have been called at least once
    mock_session.execute.assert_called_once()

    # Verify the SQL text contains "SELECT 1"
    call_args = mock_session.execute.call_args[0][0]
    assert "SELECT 1" in str(call_args)
