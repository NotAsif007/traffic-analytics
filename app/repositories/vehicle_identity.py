"""VehicleIdentity and VehicleMatch repositories."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vehicle_identity import VehicleIdentity, VehicleMatch
from app.repositories.base import BaseRepository
from app.schemas.vehicle_identity import IdentityFilters


class VehicleIdentityRepository(BaseRepository[VehicleIdentity]):
    model = VehicleIdentity

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_with_matches(self, identity_id: uuid.UUID) -> Optional[VehicleIdentity]:
        """Fetch a vehicle identity including all associated match events."""
        result = await self._session.execute(
            select(VehicleIdentity)
            .where(VehicleIdentity.id == identity_id)
            .options(selectinload(VehicleIdentity.matches))
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, identity_code: str) -> Optional[VehicleIdentity]:
        result = await self._session.execute(
            select(VehicleIdentity).where(VehicleIdentity.identity_code == identity_code)
        )
        return result.scalar_one_or_none()

    async def list_identities(
        self,
        *,
        filters: IdentityFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[VehicleIdentity], int]:
        query = select(VehicleIdentity)
        count_query = select(func.count()).select_from(VehicleIdentity)

        conditions = []
        if filters.status:
            conditions.append(VehicleIdentity.status == filters.status)
        if filters.primary_plate:
            conditions.append(VehicleIdentity.primary_plate.ilike(f"%{filters.primary_plate}%"))
        if filters.vehicle_class:
            conditions.append(VehicleIdentity.vehicle_class == filters.vehicle_class)
        if filters.min_confidence is not None:
            conditions.append(VehicleIdentity.confidence >= filters.min_confidence)
        if filters.seen_after:
            conditions.append(VehicleIdentity.last_seen_at >= filters.seen_after)
        if filters.seen_before:
            conditions.append(VehicleIdentity.first_seen_at <= filters.seen_before)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            await self._session.execute(
                query.order_by(VehicleIdentity.last_seen_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(rows), total

    async def find_recent_identities(
        self,
        seen_after: datetime,
        limit: int = 100,
    ) -> list[VehicleIdentity]:
        """Find active identities seen recently within the search window."""
        result = await self._session.execute(
            select(VehicleIdentity)
            .where(VehicleIdentity.last_seen_at >= seen_after)
            .where(VehicleIdentity.status != "rejected")
            .options(selectinload(VehicleIdentity.matches))
            .order_by(VehicleIdentity.last_seen_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class VehicleMatchRepository(BaseRepository[VehicleMatch]):
    model = VehicleMatch

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_matches(
        self,
        *,
        identity_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[VehicleMatch], int]:
        query = select(VehicleMatch)
        count_query = select(func.count()).select_from(VehicleMatch)

        conditions = []
        if identity_id:
            conditions.append(VehicleMatch.vehicle_identity_id == identity_id)
        if status:
            conditions.append(VehicleMatch.status == status)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            await self._session.execute(
                query.order_by(VehicleMatch.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(rows), total
