"""Integration tests for Real-Time Event Processing API endpoints."""

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_publish_event_endpoint(client: AsyncClient) -> None:
    """POST /events/publish publishes domain event to the bus."""
    payload = {
        "event_type": "VEHICLE_OBSERVED",
        "source": "integration-test-api",
        "payload": {
            "plate_text": "AS01AB1234",
            "camera_id": str(uuid.uuid4()),
        },
        "idempotency_key": f"key-{uuid.uuid4()}",
    }
    response = await client.post("/api/v1/events/publish", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["event_type"] == "VEHICLE_OBSERVED"


@pytest.mark.integration
async def test_dead_letter_endpoint(client: AsyncClient) -> None:
    """GET /events/dead-letter returns dead letter list."""
    response = await client.get("/api/v1/events/dead-letter")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
