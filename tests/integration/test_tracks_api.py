"""Integration tests for single-camera vehicle tracks API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _create_camera(client: AsyncClient, camera_id: str, name: str) -> dict:
    r = await client.post("/api/v1/cameras/", json={"camera_id": camera_id, "name": name})
    assert r.status_code == 201, r.json()
    return r.json()


@pytest.mark.integration
async def test_create_and_retrieve_track(client: AsyncClient) -> None:
    """POST /tracks creates a track and GET /tracks/{id} retrieves it."""
    cam = await _create_camera(client, "TRK-CAM-1", "Track Camera 1")
    t0 = _utcnow_iso()

    payload = {
        "track_id": "TRK-001",
        "camera_id": cam["id"],
        "start_time": t0,
        "end_time": t0,
        "status": "active",
        "confidence": 0.94,
        "vehicle_class": "car",
        "best_plate_text": "KA01AB1234",
        "best_plate_confidence": 0.92,
    }

    create_resp = await client.post("/api/v1/tracks/", json=payload)
    assert create_resp.status_code == 201
    track_data = create_resp.json()
    assert track_data["track_id"] == "TRK-001"
    assert track_data["camera_id"] == cam["id"]

    # Retrieve by ID
    get_resp = await client.get(f"/api/v1/tracks/{track_data['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == track_data["id"]
    assert get_resp.json()["track_id"] == "TRK-001"


@pytest.mark.integration
async def test_list_tracks_filtering(client: AsyncClient) -> None:
    """GET /tracks filtering by camera_id and status."""
    cam1 = await _create_camera(client, "TRK-CAM-F1", "Filter Camera 1")
    cam2 = await _create_camera(client, "TRK-CAM-F2", "Filter Camera 2")
    t0 = _utcnow_iso()

    await client.post(
        "/api/v1/tracks/",
        json={
            "track_id": "TRK-F1",
            "camera_id": cam1["id"],
            "start_time": t0,
            "end_time": t0,
            "status": "active",
            "vehicle_class": "car",
        },
    )
    await client.post(
        "/api/v1/tracks/",
        json={
            "track_id": "TRK-F2",
            "camera_id": cam2["id"],
            "start_time": t0,
            "end_time": t0,
            "status": "completed",
            "vehicle_class": "truck",
        },
    )

    # Filter by camera
    r_cam = await client.get(f"/api/v1/tracks/?camera_id={cam1['id']}")
    assert r_cam.status_code == 200
    items = r_cam.json()["items"]
    assert len(items) >= 1
    assert all(t["camera_id"] == cam1["id"] for t in items)

    # Filter by status
    r_stat = await client.get("/api/v1/tracks/?status=completed")
    assert r_stat.status_code == 200
    assert all(t["status"] == "completed" for t in r_stat.json()["items"])


@pytest.mark.integration
async def test_get_camera_tracks(client: AsyncClient) -> None:
    """GET /cameras/{id}/tracks returns tracks local to that camera."""
    cam = await _create_camera(client, "TRK-CAM-LOCAL", "Local Camera")
    t0 = _utcnow_iso()

    await client.post(
        "/api/v1/tracks/",
        json={
            "track_id": "TRK-LOC-1",
            "camera_id": cam["id"],
            "start_time": t0,
            "end_time": t0,
            "status": "active",
        },
    )

    response = await client.get(f"/api/v1/cameras/{cam['id']}/tracks")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert any(t["track_id"] == "TRK-LOC-1" for t in data["items"])


@pytest.mark.integration
async def test_get_track_observations_endpoint(client: AsyncClient) -> None:
    """GET /tracks/{id}/observations returns ordered list of track observations."""
    cam = await _create_camera(client, "TRK-CAM-OBS", "Obs Track Cam")
    t0 = _utcnow_iso()

    create_resp = await client.post(
        "/api/v1/tracks/",
        json={
            "track_id": "TRK-OBS-1",
            "camera_id": cam["id"],
            "start_time": t0,
            "end_time": t0,
            "status": "active",
        },
    )
    track_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/tracks/{track_id}/observations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
