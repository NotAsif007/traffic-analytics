"""
Integration tests for /api/v1/camera-connections.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _create_camera(client: AsyncClient, camera_id: str, name: str) -> dict:
    r = await client.post(
        "/api/v1/cameras/", json={"camera_id": camera_id, "name": name}
    )
    assert r.status_code == 201, r.json()
    return r.json()


@pytest.mark.integration
async def test_create_connection(client: AsyncClient) -> None:
    """POST /camera-connections creates a directed edge."""
    src = await _create_camera(client, "CC-SRC-1", "Source Cam")
    dst = await _create_camera(client, "CC-DST-1", "Dest Cam")

    r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst["id"],
            "min_travel_time_s": 30,
            "max_travel_time_s": 120,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["source_camera_id"] == src["id"]
    assert data["min_travel_time_s"] == 30


@pytest.mark.integration
async def test_self_loop_rejected(client: AsyncClient) -> None:
    """POST /camera-connections with src == dst returns 422."""
    cam = await _create_camera(client, "CC-SELF", "Self Loop Cam")
    r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": cam["id"],
            "destination_camera_id": cam["id"],
            "min_travel_time_s": 30,
            "max_travel_time_s": 120,
        },
    )
    assert r.status_code == 422


@pytest.mark.integration
async def test_invalid_travel_times_rejected(client: AsyncClient) -> None:
    """POST /camera-connections with min > max returns 422."""
    src = await _create_camera(client, "CC-TT-SRC", "TT Source")
    dst = await _create_camera(client, "CC-TT-DST", "TT Dest")
    r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst["id"],
            "min_travel_time_s": 200,
            "max_travel_time_s": 50,
        },
    )
    assert r.status_code == 422


@pytest.mark.integration
async def test_duplicate_connection_conflict(client: AsyncClient) -> None:
    """Creating duplicate directed edge returns 409."""
    src = await _create_camera(client, "CC-DUP-SRC", "Dup Source")
    dst = await _create_camera(client, "CC-DUP-DST", "Dup Dest")
    payload = {
        "source_camera_id": src["id"],
        "destination_camera_id": dst["id"],
        "min_travel_time_s": 30,
        "max_travel_time_s": 120,
    }
    r1 = await client.post("/api/v1/camera-connections/", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/camera-connections/", json=payload)
    assert r2.status_code == 409


@pytest.mark.integration
async def test_nonexistent_camera_returns_404(client: AsyncClient) -> None:
    """POST /camera-connections with unknown camera IDs returns 404."""
    r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": str(uuid.uuid4()),
            "destination_camera_id": str(uuid.uuid4()),
            "min_travel_time_s": 30,
            "max_travel_time_s": 120,
        },
    )
    assert r.status_code == 404


@pytest.mark.integration
async def test_list_connections_filter_by_source(client: AsyncClient) -> None:
    """GET /camera-connections?source_camera_id=X returns connections from X."""
    src = await _create_camera(client, "CC-LST-SRC", "List Source")
    dst1 = await _create_camera(client, "CC-LST-D1", "List Dest 1")
    dst2 = await _create_camera(client, "CC-LST-D2", "List Dest 2")

    await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst1["id"],
            "min_travel_time_s": 30,
            "max_travel_time_s": 90,
        },
    )
    await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst2["id"],
            "min_travel_time_s": 60,
            "max_travel_time_s": 180,
        },
    )

    r = await client.get(f"/api/v1/camera-connections/?source_camera_id={src['id']}")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    assert all(c["source_camera_id"] == src["id"] for c in items)


@pytest.mark.integration
async def test_update_connection(client: AsyncClient) -> None:
    """PATCH /camera-connections/{id} updates travel time."""
    src = await _create_camera(client, "CC-UPD-SRC", "Upd Source")
    dst = await _create_camera(client, "CC-UPD-DST", "Upd Dest")
    create_r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst["id"],
            "min_travel_time_s": 30,
            "max_travel_time_s": 120,
        },
    )
    conn_id = create_r.json()["id"]

    upd_r = await client.patch(
        f"/api/v1/camera-connections/{conn_id}",
        json={"max_travel_time_s": 180, "distance_m": 950.0},
    )
    assert upd_r.status_code == 200
    assert upd_r.json()["max_travel_time_s"] == 180


@pytest.mark.integration
async def test_delete_connection(client: AsyncClient) -> None:
    """DELETE /camera-connections/{id} removes the connection."""
    src = await _create_camera(client, "CC-DEL-SRC", "Del Source")
    dst = await _create_camera(client, "CC-DEL-DST", "Del Dest")
    create_r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst["id"],
            "min_travel_time_s": 30,
            "max_travel_time_s": 120,
        },
    )
    conn_id = create_r.json()["id"]

    del_r = await client.delete(f"/api/v1/camera-connections/{conn_id}")
    assert del_r.status_code == 204

    get_r = await client.get(f"/api/v1/camera-connections/{conn_id}")
    assert get_r.status_code == 404


@pytest.mark.integration
async def test_delete_camera_cascades_connections(client: AsyncClient) -> None:
    """Deleting a camera also deletes its connections (ON DELETE CASCADE)."""
    src = await _create_camera(client, "CC-CAS-SRC", "Cascade Source")
    dst = await _create_camera(client, "CC-CAS-DST", "Cascade Dest")
    create_r = await client.post(
        "/api/v1/camera-connections/",
        json={
            "source_camera_id": src["id"],
            "destination_camera_id": dst["id"],
            "min_travel_time_s": 30,
            "max_travel_time_s": 120,
        },
    )
    conn_id = create_r.json()["id"]

    # Delete the source camera — connection should cascade-delete
    await client.delete(f"/api/v1/cameras/{src['id']}")

    get_r = await client.get(f"/api/v1/camera-connections/{conn_id}")
    assert get_r.status_code == 404
