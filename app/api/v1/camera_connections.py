"""CameraConnection CRUD endpoints — /api/v1/camera-connections."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.camera_connection import (
    CameraConnectionCreate,
    CameraConnectionResponse,
    CameraConnectionUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services.camera_connection import CameraConnectionService

router = APIRouter(prefix="/camera-connections", tags=["camera-connections"])


def _conn_service(db: DBSession) -> CameraConnectionService:
    return CameraConnectionService(db)


ConnectionServiceDep = Annotated[CameraConnectionService, Depends(_conn_service)]


@router.post("/", response_model=CameraConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    payload: CameraConnectionCreate, svc: ConnectionServiceDep
) -> CameraConnectionResponse:
    """
    Create a directed camera-to-camera connection.

    Represents a plausible vehicle movement from source to destination.
    Source and destination cameras must exist, and the directed pair must
    be unique.
    """
    return await svc.create_connection(payload)


@router.get("/", response_model=PaginatedResponse[CameraConnectionResponse])
async def list_connections(
    svc: ConnectionServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_camera_id: uuid.UUID | None = Query(None),
    destination_camera_id: uuid.UUID | None = Query(None),
    road_id: uuid.UUID | None = Query(None),
) -> PaginatedResponse[CameraConnectionResponse]:
    """List camera connections with optional filters."""
    return await svc.list_connections(
        page=page,
        page_size=page_size,
        source_camera_id=source_camera_id,
        destination_camera_id=destination_camera_id,
        road_id=road_id,
    )


@router.get("/{connection_id}", response_model=CameraConnectionResponse)
async def get_connection(
    connection_id: uuid.UUID, svc: ConnectionServiceDep
) -> CameraConnectionResponse:
    """Retrieve a connection by UUID."""
    return await svc.get_connection(connection_id)


@router.patch("/{connection_id}", response_model=CameraConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    payload: CameraConnectionUpdate,
    svc: ConnectionServiceDep,
) -> CameraConnectionResponse:
    """Partially update a connection (travel times, distance, metadata)."""
    return await svc.update_connection(connection_id, payload)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_connection(connection_id: uuid.UUID, svc: ConnectionServiceDep) -> None:
    """Delete a camera connection."""
    await svc.delete_connection(connection_id)
