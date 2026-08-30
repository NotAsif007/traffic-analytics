"""VehicleObservation repository."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle_observation import VehicleObservation
from app.repositories.base import BaseRepository
from app.schemas.vehicle_observation import ObservationFilters


class VehicleObservationRepository(BaseRepository[VehicleObservation]):
    model = VehicleObservation

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_source(
        self,
        source: str,
        source_observation_id: str,
    ) -> Optional[VehicleObservation]:
        """Look up by idempotency key (source, source_observation_id)."""
        result = await self._session.execute(
            select(VehicleObservation).where(
                VehicleObservation.source == source,
                VehicleObservation.source_observation_id == source_observation_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_observations(
        self,
        *,
        filters: ObservationFilters,
        offset: int = 0,
        limit: int = 20,
        order_by_desc: bool = True,
    ) -> tuple[list[VehicleObservation], int]:
        """
        List observations matching the given filters.

        Returns (records, total_count).
        Ordered by observed_at DESC by default (most recent first).
        """
        query = select(VehicleObservation)
        count_query = select(func.count()).select_from(VehicleObservation)

        # Apply filters
        conditions = _build_filter_conditions(filters)
        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        # Count total before pagination
        total = (await self._session.execute(count_query)).scalar_one()

        # Order and paginate
        order_col = (
            VehicleObservation.observed_at.desc()
            if order_by_desc
            else VehicleObservation.observed_at.asc()
        )
        result = await self._session.execute(
            query.order_by(order_col).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_many_by_source(
        self,
        pairs: list[tuple[str, str]],
    ) -> dict[tuple[str, str], VehicleObservation]:
        """
        Fetch existing records for a batch of (source, source_observation_id) pairs.

        Used by bulk ingestion to detect duplicates efficiently in one query.
        """
        if not pairs:
            return {}

        # Build OR conditions for all pairs
        conditions = [
            (VehicleObservation.source == src)
            & (VehicleObservation.source_observation_id == obs_id)
            for src, obs_id in pairs
        ]
        result = await self._session.execute(
            select(VehicleObservation).where(or_(*conditions))
        )
        existing = result.scalars().all()
        return {(obs.source, obs.source_observation_id): obs for obs in existing}


def _build_filter_conditions(f: ObservationFilters) -> list:
    """Build SQLAlchemy filter conditions from ObservationFilters."""
    conditions = []

    if f.camera_id:
        conditions.append(VehicleObservation.camera_id == f.camera_id)

    if f.observed_after:
        conditions.append(VehicleObservation.observed_at >= f.observed_after)

    if f.observed_before:
        conditions.append(VehicleObservation.observed_at <= f.observed_before)

    if f.plate_text:
        # Case-insensitive partial match (uses pg_trgm GIN index)
        conditions.append(
            VehicleObservation.plate_text.ilike(f"%{f.plate_text}%")
        )

    if f.vehicle_class:
        conditions.append(VehicleObservation.vehicle_class == f.vehicle_class)

    if f.min_detection_confidence is not None:
        conditions.append(
            VehicleObservation.detection_confidence >= f.min_detection_confidence
        )

    if f.min_plate_confidence is not None:
        conditions.append(
            VehicleObservation.plate_confidence >= f.min_plate_confidence
        )

    if f.status:
        conditions.append(VehicleObservation.status == f.status)

    if f.source:
        conditions.append(VehicleObservation.source == f.source)

    return conditions
