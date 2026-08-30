"""Single-camera vehicle tracking endpoints — /api/v1/tracks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_track import (
    TrackFilters,
    TrackPointResponse,
    VehicleTrackCreate,
    VehicleTrackDetailResponse,
    VehicleTrackResponse,
)
from app.services.vehicle_track import VehicleTrackService

router = APIRouter(prefix="/tracks", tags=["tracks"])


def _track_service(db: DBSession) -> VehicleTrackService:
    return VehicleTrackService(db)


TrackServiceDep = Annotated[VehicleTrackService, Depends(_track_service)]


@router.post(
    "/",
    response_model=VehicleTrackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or register a single-camera vehicle track",
)
async def create_track(
    payload: VehicleTrackCreate,
    svc: TrackServiceDep,
) -> VehicleTrackResponse:
    return await svc.create_track(payload)


@router.get(
    "/",
    response_model=PaginatedResponse[VehicleTrackResponse],
    summary="List single-camera vehicle tracks",
)
async def list_tracks(
    svc: TrackServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    camera_id: Optional[uuid.UUID] = Query(None, description="Filter by camera UUID"),
    status: Optional[str] = Query(None, description="Filter by track status: active|completed|lost|terminated"),
    vehicle_class: Optional[str] = Query(None, description="Filter by vehicle class"),
    plate_text: Optional[str] = Query(None, description="Partial plate text match"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    start_after: Optional[datetime] = Query(None, description="Tracks starting after this timestamp"),
    end_before: Optional[datetime] = Query(None, description="Tracks ending before this timestamp"),
) -> PaginatedResponse[VehicleTrackResponse]:
    filters = TrackFilters(
        camera_id=camera_id,
        status=status,
        vehicle_class=vehicle_class,
        plate_text=plate_text,
        min_confidence=min_confidence,
        start_after=start_after,
        end_before=end_before,
    )
    return await svc.list_tracks(filters=filters, page=page, page_size=page_size)


@router.get(
    "/{track_id}",
    response_model=VehicleTrackDetailResponse,
    summary="Retrieve a single-camera track by UUID including its track points",
)
async def get_track(
    track_id: uuid.UUID,
    svc: TrackServiceDep,
) -> VehicleTrackDetailResponse:
    return await svc.get_track_detail(track_id)


@router.get(
    "/{track_id}/observations",
    response_model=list[TrackPointResponse],
    summary="Retrieve all chronological observations/points for a single-camera track",
)
async def get_track_observations(
    track_id: uuid.UUID,
    svc: TrackServiceDep,
) -> list[TrackPointResponse]:
    return await svc.get_track_observations(track_id)
