"""
Unit tests for VehicleObservation schemas and service.

Tests validation rules, confidence boundaries, and business logic.
No real database — uses mock session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.vehicle_observation import (
    BoundingBox,
    BulkObservationRequest,
    VehicleObservationCreate,
    VehicleObservationStatusUpdate,
)
from app.services.vehicle_observation import VehicleObservationService

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

CAMERA_ID = uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_payload(**kwargs) -> VehicleObservationCreate:
    defaults = {
        "source": "yolov8-test",
        "source_observation_id": "obs-001",
        "camera_id": CAMERA_ID,
        "observed_at": _utcnow(),
    }
    defaults.update(kwargs)
    return VehicleObservationCreate(**defaults)


def _make_obs_orm(**kwargs) -> MagicMock:
    obs = MagicMock()
    obs.id = uuid.uuid4()
    obs.source = kwargs.get("source", "yolov8-test")
    obs.source_observation_id = kwargs.get("source_observation_id", "obs-001")
    obs.camera_id = CAMERA_ID
    obs.observed_at = _utcnow()
    obs.frame_number = None
    obs.vehicle_class = kwargs.get("vehicle_class", "car")
    obs.vehicle_color = None
    obs.bounding_box = None
    obs.detection_confidence = kwargs.get("detection_confidence", 0.95)
    obs.plate_text = kwargs.get("plate_text", "KA01AB1234")
    obs.plate_confidence = kwargs.get("plate_confidence", 0.91)
    obs.plate_bbox = None
    obs.plate_region = None
    obs.frame_path = None
    obs.crop_path = None
    obs.plate_crop_path = None
    obs.embedding_id = None
    obs.embedding_model = None
    obs.estimated_speed_kmh = None
    obs.direction = None
    obs.lane = None
    obs.status = "detected"
    obs.rejection_reason = None
    obs.metadata_ = None
    obs.created_at = _utcnow()
    obs.updated_at = _utcnow()
    return obs


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def obs_service(mock_session: AsyncMock) -> VehicleObservationService:
    return VehicleObservationService(mock_session)


@pytest.fixture
def sample_obs() -> MagicMock:
    return _make_obs_orm()


@pytest.fixture
def sample_camera() -> MagicMock:
    cam = MagicMock()
    cam.id = CAMERA_ID
    return cam


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_bounding_box_valid() -> None:
    """BoundingBox accepts valid normalised coordinates."""
    bb = BoundingBox(x1=0.1, y1=0.1, x2=0.9, y2=0.9)
    assert bb.x1 == 0.1


@pytest.mark.unit
def test_bounding_box_rejects_x2_less_than_x1() -> None:
    """BoundingBox rejects x2 <= x1."""
    with pytest.raises(ValidationError, match="x2 must be greater than x1"):
        BoundingBox(x1=0.8, y1=0.1, x2=0.2, y2=0.9)


@pytest.mark.unit
def test_bounding_box_rejects_y2_less_than_y1() -> None:
    """BoundingBox rejects y2 <= y1."""
    with pytest.raises(ValidationError, match="y2 must be greater than y1"):
        BoundingBox(x1=0.1, y1=0.8, x2=0.9, y2=0.2)


@pytest.mark.unit
def test_bounding_box_rejects_out_of_range() -> None:
    """BoundingBox rejects coordinates outside [0, 1]."""
    with pytest.raises(ValidationError):
        BoundingBox(x1=-0.1, y1=0.0, x2=0.9, y2=0.9)


@pytest.mark.unit
def test_create_observation_rejects_naive_timestamp() -> None:
    """observed_at without timezone info is rejected."""
    with pytest.raises(ValidationError, match="timezone-aware"):
        _make_payload(observed_at=datetime(2026, 8, 30, 10, 0, 0))  # naive


@pytest.mark.unit
def test_create_observation_rejects_invalid_vehicle_class() -> None:
    """Unknown vehicle classes are rejected."""
    with pytest.raises(ValidationError):
        _make_payload(vehicle_class="spaceship")


@pytest.mark.unit
def test_create_observation_rejects_confidence_out_of_range() -> None:
    """Confidence > 1.0 is rejected by schema."""
    with pytest.raises(ValidationError):
        _make_payload(detection_confidence=1.5)


@pytest.mark.unit
def test_create_observation_rejects_plate_confidence_without_text() -> None:
    """plate_confidence without plate_text is rejected."""
    with pytest.raises(ValidationError, match="plate_confidence provided without plate_text"):
        _make_payload(plate_text=None, plate_confidence=0.9)


@pytest.mark.unit
def test_create_observation_valid_no_plate() -> None:
    """An observation with no plate data is valid (plates are optional)."""
    payload = _make_payload(plate_text=None, plate_confidence=None, vehicle_class="car")
    assert payload.plate_text is None
    assert payload.vehicle_class == "car"


@pytest.mark.unit
def test_status_update_requires_rejection_reason() -> None:
    """Setting status to rejected without reason raises ValidationError."""
    with pytest.raises(ValidationError, match="rejection_reason is required"):
        VehicleObservationStatusUpdate(status="rejected")


@pytest.mark.unit
def test_status_update_rejected_with_reason_is_valid() -> None:
    update = VehicleObservationStatusUpdate(
        status="rejected", rejection_reason="Low confidence plate"
    )
    assert update.status == "rejected"


@pytest.mark.unit
def test_status_update_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        VehicleObservationStatusUpdate(status="unknown_state")


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_create_observation_success(
    obs_service: VehicleObservationService,
    sample_obs: MagicMock,
    sample_camera: MagicMock,
) -> None:
    """create_observation returns a response on success."""
    with (
        patch.object(obs_service._camera_repo, "get_by_id", return_value=sample_camera),
        patch.object(obs_service._repo, "get_by_source", return_value=None),
        patch.object(obs_service._repo, "create", return_value=sample_obs),
    ):
        result = await obs_service.create_observation(_make_payload())
        assert result.source == "yolov8-test"
        assert result.status == "detected"


@pytest.mark.unit
async def test_create_observation_camera_not_found(
    obs_service: VehicleObservationService,
) -> None:
    """create_observation raises NotFoundError for unknown camera."""
    with patch.object(obs_service._camera_repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await obs_service.create_observation(_make_payload())


@pytest.mark.unit
async def test_create_observation_duplicate_raises_conflict(
    obs_service: VehicleObservationService,
    sample_obs: MagicMock,
    sample_camera: MagicMock,
) -> None:
    """create_observation raises ConflictError for duplicate source key."""
    with (
        patch.object(obs_service._camera_repo, "get_by_id", return_value=sample_camera),
        patch.object(obs_service._repo, "get_by_source", return_value=sample_obs),
    ):
        with pytest.raises(ConflictError):
            await obs_service.create_observation(_make_payload())


@pytest.mark.unit
async def test_get_observation_not_found(
    obs_service: VehicleObservationService,
) -> None:
    with patch.object(obs_service._repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await obs_service.get_observation(uuid.uuid4())


@pytest.mark.unit
async def test_get_observation_success(
    obs_service: VehicleObservationService,
    sample_obs: MagicMock,
) -> None:
    with patch.object(obs_service._repo, "get_by_id", return_value=sample_obs):
        result = await obs_service.get_observation(sample_obs.id)
        assert result.id == sample_obs.id


@pytest.mark.unit
async def test_list_observations_pagination(
    obs_service: VehicleObservationService,
    sample_obs: MagicMock,
) -> None:
    from app.schemas.vehicle_observation import ObservationFilters

    with patch.object(obs_service._repo, "list_observations", return_value=([sample_obs], 1)):
        result = await obs_service.list_observations(
            filters=ObservationFilters(), page=1, page_size=10
        )
        assert result.total == 1
        assert result.pages == 1
        assert len(result.items) == 1


@pytest.mark.unit
async def test_bulk_ingest_mixed_results(
    obs_service: VehicleObservationService,
    sample_camera: MagicMock,
) -> None:
    """bulk_ingest accepts valid records and rejects unknown camera / duplicate records."""
    valid_payload = _make_payload(source_observation_id="valid-1")
    dup_payload = _make_payload(source_observation_id="dup-1")
    batch_dup_payload = _make_payload(source_observation_id="valid-1")  # duplicate of first
    bad_cam_payload = _make_payload(camera_id=uuid.uuid4(), source_observation_id="bad-cam-1")

    request = BulkObservationRequest(
        observations=[valid_payload, dup_payload, batch_dup_payload, bad_cam_payload]
    )

    mock_cam_exec = MagicMock()
    mock_cam_exec.scalars.return_value.all.return_value = [sample_camera]

    obs_service._repo._session.execute = AsyncMock(return_value=mock_cam_exec)
    obs_service._repo.get_many_by_source = AsyncMock(
        return_value={("yolov8-test", "dup-1"): MagicMock()}
    )
    obs_service._repo._session.add = MagicMock()
    obs_service._repo._session.flush = AsyncMock()
    obs_service._repo._session.refresh = AsyncMock()

    response = await obs_service.bulk_ingest(request)

    assert response.accepted_count == 1
    assert response.rejected_count == 3
    assert len(response.accepted) == 1
    assert response.accepted[0].source_observation_id == "valid-1"

    rejected_reasons = {r.source_observation_id: r.reason for r in response.rejected}
    assert "dup-1" in rejected_reasons
    assert "Duplicate:" in rejected_reasons["dup-1"]
    assert "valid-1" in rejected_reasons
    assert "Duplicate within this batch" in rejected_reasons["valid-1"]
    assert "bad-cam-1" in rejected_reasons
    assert "not found" in rejected_reasons["bad-cam-1"]
