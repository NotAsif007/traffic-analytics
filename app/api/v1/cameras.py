"""Camera CRUD endpoints — /api/v1/cameras."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.camera import CameraCreate, CameraResponse
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_track import VehicleTrackResponse
from app.services.camera import CameraService
from app.services.vehicle_track import VehicleTrackService

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _camera_service(db: DBSession) -> CameraService:
    return CameraService(db)


def _vehicle_track_service(db: DBSession) -> VehicleTrackService:
    return VehicleTrackService(db)


CameraServiceDep = Annotated[CameraService, Depends(_camera_service)]
VehicleTrackServiceDep = Annotated[VehicleTrackService, Depends(_vehicle_track_service)]


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(payload: CameraCreate, svc: CameraServiceDep) -> CameraResponse:
    """Register a new traffic camera."""
    return await svc.create_camera(payload)


@router.get("/", response_model=PaginatedResponse[CameraResponse])
async def list_cameras(
    svc: CameraServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None, description="Filter by status: active | inactive | maintenance | fault"
    ),
    road_id: uuid.UUID | None = Query(None, description="Filter by road UUID"),
    direction: str | None = Query(None, description="Filter by direction heading"),
) -> PaginatedResponse[CameraResponse]:
    """List cameras with optional filters."""
    return await svc.list_cameras(
        page=page,
        page_size=page_size,
        status=status,
        road_id=road_id,
        direction=direction,
    )


@router.get("/near", response_model=list[CameraResponse])
async def cameras_near_point(
    svc: CameraServiceDep,
    longitude: float = Query(..., ge=-180.0, le=180.0),
    latitude: float = Query(..., ge=-90.0, le=90.0),
    radius_m: float = Query(200.0, ge=1.0, le=5000.0, description="Search radius in metres"),
) -> list[CameraResponse]:
    """Find cameras within a radius of a GPS coordinate."""
    return await svc.find_cameras_near(longitude, latitude, radius_m)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: uuid.UUID, svc: CameraServiceDep) -> CameraResponse:
    """Retrieve a camera by its UUID."""
    return await svc.get_camera(camera_id)


@router.patch("/{camera_id}", response_model=CameraResponse)
@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_camera(camera_id: uuid.UUID, svc: CameraServiceDep) -> None:
    """Delete a camera (its connections will be cascade-deleted)."""
    await svc.delete_camera(camera_id)


@router.get("/{camera_id}/tracks", response_model=PaginatedResponse[VehicleTrackResponse])
async def list_camera_tracks(
    camera_id: uuid.UUID,
    track_svc: VehicleTrackServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by track status"),
) -> PaginatedResponse[VehicleTrackResponse]:
    """Retrieve all vehicle tracks captured by a specific camera."""
    return await track_svc.list_camera_tracks(
        camera_id=camera_id, status=status, page=page, page_size=page_size
    )
