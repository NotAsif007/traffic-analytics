"""
Unit tests for CameraService.

Uses mock session — no real database required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.camera import CameraCreate
from app.services.camera import CameraService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def camera_service(mock_session: AsyncMock) -> CameraService:
    return CameraService(mock_session)


@pytest.fixture
def sample_camera() -> MagicMock:
    cam = MagicMock()
    cam.id = uuid.uuid4()
    cam.camera_id = "CAM-001"
    cam.name = "Junction Camera North"
    cam.road_id = None
    cam.direction = "N"
    cam.fov_degrees = 120
    cam.lane_count = 3
    cam.lane_coverage = "1,2,3"
    cam.status = "active"
    cam.timezone = "Asia/Kolkata"
    cam.height_m = 6
    cam.metadata_ = None
    cam.notes = None
    cam.location = None
    return cam


@pytest.mark.unit
async def test_create_camera_success(
    camera_service: CameraService, sample_camera: MagicMock
) -> None:
    """create_camera returns a CameraResponse on success."""
    with (
        patch.object(camera_service._repo, "get_by_camera_id", return_value=None),
        patch.object(camera_service._repo, "create", return_value=sample_camera),
    ):
        result = await camera_service.create_camera(
            CameraCreate(camera_id="CAM-001", name="Junction Camera North")
        )
        assert result.camera_id == "CAM-001"
        assert result.status == "active"


@pytest.mark.unit
async def test_create_camera_duplicate_id(
    camera_service: CameraService, sample_camera: MagicMock
) -> None:
    """create_camera raises ConflictError if camera_id already exists."""
    with patch.object(camera_service._repo, "get_by_camera_id", return_value=sample_camera):
        with pytest.raises(ConflictError):
            await camera_service.create_camera(CameraCreate(camera_id="CAM-001", name="Duplicate"))


@pytest.mark.unit
async def test_get_camera_not_found(camera_service: CameraService) -> None:
    """get_camera raises NotFoundError for an unknown UUID."""
    with patch.object(camera_service._repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await camera_service.get_camera(uuid.uuid4())


@pytest.mark.unit
async def test_get_camera_success(camera_service: CameraService, sample_camera: MagicMock) -> None:
    """get_camera returns CameraResponse for an existing camera."""
    with patch.object(camera_service._repo, "get_by_id", return_value=sample_camera):
        result = await camera_service.get_camera(sample_camera.id)
        assert result.id == sample_camera.id
        assert result.camera_id == "CAM-001"


@pytest.mark.unit
async def test_create_camera_invalid_status(camera_service: CameraService) -> None:
    """CameraCreate rejects invalid status values at schema validation time."""
    with pytest.raises(Exception):  # pydantic ValidationError
        CameraCreate(camera_id="CAM-X", name="Bad Status Cam", status="broken")


@pytest.mark.unit
async def test_list_cameras_pagination(
    camera_service: CameraService, sample_camera: MagicMock
) -> None:
    """list_cameras returns a correctly shaped PaginatedResponse."""
    with patch.object(camera_service._repo, "list_cameras", return_value=([sample_camera], 1)):
        result = await camera_service.list_cameras(page=1, page_size=10)
        assert result.total == 1
        assert result.pages == 1
        assert len(result.items) == 1
