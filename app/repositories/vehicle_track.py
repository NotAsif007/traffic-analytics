"""VehicleTrack and TrackPoint repository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vehicle_track import TrackPoint, VehicleTrack
from app.repositories.base import BaseRepository
from app.schemas.vehicle_track import TrackFilters


class VehicleTrackRepository(BaseRepository[VehicleTrack]):
    model = VehicleTrack

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_with_points(self, track_id: uuid.UUID) -> VehicleTrack | None:
        """Fetch a vehicle track including all its track points ordered by timestamp."""
        result = await self._session.execute(
            select(VehicleTrack)
            .where(VehicleTrack.id == track_id)
            .options(selectinload(VehicleTrack.track_points))
        )
        return result.scalar_one_or_none()

    async def list_tracks(
        self,
        *,
        filters: TrackFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[VehicleTrack], int]:
        """List vehicle tracks with filtering and pagination."""
        query = select(VehicleTrack)
        count_query = select(func.count()).select_from(VehicleTrack)

        conditions = []
        if filters.camera_id:
            conditions.append(VehicleTrack.camera_id == filters.camera_id)
        if filters.status:
            conditions.append(VehicleTrack.status == filters.status)
        if filters.vehicle_class:
            conditions.append(VehicleTrack.vehicle_class == filters.vehicle_class)
        if filters.plate_text:
            conditions.append(VehicleTrack.best_plate_text.ilike(f"%{filters.plate_text}%"))
        if filters.min_confidence is not None:
            conditions.append(VehicleTrack.confidence >= filters.min_confidence)
        if filters.start_after:
            conditions.append(VehicleTrack.start_time >= filters.start_after)
        if filters.end_before:
            conditions.append(VehicleTrack.end_time <= filters.end_before)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            (
                await self._session.execute(
                    query.order_by(VehicleTrack.start_time.desc()).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_by_camera(
        self,
        camera_id: uuid.UUID,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[VehicleTrack], int]:
        filters = TrackFilters(camera_id=camera_id, status=status)
        return await self.list_tracks(filters=filters, offset=offset, limit=limit)

    async def get_track_observations(self, track_id: uuid.UUID) -> list[TrackPoint]:
        """Get all track points for a track in chronological order."""
        result = await self._session.execute(
            select(TrackPoint)
            .where(TrackPoint.track_id == track_id)
            .order_by(TrackPoint.timestamp.asc())
        )
        return list(result.scalars().all())
