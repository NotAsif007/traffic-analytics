"""CameraConnection service — business logic for connection management."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.camera_connection import CameraConnection
from app.repositories.camera import CameraRepository
from app.repositories.camera_connection import CameraConnectionRepository
from app.repositories.road import RoadRepository
from app.schemas.camera_connection import (
    CameraConnectionCreate,
    CameraConnectionResponse,
    CameraConnectionUpdate,
)
from app.schemas.common import PaginatedResponse

logger = get_logger(__name__)


def _conn_to_response(conn: CameraConnection) -> CameraConnectionResponse:
    return CameraConnectionResponse(
        id=conn.id,
        source_camera_id=conn.source_camera_id,
        destination_camera_id=conn.destination_camera_id,
        road_id=conn.road_id,
        min_travel_time_s=conn.min_travel_time_s,
        max_travel_time_s=conn.max_travel_time_s,
        avg_travel_time_s=conn.avg_travel_time_s,
        distance_m=float(conn.distance_m) if conn.distance_m else None,
        connection_type=conn.connection_type,
        notes=conn.notes,
        metadata=conn.metadata_,
    )


class CameraConnectionService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CameraConnectionRepository(session)
        self._camera_repo = CameraRepository(session)
        self._road_repo = RoadRepository(session)

    async def _validate_cameras_exist(
        self,
        source_id: uuid.UUID,
        dest_id: uuid.UUID,
    ) -> None:
        """Raise NotFoundError if either camera doesn't exist."""
        src = await self._camera_repo.get_by_id(source_id)
        if not src:
            raise NotFoundError("Camera (source)", source_id)
        dst = await self._camera_repo.get_by_id(dest_id)
        if not dst:
            raise NotFoundError("Camera (destination)", dest_id)

    async def create_connection(
        self, payload: CameraConnectionCreate
    ) -> CameraConnectionResponse:
        # Validate cameras exist
        await self._validate_cameras_exist(
            payload.source_camera_id, payload.destination_camera_id
        )

        # Validate road_id if provided
        if payload.road_id:
            road = await self._road_repo.get_by_id(payload.road_id)
            if not road:
                raise NotFoundError("Road", payload.road_id)

        # Enforce uniqueness of directed edge
        existing = await self._repo.get_by_camera_pair(
            payload.source_camera_id, payload.destination_camera_id
        )
        if existing:
            raise ConflictError(
                "CameraConnection",
                f"Connection from {payload.source_camera_id} to "
                f"{payload.destination_camera_id} already exists",
            )

        conn = CameraConnection(
            source_camera_id=payload.source_camera_id,
            destination_camera_id=payload.destination_camera_id,
            road_id=payload.road_id,
            min_travel_time_s=payload.min_travel_time_s,
            max_travel_time_s=payload.max_travel_time_s,
            avg_travel_time_s=payload.avg_travel_time_s,
            distance_m=payload.distance_m,
            connection_type=payload.connection_type,
            notes=payload.notes,
            metadata_=payload.metadata_,
        )
        conn = await self._repo.create(conn)
        logger.info(
            "camera_connection.created",
            connection_id=str(conn.id),
            source=str(conn.source_camera_id),
            dest=str(conn.destination_camera_id),
        )
        return _conn_to_response(conn)

    async def get_connection(self, connection_id: uuid.UUID) -> CameraConnectionResponse:
        conn = await self._repo.get_by_id(connection_id)
        if not conn:
            raise NotFoundError("CameraConnection", connection_id)
        return _conn_to_response(conn)

    async def list_connections(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        source_camera_id: Optional[uuid.UUID] = None,
        destination_camera_id: Optional[uuid.UUID] = None,
        road_id: Optional[uuid.UUID] = None,
    ) -> PaginatedResponse[CameraConnectionResponse]:
        offset = (page - 1) * page_size
        conns, total = await self._repo.list_connections(
            offset=offset,
            limit=page_size,
            source_camera_id=source_camera_id,
            destination_camera_id=destination_camera_id,
            road_id=road_id,
        )
        items = [_conn_to_response(c) for c in conns]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def update_connection(
        self, connection_id: uuid.UUID, payload: CameraConnectionUpdate
    ) -> CameraConnectionResponse:
        conn = await self._repo.get_by_id(connection_id)
        if not conn:
            raise NotFoundError("CameraConnection", connection_id)

        if payload.road_id is not None:
            road = await self._road_repo.get_by_id(payload.road_id)
            if not road:
                raise NotFoundError("Road", payload.road_id)

        updates: dict[str, Any] = {}
        for field in ("road_id", "min_travel_time_s", "max_travel_time_s",
                      "avg_travel_time_s", "distance_m", "connection_type", "notes"):
            val = getattr(payload, field, None)
            if val is not None:
                updates[field] = val
        if payload.metadata_ is not None:
            updates["metadata_"] = payload.metadata_

        # Re-validate times after update
        new_min = updates.get("min_travel_time_s", conn.min_travel_time_s)
        new_max = updates.get("max_travel_time_s", conn.max_travel_time_s)
        if new_min > new_max:
            raise ValidationError("min_travel_time_s must be <= max_travel_time_s")

        conn = await self._repo.update(conn, updates)
        return _conn_to_response(conn)

    async def delete_connection(self, connection_id: uuid.UUID) -> None:
        conn = await self._repo.get_by_id(connection_id)
        if not conn:
            raise NotFoundError("CameraConnection", connection_id)
        await self._repo.delete(conn)
        logger.info("camera_connection.deleted", connection_id=str(connection_id))
