"""Camera repository."""

from __future__ import annotations

import uuid
from typing import Optional

from geoalchemy2.functions import ST_DWithin
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.camera import Camera
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    model = Camera

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_camera_id(self, camera_id: str) -> Optional[Camera]:
        """Look up camera by its human-readable camera_id (e.g. 'CAM-001')."""
        result = await self._session.execute(
            select(Camera).where(Camera.camera_id == camera_id)
        )
        return result.scalar_one_or_none()

    async def list_cameras(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        road_id: Optional[uuid.UUID] = None,
        direction: Optional[str] = None,
    ) -> tuple[list[Camera], int]:
        """List cameras with optional filters."""
        query = select(Camera)
        count_query = select(func.count()).select_from(Camera)

        if status:
            query = query.where(Camera.status == status)
            count_query = count_query.where(Camera.status == status)
        if road_id:
            query = query.where(Camera.road_id == road_id)
            count_query = count_query.where(Camera.road_id == road_id)
        if direction:
            query = query.where(Camera.direction == direction)
            count_query = count_query.where(Camera.direction == direction)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (await self._session.execute(query.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def find_near_point(
        self,
        longitude: float,
        latitude: float,
        radius_m: float = 200.0,
        limit: int = 10,
    ) -> list[Camera]:
        """Find cameras within radius_m metres of a WGS-84 point."""
        point_wkt = f"SRID=4326;POINT({longitude} {latitude})"
        # Convert metres to degrees (approximate, valid for small distances)
        radius_deg = radius_m / 111320.0
        query = (
            select(Camera)
            .where(Camera.location.isnot(None))
            .where(ST_DWithin(Camera.location, point_wkt, radius_deg))
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
