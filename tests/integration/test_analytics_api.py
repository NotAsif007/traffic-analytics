"""Integration tests for Urban Traffic Analytics API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_get_traffic_volume_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/volume?interval=1h")
    assert response.status_code == 200
    data = response.json()
    assert "total_vehicles" in data
    assert "buckets" in data
    assert data["interval"] == "1h"


@pytest.mark.integration
async def test_get_class_distribution_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/class-distribution")
    assert response.status_code == 200
    data = response.json()
    assert "total_classified_vehicles" in data
    assert "distribution" in data


@pytest.mark.integration
async def test_get_density_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/density")
    assert response.status_code == 200
    data = response.json()
    assert "density_veh_per_km" in data
    assert "methodology" in data
    assert "k = q / v_s" in data["methodology"]


@pytest.mark.integration
async def test_get_travel_times_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/travel-times")
    assert response.status_code == 200
    data = response.json()
    assert "pairs" in data


@pytest.mark.integration
async def test_get_congestion_report_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/congestion")
    assert response.status_code == 200
    data = response.json()
    assert "summary_congestion_index" in data
    assert "overall_status" in data


@pytest.mark.integration
async def test_get_od_matrix_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/od-matrix")
    assert response.status_code == 200
    data = response.json()
    assert "total_trips" in data
    assert "matrix" in data


@pytest.mark.integration
async def test_get_routes_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/routes?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "top_routes" in data


@pytest.mark.integration
async def test_get_camera_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/camera-health")
    assert response.status_code == 200
    data = response.json()
    assert "total_cameras" in data
    assert "cameras" in data
