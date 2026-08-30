"""
Reusable SQLAlchemy model mixins.

All domain models compose these to get consistent primary keys
and audit timestamps without duplication.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """
    Provides a UUID primary key generated server-side.

    Using PostgreSQL's native UUID type for storage efficiency.
    The default is generated in Python (not the DB) so the ID is
    available immediately after object creation without a DB round-trip.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """
    Provides created_at and updated_at audit timestamps.

    - created_at: set once at INSERT time (default + server_default)
    - updated_at: automatically updated on every UPDATE (default + onupdate)

    Both are timezone-aware UTC timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
