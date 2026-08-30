"""Road repository."""

from __future__ import annotations

from geoalchemy2.functions import ST_DWithin
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.road import Road
from app.repositories.base import BaseRepository


class RoadRepository(BaseRepository[Road]):
    model = Road

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_roads(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        road_type: str | None = None,
        direction: str | None = None,
    ) -> tuple[list[Road], int]:
        """List roads with optional filters."""
        query = select(Road)
        count_query = select(func.count()).select_from(Road)

        if road_type:
            query = query.where(Road.road_type == road_type)
            count_query = count_query.where(Road.road_type == road_type)
        if direction:
            query = query.where(Road.direction == direction)
            count_query = count_query.where(Road.direction == direction)

        total = (await self._session.execute(count_query)).scalar_one()
        rows = (await self._session.execute(query.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get_by_external_id(self, external_id: str) -> Road | None:
        result = await self._session.execute(select(Road).where(Road.external_id == external_id))
        return result.scalar_one_or_none()

    async def find_near_point(
        self,
        longitude: float,
        latitude: float,
        radius_m: float = 500.0,
        limit: int = 10,
    ) -> list[Road]:
        """Find roads within radius_m metres of a given WGS-84 point."""
        point_wkt = f"SRID=4326;POINT({longitude} {latitude})"
        query = (
            select(Road)
            .where(Road.geometry.isnot(None))
            .where(ST_DWithin(Road.geometry, point_wkt, radius_m / 111320.0))
            .limit(limit)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())
