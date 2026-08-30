"""Trajectory and TrajectoryPoint repository."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trajectory import Trajectory, TrajectoryPoint
from app.repositories.base import BaseRepository
from app.schemas.trajectory import TrajectoryFilters


class TrajectoryRepository(BaseRepository[Trajectory]):
    model = Trajectory

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_with_points(self, trajectory_id: uuid.UUID) -> Optional[Trajectory]:
        """Fetch trajectory with all points ordered by sequence order."""
        result = await self._session.execute(
            select(Trajectory)
            .where(Trajectory.id == trajectory_id)
            .options(selectinload(Trajectory.points).selectinload(TrajectoryPoint.camera))
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, trajectory_id_str: str) -> Optional[Trajectory]:
        result = await self._session.execute(
            select(Trajectory)
            .where(Trajectory.trajectory_id == trajectory_id_str)
            .options(selectinload(Trajectory.points).selectinload(TrajectoryPoint.camera))
        )
        return result.scalar_one_or_none()

    async def get_active_by_identity(
        self, identity_id: uuid.UUID
    ) -> Optional[Trajectory]:
        """Find the currently active trajectory for a vehicle identity."""
        result = await self._session.execute(
            select(Trajectory)
            .where(Trajectory.vehicle_identity_id == identity_id)
            .where(Trajectory.status == "active")
            .options(selectinload(Trajectory.points).selectinload(TrajectoryPoint.camera))
            .order_by(Trajectory.end_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_trajectories(
        self,
        *,
        filters: TrajectoryFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Trajectory], int]:
        query = select(Trajectory)
        count_query = select(func.count()).select_from(Trajectory)

        conditions = []
        if filters.vehicle_identity_id:
            conditions.append(Trajectory.vehicle_identity_id == filters.vehicle_identity_id)
        if filters.status:
            conditions.append(Trajectory.status == filters.status)
        if filters.min_confidence is not None:
            conditions.append(Trajectory.confidence >= filters.min_confidence)
        if filters.start_after:
            conditions.append(Trajectory.start_time >= filters.start_after)
        if filters.end_before:
            conditions.append(Trajectory.end_time <= filters.end_before)
        if filters.camera_id:
            # Check JSONB array ordered_camera_ids contains camera_id string
            conditions.append(
                Trajectory.ordered_camera_ids.contains([str(filters.camera_id)])
            )

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            await self._session.execute(
                query.order_by(Trajectory.end_time.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(rows), total

    async def get_by_vehicle_identity(
        self,
        identity_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Trajectory], int]:
        filters = TrajectoryFilters(vehicle_identity_id=identity_id)
        return await self.list_trajectories(filters=filters, offset=offset, limit=limit)
