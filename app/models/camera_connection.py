"""CameraConnection SQLAlchemy model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.road import Road


class CameraConnection(UUIDMixin, TimestampMixin, Base):
    """
    Represents a plausible vehicle movement from one camera to another.

    A directed edge in the camera-road graph. Used by the trajectory
    association engine to determine whether a vehicle sighting at camera B
    is plausible given a prior sighting at camera A.

    Constraints enforced at DB level:
    - source and destination must differ
    - travel times must be positive
    - distance must be positive if provided
    - min_travel_time_s <= max_travel_time_s
    """

    __tablename__ = "camera_connections"

    source_camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    destination_camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional: the road segment connecting the two cameras
    road_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Travel time bounds in seconds (for plausibility gating)
    min_travel_time_s: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Minimum plausible travel time in seconds"
    )
    max_travel_time_s: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Maximum plausible travel time in seconds"
    )
    avg_travel_time_s: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Expected average travel time in seconds"
    )

    # Road distance between cameras in metres
    distance_m: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True, comment="Route distance in metres"
    )

    # Connection type / relationship description
    connection_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="direct | via_junction | u_turn | merge"
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-form metadata (weights for matching, etc.)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    source_camera: Mapped[Camera] = relationship(
        "Camera",
        foreign_keys=[source_camera_id],
        back_populates="outgoing_connections",
    )
    destination_camera: Mapped[Camera] = relationship(
        "Camera",
        foreign_keys=[destination_camera_id],
        back_populates="incoming_connections",
    )
    road: Mapped[Road | None] = relationship("Road", lazy="select")

    __table_args__ = (
        # Source and destination must differ
        CheckConstraint(
            "source_camera_id <> destination_camera_id",
            name="ck_camera_connections_no_self_loop",
        ),
        # Travel times must be positive
        CheckConstraint(
            "min_travel_time_s > 0",
            name="ck_camera_connections_min_travel_positive",
        ),
        CheckConstraint(
            "max_travel_time_s > 0",
            name="ck_camera_connections_max_travel_positive",
        ),
        # Min must be <= max
        CheckConstraint(
            "min_travel_time_s <= max_travel_time_s",
            name="ck_camera_connections_travel_time_order",
        ),
        # Distance must be positive if provided
        CheckConstraint(
            "distance_m IS NULL OR distance_m > 0",
            name="ck_camera_connections_distance_positive",
        ),
        # Unique directed edge (no duplicate connections for same source-dest pair)
        Index(
            "uix_camera_connections_source_dest",
            "source_camera_id",
            "destination_camera_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CameraConnection {self.source_camera_id} → {self.destination_camera_id} "
            f"({self.min_travel_time_s}-{self.max_travel_time_s}s)>"
        )
