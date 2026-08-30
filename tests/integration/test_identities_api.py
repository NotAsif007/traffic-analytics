"""Integration tests for VehicleIdentity and VehicleMatch API endpoints."""

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


@pytest.mark.integration
async def test_create_and_retrieve_identity(client: AsyncClient) -> None:
    """POST /identities creates an identity hypothesis and GET /identities/{id} retrieves it."""
    t0 = _utcnow_iso()
    payload = {
        "identity_code": "VID-TEST-001",
        "primary_plate": "KA01AB1234",
        "plate_confidence": 0.94,
        "vehicle_class": "car",
        "vehicle_color": "white",
        "status": "candidate",
        "first_seen_at": t0,
        "last_seen_at": t0,
        "total_sightings": 1,
        "confidence": 0.90,
    }

    create_resp = await client.post("/api/v1/identities/", json=payload)
    assert create_resp.status_code == 201
    ident = create_resp.json()
    assert ident["identity_code"] == "VID-TEST-001"
    assert ident["primary_plate"] == "KA01AB1234"

    get_resp = await client.get(f"/api/v1/identities/{ident['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ident["id"]
    assert "matches" in get_resp.json()


@pytest.mark.integration
async def test_list_identities_filtering(client: AsyncClient) -> None:
    """GET /identities filtering by plate and status."""
    t0 = _utcnow_iso()
    await client.post(
        "/api/v1/identities/",
        json={
            "identity_code": "VID-F1",
            "primary_plate": "MH12CD5678",
            "status": "accepted",
            "first_seen_at": t0,
            "last_seen_at": t0,
        },
    )
    await client.post(
        "/api/v1/identities/",
        json={
            "identity_code": "VID-F2",
            "primary_plate": "DL01XY9999",
            "status": "candidate",
            "first_seen_at": t0,
            "last_seen_at": t0,
        },
    )

    # Filter by plate
    r_plate = await client.get("/api/v1/identities/?primary_plate=MH12")
    assert r_plate.status_code == 200
    items = r_plate.json()["items"]
    assert any(i["identity_code"] == "VID-F1" for i in items)
    assert not any(i["identity_code"] == "VID-F2" for i in items)

    # Filter by status
    r_stat = await client.get("/api/v1/identities/?status=candidate")
    assert r_stat.status_code == 200
    assert all(i["status"] == "candidate" for i in r_stat.json()["items"])


@pytest.mark.integration
async def test_associate_observation_endpoint(client: AsyncClient) -> None:
    """POST /identities/associate runs cross-camera association on an observation."""
    cam = await _create_camera(client, "ASSOC-CAM-1", "Assoc Cam 1")
    obs_resp = await client.post(
        "/api/v1/observations/",
        json={
            "source": "assoc-pipeline",
            "source_observation_id": f"obs-{uuid.uuid4()}",
            "camera_id": cam["id"],
            "observed_at": _utcnow_iso(),
            "plate_text": "AS01AB1234",
            "plate_confidence": 0.95,
            "vehicle_class": "car",
        },
    )
    obs = obs_resp.json()

    assoc_resp = await client.post(
        "/api/v1/identities/associate",
        json={"observation_id": obs["id"]},
    )
    assert assoc_resp.status_code == 200
    data = assoc_resp.json()
    assert "identity" in data
    assert data["identity"]["primary_plate"] == "AS01AB1234"


@pytest.mark.integration
async def test_list_matches_endpoint(client: AsyncClient) -> None:
    """GET /matches lists association matches."""
    response = await client.get("/api/v1/matches/")
    assert response.status_code == 200
    assert "items" in response.json()
