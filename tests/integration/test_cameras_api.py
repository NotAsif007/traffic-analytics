"""
Integration tests for /api/v1/cameras.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _create_road(client: AsyncClient, name: str = "Test Road") -> dict:
    r = await client.post("/api/v1/roads/", json={"name": name})
    assert r.status_code == 201
    return r.json()


@pytest.mark.integration
async def test_create_camera_minimal(client: AsyncClient) -> None:
    """POST /cameras with minimal payload returns 201."""
    response = await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-001", "name": "North Junction"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["camera_id"] == "CAM-001"
    assert data["status"] == "active"


@pytest.mark.integration
async def test_create_camera_with_road(client: AsyncClient) -> None:
    """POST /cameras referencing a road persists the FK."""
    road = await _create_road(client, "Linked Road")
    response = await client.post(
        "/api/v1/cameras/",
        json={
            "camera_id": "CAM-R01",
            "name": "Road Camera",
            "road_id": road["id"],
            "direction": "N",
        },
    )
    assert response.status_code == 201
    assert response.json()["road_id"] == road["id"]


@pytest.mark.integration
async def test_create_camera_invalid_road(client: AsyncClient) -> None:
    """POST /cameras with non-existent road_id returns 404."""
    response = await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-BAD", "name": "Bad Road Cam", "road_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_create_camera_invalid_status(client: AsyncClient) -> None:
    """POST /cameras with invalid status returns 422."""
    response = await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-INV", "name": "Invalid Status", "status": "broken"},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_camera_with_location(client: AsyncClient) -> None:
    """POST /cameras with GeoJSON Point persists location."""
    response = await client.post(
        "/api/v1/cameras/",
        json={
            "camera_id": "CAM-GEO",
            "name": "Geo Camera",
            "location": {"type": "Point", "coordinates": [77.5946, 12.9716]},
        },
    )
    assert response.status_code == 201
    assert response.json()["location"]["type"] == "Point"


@pytest.mark.integration
async def test_duplicate_camera_id_conflict(client: AsyncClient) -> None:
    """POST /cameras with duplicate camera_id returns 409."""
    await client.post("/api/v1/cameras/", json={"camera_id": "CAM-DUP", "name": "First"})
    r = await client.post("/api/v1/cameras/", json={"camera_id": "CAM-DUP", "name": "Second"})
    assert r.status_code == 409


@pytest.mark.integration
async def test_list_cameras_filter_status(client: AsyncClient) -> None:
    """GET /cameras?status=inactive returns only inactive cameras."""
    await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-ACT", "name": "Active Cam", "status": "active"},
    )
    await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-INA", "name": "Inactive Cam", "status": "inactive"},
    )
    r = await client.get("/api/v1/cameras/?status=inactive")
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(c["status"] == "inactive" for c in items)


@pytest.mark.integration
async def test_list_cameras_filter_by_road(client: AsyncClient) -> None:
    """GET /cameras?road_id=<uuid> returns cameras on that road only."""
    road = await _create_road(client, "Filter Road")
    await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-RD1", "name": "Road Cam 1", "road_id": road["id"]},
    )
    await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-RD2", "name": "No Road Cam"},
    )
    r = await client.get(f"/api/v1/cameras/?road_id={road['id']}")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 1
    assert all(c["road_id"] == road["id"] for c in items)


@pytest.mark.integration
async def test_get_camera_not_found(client: AsyncClient) -> None:
    """GET /cameras/{unknown_id} returns 404."""
    r = await client.get(f"/api/v1/cameras/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.integration
async def test_update_camera_status(client: AsyncClient) -> None:
    """PATCH /cameras/{id} updates status field."""
    create = await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-UPD", "name": "Update Test"},
    )
    cam_id = create.json()["id"]
    r = await client.patch(f"/api/v1/cameras/{cam_id}", json={"status": "maintenance"})
    assert r.status_code == 200
    assert r.json()["status"] == "maintenance"


@pytest.mark.integration
async def test_delete_camera(client: AsyncClient) -> None:
    """DELETE /cameras/{id} returns 204 and camera is gone."""
    create = await client.post(
        "/api/v1/cameras/",
        json={"camera_id": "CAM-DEL", "name": "Delete Me"},
    )
    cam_id = create.json()["id"]
    del_r = await client.delete(f"/api/v1/cameras/{cam_id}")
    assert del_r.status_code == 204
    get_r = await client.get(f"/api/v1/cameras/{cam_id}")
    assert get_r.status_code == 404
