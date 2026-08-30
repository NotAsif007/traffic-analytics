"""Unit tests for VehicleIdentityService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.schemas.vehicle_identity import IdentityFilters, VehicleIdentityCreate
from app.services.vehicle_identity import VehicleIdentityService

VID_ID = uuid.uuid4()
T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def identity_service(mock_session: AsyncMock) -> VehicleIdentityService:
    return VehicleIdentityService(mock_session)


@pytest.fixture
def sample_identity() -> MagicMock:
    ident = MagicMock()
    ident.id = VID_ID
    ident.identity_code = "VID-20260830-0001"
    ident.primary_plate = "AS01AB1234"
    ident.plate_confidence = 0.95
    ident.vehicle_class = "car"
    ident.vehicle_color = "silver"
    ident.vehicle_make = None
    ident.vehicle_model = None
    ident.status = "accepted"
    ident.first_seen_at = T0
    ident.last_seen_at = T0
    ident.total_sightings = 1
    ident.confidence = 0.90
    ident.reid_embedding_id = None
    ident.notes = None
    ident.metadata_ = None
    ident.created_at = T0
    ident.updated_at = T0
    ident.matches = []
    return ident


@pytest.mark.unit
async def test_create_identity(
    identity_service: VehicleIdentityService, sample_identity: MagicMock
) -> None:
    payload = VehicleIdentityCreate(
        identity_code="VID-20260830-0001",
        primary_plate="AS01AB1234",
        first_seen_at=T0,
        last_seen_at=T0,
        status="candidate",
    )
    with patch.object(identity_service._identity_repo, "create", return_value=sample_identity):
        res = await identity_service.create_identity(payload)
        assert res.identity_code == "VID-20260830-0001"
        assert res.primary_plate == "AS01AB1234"


@pytest.mark.unit
async def test_get_identity_not_found(identity_service: VehicleIdentityService) -> None:
    with patch.object(identity_service._identity_repo, "get_by_id", return_value=None):
        with pytest.raises(NotFoundError):
            await identity_service.get_identity(uuid.uuid4())


@pytest.mark.unit
async def test_get_identity_detail(
    identity_service: VehicleIdentityService, sample_identity: MagicMock
) -> None:
    with patch.object(
        identity_service._identity_repo, "get_with_matches", return_value=sample_identity
    ):
        res = await identity_service.get_identity_detail(VID_ID)
        assert res.id == VID_ID
        assert res.identity_code == "VID-20260830-0001"
        assert res.matches == []


@pytest.mark.unit
async def test_list_identities_pagination(
    identity_service: VehicleIdentityService, sample_identity: MagicMock
) -> None:
    with patch.object(
        identity_service._identity_repo, "list_identities", return_value=([sample_identity], 1)
    ):
        res = await identity_service.list_identities(
            filters=IdentityFilters(), page=1, page_size=10
        )
        assert res.total == 1
        assert len(res.items) == 1
        assert res.items[0].identity_code == "VID-20260830-0001"
