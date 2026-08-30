"""Integration tests for Command Center Dashboard API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_dashboard_overview_endpoint(client: AsyncClient) -> None:
    """GET /dashboard/overview returns high level operational stats."""
    response = await client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "active_cameras_count" in data
    assert "vehicles_observed_today" in data
    assert "current_traffic_level" in data
    assert "active_alerts_count" in data


@pytest.mark.integration
async def test_dashboard_live_map_endpoint(client: AsyncClient) -> None:
    """GET /dashboard/map returns GIS spatial layers."""
    response = await client.get("/api/v1/dashboard/map")
    assert response.status_code == 200
    data = response.json()
    assert "cameras" in data
    assert "road_segments" in data
    assert "active_trajectories" in data
    assert "active_alerts" in data


@pytest.mark.integration
async def test_dashboard_analytics_summary_endpoint(client: AsyncClient) -> None:
    """GET /dashboard/analytics/summary returns consolidated analytics."""
    response = await client.get("/api/v1/dashboard/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "hourly_volume_trend" in data
    assert "top_congested_corridors" in data


@pytest.mark.integration
async def test_investigate_nonexistent_vehicle_returns_404(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/dashboard/investigate/vehicle/{fake_id}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_investigate_nonexistent_alert_returns_404(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/dashboard/investigate/alert/{fake_id}")
    assert response.status_code == 404
