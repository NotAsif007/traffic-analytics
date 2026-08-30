"""Integration tests for Trajectory and Vehicle Trajectory API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _create_camera(client: AsyncClient, camera_id: str, name: str) -> dict:
    r = await client.post(
        "/api/v1/cameras/", json={"camera_id": camera_id, "name": name}
    )
    assert r.status_code == 201, r.json()
    return r.json()


async def _create_identity(client: AsyncClient, code: str, plate: str) -> dict:
    t0 = _utcnow_iso()
    r = await client.post(
        "/api/v1/identities/",
        json={
            "identity_code": code,
            "primary_plate": plate,
            "status": "accepted",
            "first_seen_at": t0,
            "last_seen_at": t0,
        },
    )
    assert r.status_code == 201, r.json()
    return r.json()


@pytest.mark.integration
async def test_list_trajectories_endpoint(client: AsyncClient) -> None:
    """GET /trajectories returns paginated response."""
    response = await client.get("/api/v1/trajectories/")
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()


@pytest.mark.integration
async def test_list_vehicle_trajectories_endpoint(client: AsyncClient) -> None:
    """GET /vehicles/{identity_id}/trajectories returns trajectories for identity."""
    ident = await _create_identity(client, "VID-TRJ-001", "AS01AB1234")
    response = await client.get(f"/api/v1/vehicles/{ident['id']}/trajectories")
    assert response.status_code == 200
    assert "items" in response.json()


@pytest.mark.integration
async def test_get_nonexistent_trajectory_returns_404(client: AsyncClient) -> None:
    """GET /trajectories/{id} returns 404 for unknown trajectory."""
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/trajectories/{fake_id}")
    assert response.status_code == 404
