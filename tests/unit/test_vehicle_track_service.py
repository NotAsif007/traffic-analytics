"""Unit tests for VehicleTrackService business logic with mocked database session."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.vehicle_track import TrackFilters, VehicleTrackCreate
from app.services.vehicle_track import VehicleTrackService

CAMERA_ID = uuid.uuid4()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def track_service(mock_session: AsyncMock) -> VehicleTrackService:
    return VehicleTrackService(mock_session)


@pytest.fixture
def sample_camera() -> MagicMock:
    cam = MagicMock()
    cam.id = CAMERA_ID
    return cam


@pytest.fixture
def sample_track() -> MagicMock:
    track = MagicMock()
    track.id = uuid.uuid4()
    track.track_id = "TRK-0001"
    track.camera_id = CAMERA_ID
    track.start_time = _utcnow()
    track.end_time = _utcnow()
    track.status = "active"
    track.confidence = 0.95
    track.vehicle_class = "car"
    track.vehicle_color = "black"
    track.best_plate_text = "KA01AB1234"
    track.best_plate_confidence = 0.92
    track.points_count = 5
    track.notes = None
    track.metadata_ = None
    track.created_at = _utcnow()
    track.updated_at = _utcnow()
    track.track_points = []
    return track


@pytest.mark.unit
async def test_create_track_success(
    track_service: VehicleTrackService, sample_camera: MagicMock, sample_track: MagicMock
) -> None:
    payload = VehicleTrackCreate(
        track_id="TRK-0001",
        camera_id=CAMERA_ID,
        start_time=_utcnow(),
        end_time=_utcnow(),
        confidence=0.95,
        vehicle_class="car",
    )
    with (
        patch.object(track_service._camera_repo, "get_by_id", return_value=sample_camera),
        patch.object(track_service._repo, "create", return_value=sample_track),
    ):
        result = await track_service.create_track(payload)
        assert result.track_id == "TRK-0001"
        assert result.camera_id == CAMERA_ID


@pytest.mark.unit
async def test_create_track_unknown_camera(track_service: VehicleTrackService) -> None:
    payload = VehicleTrackCreate(
        track_id="TRK-0001",
        camera_id=uuid.uuid4(),
        start_time=_utcnow(),
        end_time=_utcnow(),
    )
    with patch.object(track_service._camera_repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await track_service.create_track(payload)


@pytest.mark.unit
async def test_get_track_not_found(track_service: VehicleTrackService) -> None:
    with patch.object(track_service._repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await track_service.get_track(uuid.uuid4())


@pytest.mark.unit
async def test_get_track_success(
    track_service: VehicleTrackService, sample_track: MagicMock
) -> None:
    with patch.object(track_service._repo, "get_by_id", return_value=sample_track):
        result = await track_service.get_track(sample_track.id)
        assert result.id == sample_track.id
        assert result.track_id == "TRK-0001"


@pytest.mark.unit
async def test_list_tracks_pagination(
    track_service: VehicleTrackService, sample_track: MagicMock
) -> None:
    with patch.object(track_service._repo, "list_tracks", return_value=([sample_track], 1)):
        result = await track_service.list_tracks(filters=TrackFilters(), page=1, page_size=10)
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].track_id == "TRK-0001"
