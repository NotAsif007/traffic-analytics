"""
Integration tests for the Health API endpoints.

These tests require a running PostgreSQL database.
Set TEST_DATABASE_URL in your environment, or use docker-compose to start the DB.

Tests:
- GET /api/v1/health returns 200 with valid JSON structure
- GET /api/v1/health status is "ok" with live database
- GET /api/v1/health/ready returns 200
- GET /api/v1/health components include "database" key
- GET /api/v1/health database component has latency_ms
- API errors return consistent JSON envelope (404 → standard error shape)
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """Health endpoint should always return HTTP 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_response_structure(client: AsyncClient) -> None:
    """Health response should match the expected schema."""
    response = await client.get("/api/v1/health")
    data = response.json()

    assert "status" in data
    assert data["status"] in ("ok", "degraded", "unavailable")
    assert "version" in data
    assert "environment" in data
    assert "components" in data
    assert isinstance(data["components"], dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_database_component_present(client: AsyncClient) -> None:
    """Database component should be present in health response."""
    response = await client.get("/api/v1/health")
    data = response.json()

    assert "database" in data["components"]
    db = data["components"]["database"]
    assert "status" in db
    assert db["status"] in ("ok", "degraded", "unavailable")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_database_ok_with_live_db(client: AsyncClient) -> None:
    """With a live database, database component status should be 'ok'."""
    response = await client.get("/api/v1/health")
    data = response.json()

    assert data["status"] == "ok"
    assert data["components"]["database"]["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_database_latency_recorded(client: AsyncClient) -> None:
    """Database latency_ms should be a non-negative number."""
    response = await client.get("/api/v1/health")
    data = response.json()

    latency = data["components"]["database"]["latency_ms"]
    assert latency is not None
    assert isinstance(latency, (int, float))
    assert latency >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ready_endpoint_returns_200(client: AsyncClient) -> None:
    """Readiness probe should return HTTP 200."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ready_endpoint_structure(client: AsyncClient) -> None:
    """Readiness probe should return status, service, version, environment."""
    response = await client.get("/api/v1/health/ready")
    data = response.json()

    assert data["status"] == "ready"
    assert "service" in data
    assert "version" in data
    assert "environment" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unknown_endpoint_returns_error_envelope(client: AsyncClient) -> None:
    """
    Unknown routes should return a consistent error JSON envelope.

    Verifies that the error handler for HTTPException is properly wired.
    """
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
