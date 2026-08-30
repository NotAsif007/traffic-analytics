"""
Integration tests for /api/v1/roads.

Require a real PostgreSQL/PostGIS database.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_create_road(client: AsyncClient) -> None:
    """POST /roads creates a road and returns 201."""
    response = await client.post(
        "/api/v1/roads/",
        json={"name": "MG Road", "road_type": "arterial", "direction": "two_way"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "MG Road"
    assert "id" in data


@pytest.mark.integration
async def test_create_road_with_geometry(client: AsyncClient) -> None:
    """POST /roads with GeoJSON LineString persists geometry."""
    response = await client.post(
        "/api/v1/roads/",
        json={
            "name": "Ring Road",
            "geometry": {
                "type": "LineString",
                "coordinates": [[77.5, 12.9], [77.51, 12.91], [77.52, 12.92]],
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["geometry"] is not None
    assert data["geometry"]["type"] == "LineString"


@pytest.mark.integration
async def test_list_roads_pagination(client: AsyncClient) -> None:
    """GET /roads returns paginated response."""
    for i in range(3):
        await client.post("/api/v1/roads/", json={"name": f"Test Road {i}"})

    response = await client.get("/api/v1/roads/?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "pages" in data
    assert len(data["items"]) <= 2


@pytest.mark.integration
async def test_get_road(client: AsyncClient) -> None:
    """GET /roads/{id} retrieves the created road."""
    create_resp = await client.post(
        "/api/v1/roads/", json={"name": "Retrieve Road Test"}
    )
    road_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/roads/{road_id}")
    assert response.status_code == 200
    assert response.json()["id"] == road_id


@pytest.mark.integration
async def test_get_road_not_found(client: AsyncClient) -> None:
    """GET /roads/{non-existent-id} returns 404."""
    import uuid
    response = await client.get(f"/api/v1/roads/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "error" in response.json()


@pytest.mark.integration
async def test_update_road(client: AsyncClient) -> None:
    """PATCH /roads/{id} updates specified fields only."""
    create_resp = await client.post(
        "/api/v1/roads/", json={"name": "Original Name", "speed_limit_kmh": 60}
    )
    road_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/roads/{road_id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.integration
async def test_delete_road(client: AsyncClient) -> None:
    """DELETE /roads/{id} returns 204 and the road is gone."""
    create_resp = await client.post("/api/v1/roads/", json={"name": "Delete Me"})
    road_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/roads/{road_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/roads/{road_id}")
    assert get_resp.status_code == 404


@pytest.mark.integration
async def test_filter_roads_by_direction(client: AsyncClient) -> None:
    """GET /roads?direction=one_way_forward returns only matching roads."""
    await client.post("/api/v1/roads/", json={"name": "One Way A", "direction": "one_way_forward"})
    await client.post("/api/v1/roads/", json={"name": "Two Way B", "direction": "two_way"})

    response = await client.get("/api/v1/roads/?direction=one_way_forward")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(r["direction"] == "one_way_forward" for r in items)


@pytest.mark.integration
async def test_duplicate_external_id_returns_conflict(client: AsyncClient) -> None:
    """Creating two roads with the same external_id returns 409."""
    await client.post(
        "/api/v1/roads/", json={"name": "Road A", "external_id": "way/999"}
    )
    response = await client.post(
        "/api/v1/roads/", json={"name": "Road B", "external_id": "way/999"}
    )
    assert response.status_code == 409
