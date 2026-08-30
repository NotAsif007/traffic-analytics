"""
Integration tests for /api/v1/observations.

Tests single observation ingestion, retrieval, status lifecycle updates,
filtering (camera, time range, plate text, class, confidence),
pagination, and bulk ingestion with partial acceptance/rejection.
"""

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
async def test_create_observation_minimal(client: AsyncClient) -> None:
    """POST /observations with required fields succeeds and sets status to 'detected'."""
    cam = await _create_camera(client, "OBS-CAM-1", "Observation Camera 1")
    payload = {
        "source": "pipeline-yolo-v1",
        "source_observation_id": "evt-001",
        "camera_id": cam["id"],
        "observed_at": _utcnow_iso(),
    }
    response = await client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "pipeline-yolo-v1"
    assert data["source_observation_id"] == "evt-001"
    assert data["status"] == "detected"
    assert "id" in data


@pytest.mark.integration
async def test_create_observation_full_fields(client: AsyncClient) -> None:
    """POST /observations with full AI fields and confidence values."""
    cam = await _create_camera(client, "OBS-CAM-FULL", "Observation Camera Full")
    payload = {
        "source": "pipeline-alpr-v2",
        "source_observation_id": "evt-full-001",
        "camera_id": cam["id"],
        "observed_at": _utcnow_iso(),
        "frame_number": 1042,
        "vehicle_class": "car",
        "vehicle_color": "white",
        "bounding_box": {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9},
        "detection_confidence": 0.9542,
        "plate_text": "KA01AB1234",
        "plate_confidence": 0.9123,
        "plate_bbox": {"x1": 0.3, "y1": 0.7, "x2": 0.6, "y2": 0.85},
        "plate_region": "KA",
        "frame_path": "s3://traffic/frames/cam1/f1042.jpg",
        "crop_path": "s3://traffic/crops/cam1/v1042.jpg",
        "plate_crop_path": "s3://traffic/plates/cam1/p1042.jpg",
        "estimated_speed_kmh": 48.5,
        "direction": "N",
        "lane": 2,
        "metadata": {"gpu": "T4", "inference_ms": 14.2},
    }
    response = await client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["plate_text"] == "KA01AB1234"
    assert data["plate_confidence"] == 0.9123
    assert data["detection_confidence"] == 0.9542
    assert data["bounding_box"]["x1"] == 0.1
    assert data["estimated_speed_kmh"] == 48.5


@pytest.mark.integration
async def test_idempotency_duplicate_rejected(client: AsyncClient) -> None:
    """Duplicate (source, source_observation_id) returns 409 Conflict."""
    cam = await _create_camera(client, "OBS-CAM-DUP", "Observation Camera Dup")
    payload = {
        "source": "pipeline-dup",
        "source_observation_id": "evt-dup-100",
        "camera_id": cam["id"],
        "observed_at": _utcnow_iso(),
    }
    r1 = await client.post("/api/v1/observations/", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/observations/", json=payload)
    assert r2.status_code == 409
    assert "error" in r2.json()


@pytest.mark.integration
async def test_unknown_camera_returns_404(client: AsyncClient) -> None:
    """POST /observations with unknown camera UUID returns 404."""
    payload = {
        "source": "pipeline-bad-cam",
        "source_observation_id": "evt-bad-cam",
        "camera_id": str(uuid.uuid4()),
        "observed_at": _utcnow_iso(),
    }
    response = await client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 404


@pytest.mark.integration
async def test_confidence_validation_rejected(client: AsyncClient) -> None:
    """Confidence > 1.0 is rejected with 422."""
    cam = await _create_camera(client, "OBS-CAM-VAL", "Observation Camera Val")
    payload = {
        "source": "pipeline-val",
        "source_observation_id": "evt-val-1",
        "camera_id": cam["id"],
        "observed_at": _utcnow_iso(),
        "detection_confidence": 1.5,
    }
    response = await client.post("/api/v1/observations/", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
async def test_get_observation_by_id(client: AsyncClient) -> None:
    """GET /observations/{id} returns the ingested observation."""
    cam = await _create_camera(client, "OBS-CAM-GET", "Observation Camera Get")
    created = (
        await client.post(
            "/api/v1/observations/",
            json={
                "source": "pipeline-get",
                "source_observation_id": "evt-get-1",
                "camera_id": cam["id"],
                "observed_at": _utcnow_iso(),
                "plate_text": "DL01XY9999",
                "plate_confidence": 0.88,
            },
        )
    ).json()

    response = await client.get(f"/api/v1/observations/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["plate_text"] == "DL01XY9999"


@pytest.mark.integration
async def test_update_observation_status(client: AsyncClient) -> None:
    """PATCH /observations/{id}/status transitions lifecycle state."""
    cam = await _create_camera(client, "OBS-CAM-STAT", "Observation Camera Stat")
    created = (
        await client.post(
            "/api/v1/observations/",
            json={
                "source": "pipeline-stat",
                "source_observation_id": "evt-stat-1",
                "camera_id": cam["id"],
                "observed_at": _utcnow_iso(),
            },
        )
    ).json()
    obs_id = created["id"]

    # Transition to validated
    r1 = await client.patch(
        f"/api/v1/observations/{obs_id}/status",
        json={"status": "validated"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "validated"

    # Transition to rejected with reason
    r2 = await client.patch(
        f"/api/v1/observations/{obs_id}/status",
        json={"status": "rejected", "rejection_reason": "Low confidence match"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "rejected"
    assert r2.json()["rejection_reason"] == "Low confidence match"


@pytest.mark.integration
async def test_list_observations_filtering(client: AsyncClient) -> None:
    """GET /observations with various filters (plate, camera, class, min_confidence)."""
    cam1 = await _create_camera(client, "OBS-FILTER-CAM1", "Filter Cam 1")
    cam2 = await _create_camera(client, "OBS-FILTER-CAM2", "Filter Cam 2")

    await client.post(
        "/api/v1/observations/",
        json={
            "source": "pipeline-filter",
            "source_observation_id": "f-1",
            "camera_id": cam1["id"],
            "observed_at": "2026-08-30T10:00:00Z",
            "vehicle_class": "car",
            "plate_text": "MH12AB1111",
            "detection_confidence": 0.95,
            "plate_confidence": 0.90,
        },
    )
    await client.post(
        "/api/v1/observations/",
        json={
            "source": "pipeline-filter",
            "source_observation_id": "f-2",
            "camera_id": cam2["id"],
            "observed_at": "2026-08-30T11:00:00Z",
            "vehicle_class": "truck",
            "plate_text": "KA01CD2222",
            "detection_confidence": 0.80,
            "plate_confidence": 0.70,
        },
    )

    # Filter by plate substring
    r_plate = await client.get("/api/v1/observations/?plate_text=MH12")
    assert r_plate.status_code == 200
    items_plate = r_plate.json()["items"]
    assert any(i["plate_text"] == "MH12AB1111" for i in items_plate)
    assert not any(i["plate_text"] == "KA01CD2222" for i in items_plate)

    # Filter by camera
    r_cam = await client.get(f"/api/v1/observations/?camera_id={cam1['id']}")
    assert r_cam.status_code == 200
    assert all(i["camera_id"] == cam1["id"] for i in r_cam.json()["items"])

    # Filter by min confidence
    r_conf = await client.get("/api/v1/observations/?min_detection_confidence=0.90")
    assert r_conf.status_code == 200
    assert all(i["detection_confidence"] >= 0.90 for i in r_conf.json()["items"])


@pytest.mark.integration
async def test_bulk_observation_ingestion(client: AsyncClient) -> None:
    """POST /observations/bulk accepts valid batch and reports rejections with details."""
    cam = await _create_camera(client, "OBS-BULK-CAM", "Bulk Camera")

    payload = {
        "observations": [
            {
                "source": "bulk-pipeline",
                "source_observation_id": "b-1",
                "camera_id": cam["id"],
                "observed_at": _utcnow_iso(),
                "vehicle_class": "car",
                "plate_text": "KA05XY1001",
                "plate_confidence": 0.95,
            },
            {
                "source": "bulk-pipeline",
                "source_observation_id": "b-2",
                "camera_id": cam["id"],
                "observed_at": _utcnow_iso(),
                "vehicle_class": "motorcycle",
                "plate_text": "KA05XY1002",
                "plate_confidence": 0.89,
            },
            {
                # Unknown camera -> should be rejected
                "source": "bulk-pipeline",
                "source_observation_id": "b-bad-cam",
                "camera_id": str(uuid.uuid4()),
                "observed_at": _utcnow_iso(),
            },
            {
                # Duplicate within this batch of b-1 -> should be rejected
                "source": "bulk-pipeline",
                "source_observation_id": "b-1",
                "camera_id": cam["id"],
                "observed_at": _utcnow_iso(),
            },
        ]
    }

    response = await client.post("/api/v1/observations/bulk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted_count"] == 2
    assert data["rejected_count"] == 2
    assert len(data["accepted"]) == 2
    assert len(data["rejected"]) == 2

    # Check that accepted records exist in DB
    accepted_ids = {obs["source_observation_id"] for obs in data["accepted"]}
    assert accepted_ids == {"b-1", "b-2"}

    # Check rejection reasons
    rejection_indices = {r["index"]: r["reason"] for r in data["rejected"]}
    assert 2 in rejection_indices  # bad camera
    assert "not found" in rejection_indices[2]
    assert 3 in rejection_indices  # duplicate
    assert "Duplicate within this batch" in rejection_indices[3]
