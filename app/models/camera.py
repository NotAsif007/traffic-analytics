"""Camera SQLAlchemy model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera_connection import CameraConnection
    from app.models.road import Road


class Camera(UUIDMixin, TimestampMixin, Base):
    """
    A physical traffic camera installed at a fixed location.

    Location is stored as a PostGIS POINT (WGS-84, SRID 4326).
    Each camera may be associated with a road segment.
    """

    __tablename__ = "cameras"

    # Human-readable identifier (e.g. "CAM-001", "Junction-MG-Road")
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # GPS location of the camera
    location: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    # FK to the road this camera monitors (optional)
    road_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Direction camera is pointing (heading in degrees 0-359, or cardinal label)
    direction: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Heading degrees or N/S/E/W/NE/etc."
    )

    # Field of view in degrees
    fov_degrees: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Number of lanes this camera covers
    lane_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Which lane numbers this camera covers (e.g. "1,2,3")
    lane_coverage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Operational status
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="active | inactive | maintenance | fault",
    )

    # IANA timezone string for the camera's local time (e.g. "Asia/Kolkata")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")

    # Mounting height in metres
    height_m: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free-form metadata (model, IP, stream URL template, etc.)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    road: Mapped[Road | None] = relationship("Road", back_populates="cameras")

    outgoing_connections: Mapped[list[CameraConnection]] = relationship(
        "CameraConnection",
        foreign_keys="CameraConnection.source_camera_id",
        back_populates="source_camera",
        lazy="select",
    )
    incoming_connections: Mapped[list[CameraConnection]] = relationship(
        "CameraConnection",
        foreign_keys="CameraConnection.destination_camera_id",
        back_populates="destination_camera",
        lazy="select",
    )

    __table_args__ = (Index("ix_cameras_location", "location", postgresql_using="gist"),)

    def __repr__(self) -> str:
        return f"<Camera id={self.id} camera_id={self.camera_id!r} status={self.status!r}>"
