"""Camera service — business logic for camera management."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.camera import Camera
from app.repositories.camera import CameraRepository
from app.repositories.road import RoadRepository
from app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from app.schemas.common import PaginatedResponse
from app.services.road import _geojson_to_wkt, _geometry_to_geojson

logger = get_logger(__name__)


def _camera_to_response(camera: Camera) -> CameraResponse:
    return CameraResponse(
        id=camera.id,
        camera_id=camera.camera_id,
        name=camera.name,
        road_id=camera.road_id,
        direction=camera.direction,
        fov_degrees=camera.fov_degrees,
        lane_count=camera.lane_count,
        lane_coverage=camera.lane_coverage,
        status=camera.status,
        timezone=camera.timezone,
        height_m=camera.height_m,
        metadata=camera.metadata_,
        notes=camera.notes,
        location=_geometry_to_geojson(camera.location),
    )


class CameraService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CameraRepository(session)
        self._road_repo = RoadRepository(session)

    async def create_camera(self, payload: CameraCreate) -> CameraResponse:
        # camera_id must be unique
        existing = await self._repo.get_by_camera_id(payload.camera_id)
        if existing:
            raise ConflictError("Camera", f"camera_id '{payload.camera_id}' already exists")

        # road_id must reference an existing road
        if payload.road_id:
            road = await self._road_repo.get_by_id(payload.road_id)
            if not road:
                raise NotFoundError("Road", payload.road_id)

        camera = Camera(
            camera_id=payload.camera_id,
            name=payload.name,
            road_id=payload.road_id,
            direction=payload.direction,
            fov_degrees=payload.fov_degrees,
            lane_count=payload.lane_count,
            lane_coverage=payload.lane_coverage,
            status=payload.status,
            timezone=payload.timezone,
            height_m=payload.height_m,
            metadata_=payload.metadata_,
            notes=payload.notes,
            location=_geojson_to_wkt(payload.location),
        )
        camera = await self._repo.create(camera)
        logger.info("camera.created", camera_id=camera.camera_id, id=str(camera.id))
        return _camera_to_response(camera)

    async def get_camera(self, camera_id: uuid.UUID) -> CameraResponse:
        camera = await self._repo.get_by_id(camera_id)
        if not camera:
            raise NotFoundError("Camera", camera_id)
        return _camera_to_response(camera)

    async def list_cameras(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        road_id: uuid.UUID | None = None,
        direction: str | None = None,
    ) -> PaginatedResponse[CameraResponse]:
        offset = (page - 1) * page_size
        cameras, total = await self._repo.list_cameras(
            offset=offset,
            limit=page_size,
            status=status,
            road_id=road_id,
            direction=direction,
        )
        items = [_camera_to_response(c) for c in cameras]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def update_camera(self, camera_id: uuid.UUID, payload: CameraUpdate) -> CameraResponse:
        camera = await self._repo.get_by_id(camera_id)
        if not camera:
            raise NotFoundError("Camera", camera_id)

        # Validate road_id if being updated
        if payload.road_id is not None:
            road = await self._road_repo.get_by_id(payload.road_id)
            if not road:
                raise NotFoundError("Road", payload.road_id)

        updates: dict[str, Any] = {}
        for field in (
            "name",
            "road_id",
            "direction",
            "fov_degrees",
            "lane_count",
            "lane_coverage",
            "status",
            "timezone",
            "height_m",
            "notes",
        ):
            val = getattr(payload, field, None)
            if val is not None:
                updates[field] = val
        if payload.metadata_ is not None:
            updates["metadata_"] = payload.metadata_
        if payload.location is not None:
            updates["location"] = _geojson_to_wkt(payload.location)

        camera = await self._repo.update(camera, updates)
        return _camera_to_response(camera)

    async def delete_camera(self, camera_id: uuid.UUID) -> None:
        camera = await self._repo.get_by_id(camera_id)
        if not camera:
            raise NotFoundError("Camera", camera_id)
        await self._repo.delete(camera)
        logger.info("camera.deleted", camera_id=str(camera_id))

    async def find_cameras_near(
        self,
        longitude: float,
        latitude: float,
        radius_m: float = 200.0,
    ) -> list[CameraResponse]:
        cameras = await self._repo.find_near_point(longitude, latitude, radius_m)
        return [_camera_to_response(c) for c in cameras]
