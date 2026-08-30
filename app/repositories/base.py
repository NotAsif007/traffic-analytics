"""
Generic base repository.

Provides standard CRUD operations for any SQLAlchemy model.
Domain-specific repositories extend this class with specialised queries.

The repository layer is the only place that imports SQLAlchemy directly.
Services work with domain objects and schemas — never with ORM internals.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async CRUD repository.

    Subclasses declare their model type:
        class CameraRepository(BaseRepository[Camera]):
            model = Camera
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -----------------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------------

    async def get_by_id(self, record_id: uuid.UUID) -> ModelT | None:
        """Return a single record by primary key, or None if not found."""
        result = await self._session.get(self.model, record_id)
        return result

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        """
        Return a paginated list of records and the total count.

        Parameters
        ----------
        offset: int
            Number of records to skip.
        limit: int
            Maximum number of records to return.
        filters: dict[str, Any] | None
            Simple equality filters: {column_name: value}.
            For complex queries, override in the subclass.

        Returns
        -------
        tuple[list[ModelT], int]
            (records, total_count)
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if filters:
            for attr, value in filters.items():
                column = getattr(self.model, attr, None)
                if column is not None and value is not None:
                    query = query.where(column == value)
                    count_query = count_query.where(column == value)

        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        result = await self._session.execute(query.offset(offset).limit(limit))
        records = list(result.scalars().all())

        return records, total

    # -----------------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------------

    async def create(self, instance: ModelT) -> ModelT:
        """Persist a new model instance. The session commit is handled by get_db()."""
        self._session.add(instance)
        await self._session.flush()  # flush to DB, assigns DB-generated fields
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, data: dict[str, Any]) -> ModelT:
        """Apply a dict of updates to an existing instance."""
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete an instance from the database."""
        await self._session.delete(instance)
        await self._session.flush()
