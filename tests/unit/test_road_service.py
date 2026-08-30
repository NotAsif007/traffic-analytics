"""
Unit tests for RoadService.

Uses a mock session — no real database required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.road import RoadCreate, RoadUpdate
from app.services.road import RoadService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def road_service(mock_session: AsyncMock) -> RoadService:
    return RoadService(mock_session)


@pytest.fixture
def sample_road() -> MagicMock:
    road = MagicMock()
    road.id = uuid.uuid4()
    road.name = "MG Road"
    road.external_id = "way/123456"
    road.road_type = "arterial"
    road.direction = "two_way"
    road.speed_limit_kmh = 60
    road.lane_count = 4
    road.description = "Main arterial road"
    road.geometry = None
    road.cameras = []
    return road


@pytest.mark.unit
async def test_create_road_success(road_service: RoadService, sample_road: MagicMock) -> None:
    """RoadService.create_road returns a RoadResponse on success."""
    with (
        patch.object(road_service._repo, "get_by_external_id", return_value=None),
        patch.object(road_service._repo, "create", return_value=sample_road),
    ):
        payload = RoadCreate(
            name="MG Road",
            external_id="way/123456",
            road_type="arterial",
        )
        result = await road_service.create_road(payload)
        assert result.name == "MG Road"
        assert result.external_id == "way/123456"


@pytest.mark.unit
async def test_create_road_duplicate_external_id(
    road_service: RoadService, sample_road: MagicMock
) -> None:
    """create_road raises ConflictError if external_id is already taken."""
    with patch.object(road_service._repo, "get_by_external_id", return_value=sample_road):
        with pytest.raises(ConflictError):
            await road_service.create_road(
                RoadCreate(name="Duplicate Road", external_id="way/123456")
            )


@pytest.mark.unit
async def test_get_road_not_found(road_service: RoadService) -> None:
    """get_road raises NotFoundError for unknown IDs."""
    with patch.object(road_service._repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await road_service.get_road(uuid.uuid4())


@pytest.mark.unit
async def test_get_road_success(road_service: RoadService, sample_road: MagicMock) -> None:
    """get_road returns RoadResponse for an existing road."""
    with patch.object(road_service._repo, "get_by_id", return_value=sample_road):
        result = await road_service.get_road(sample_road.id)
        assert result.id == sample_road.id
        assert result.name == "MG Road"


@pytest.mark.unit
async def test_delete_road_not_found(road_service: RoadService) -> None:
    """delete_road raises NotFoundError if the road doesn't exist."""
    with patch.object(road_service._repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await road_service.delete_road(uuid.uuid4())


@pytest.mark.unit
async def test_list_roads_returns_paginated(
    road_service: RoadService, sample_road: MagicMock
) -> None:
    """list_roads returns a correctly shaped PaginatedResponse."""
    with patch.object(road_service._repo, "list_roads", return_value=([sample_road], 1)):
        result = await road_service.list_roads(page=1, page_size=20)
        assert result.total == 1
        assert result.page == 1
        assert len(result.items) == 1
