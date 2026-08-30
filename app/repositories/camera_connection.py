"""CameraConnection repository."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera_connection import CameraConnection
from app.repositories.base import BaseRepository


class CameraConnectionRepository(BaseRepository[CameraConnection]):
    model = CameraConnection

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_camera_pair(
        self,
        source_camera_id: uuid.UUID,
        destination_camera_id: uuid.UUID,
    ) -> Optional[CameraConnection]:
        """Return connection between a specific camera pair, if it exists."""
        result = await self._session.execute(
            select(CameraConnection).where(
                CameraConnection.source_camera_id == source_camera_id,
                CameraConnection.destination_camera_id == destination_camera_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_connections(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        source_camera_id: Optional[uuid.UUID] = None,
        destination_camera_id: Optional[uuid.UUID] = None,
        road_id: Optional[uuid.UUID] = None,
    ) -> tuple[list[CameraConnection], int]:
        """List connections with optional filters."""
        query = select(CameraConnection)
        count_query = select(func.count()).select_from(CameraConnection)

        if source_camera_id:
            query = query.where(CameraConnection.source_camera_id == source_camera_id)
            count_query = count_query.where(CameraConnection.source_camera_id == source_camera_id)
        if destination_camera_id:
            query = query.where(CameraConnection.destination_camera_id == destination_camera_id)
            count_query = count_query.where(
                CameraConnection.destination_camera_id == destination_camera_id
            )
        if road_id:
            query = query.where(CameraConnection.road_id == road_id)
            count_query = count_query.where(CameraConnection.road_id == road_id)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (await self._session.execute(query.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get_outgoing(self, camera_id: uuid.UUID) -> list[CameraConnection]:
        """All connections originating from a camera."""
        result = await self._session.execute(
            select(CameraConnection).where(CameraConnection.source_camera_id == camera_id)
        )
        return list(result.scalars().all())

    async def get_incoming(self, camera_id: uuid.UUID) -> list[CameraConnection]:
        """All connections arriving at a camera."""
        result = await self._session.execute(
            select(CameraConnection).where(
                CameraConnection.destination_camera_id == camera_id
            )
        )
        return list(result.scalars().all())
