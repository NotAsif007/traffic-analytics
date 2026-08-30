"""Integration tests for Alert and Blacklist API endpoints."""

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_blacklist_crud_endpoints(client: AsyncClient) -> None:
    """POST /blacklist creates an entry and GET /blacklist retrieves it."""
    payload = {
        "plate_text": "KA04XY9999",
        "reason": "Stolen vehicle bolo report",
        "priority": "critical",
        "is_active": True,
    }
    create_resp = await client.post("/api/v1/blacklist/", json=payload)
    assert create_resp.status_code == 201
    entry = create_resp.json()
    assert entry["plate_text"] == "KA04XY9999"
    assert entry["priority"] == "critical"

    # List
    list_resp = await client.get("/api/v1/blacklist/?plate_text=KA04")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) >= 1

    # Update
    patch_resp = await client.patch(
        f"/api/v1/blacklist/{entry['id']}",
        json={"priority": "high", "notes": "Updated case number"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["priority"] == "high"


@pytest.mark.integration
async def test_list_alerts_endpoint(client: AsyncClient) -> None:
    """GET /alerts returns paginated alert response."""
    response = await client.get("/api/v1/alerts/")
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()


@pytest.mark.integration
async def test_get_nonexistent_alert_returns_404(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/alerts/{fake_id}")
    assert response.status_code == 404
