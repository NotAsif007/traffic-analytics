"""Alert and BlacklistEntry repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, BlacklistEntry
from app.repositories.base import BaseRepository
from app.schemas.alert import AlertFilters, BlacklistFilters


class BlacklistRepository(BaseRepository[BlacklistEntry]):
    model = BlacklistEntry

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_active_entries(self, plate_text: str | None = None) -> list[BlacklistEntry]:
        query = select(BlacklistEntry).where(BlacklistEntry.is_active.is_(True))
        if plate_text:
            query = query.where(BlacklistEntry.plate_text == plate_text)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_entries(
        self,
        *,
        filters: BlacklistFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[BlacklistEntry], int]:
        query = select(BlacklistEntry)
        count_query = select(func.count()).select_from(BlacklistEntry)

        conditions = []
        if filters.plate_text:
            conditions.append(BlacklistEntry.plate_text.ilike(f"%{filters.plate_text}%"))
        if filters.priority:
            conditions.append(BlacklistEntry.priority == filters.priority)
        if filters.is_active is not None:
            conditions.append(BlacklistEntry.is_active == filters.is_active)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            (
                await self._session.execute(
                    query.order_by(BlacklistEntry.created_at.desc()).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total


class AlertRepository(BaseRepository[Alert]):
    model = Alert

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_with_relations(self, alert_id: uuid.UUID) -> Alert | None:
        result = await self._session.execute(
            select(Alert)
            .where(Alert.id == alert_id)
            .options(
                selectinload(Alert.camera),
                selectinload(Alert.vehicle_identity),
                selectinload(Alert.blacklist_entry),
            )
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        *,
        filters: AlertFilters,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Alert], int]:
        query = select(Alert).options(selectinload(Alert.camera))
        count_query = select(func.count()).select_from(Alert)

        conditions = []
        if filters.alert_type:
            conditions.append(Alert.alert_type == filters.alert_type)
        if filters.severity:
            conditions.append(Alert.severity == filters.severity)
        if filters.status:
            conditions.append(Alert.status == filters.status)
        if filters.camera_id:
            conditions.append(Alert.camera_id == filters.camera_id)
        if filters.vehicle_identity_id:
            conditions.append(Alert.vehicle_identity_id == filters.vehicle_identity_id)
        if filters.min_confidence is not None:
            conditions.append(Alert.confidence >= filters.min_confidence)
        if filters.created_after:
            conditions.append(Alert.created_at >= filters.created_after)
        if filters.created_before:
            conditions.append(Alert.created_at <= filters.created_before)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (
            (
                await self._session.execute(
                    query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
