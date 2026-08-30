"""Road SQLAlchemy model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera


class Road(UUIDMixin, TimestampMixin, Base):
    """
    A road segment monitored by one or more cameras.

    Geometry is stored as a PostGIS LINESTRING (WGS-84, SRID 4326).
    Each road may be monitored by zero or more cameras.
    """

    __tablename__ = "roads"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Optional external reference (e.g. OpenStreetMap way ID, city GIS ID)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Road type: arterial, highway, collector, local, etc.
    road_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # PostGIS LINESTRING representing the road centreline in WGS-84
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=True,
    )

    # One-way / two-way / complex intersection metadata
    direction: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="one_way_forward | one_way_reverse | two_way"
    )

    speed_limit_kmh: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lane_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    cameras: Mapped[list[Camera]] = relationship("Camera", back_populates="road", lazy="select")

    __table_args__ = (Index("ix_roads_geometry", "geometry", postgresql_using="gist"),)

    def __repr__(self) -> str:
        return f"<Road id={self.id} name={self.name!r}>"
