"""VehicleTrack and TrackPoint SQLAlchemy models for single-camera tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.vehicle_observation import VehicleObservation


class VehicleTrack(UUIDMixin, TimestampMixin, Base):
    """
    A continuous sequence of observations of a vehicle within a SINGLE camera field of view.

    Architectural Distinction:
    - `track_id`: Local to a single camera. Represents continuous spatio-temporal
      motion across consecutive video frames (e.g. tracking via ByteTrack / BoT-SORT).
    - `vehicle_identity`: Global entity spanning multiple cameras across the city (future phase).
    """

    __tablename__ = "vehicle_tracks"

    # Human or tracker-assigned local identifier within this camera (e.g. "TRK-001", "102")
    track_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Local tracker identifier assigned by the single-camera tracking algorithm"
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp of the first observation in this track",
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp of the most recent observation in this track",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="active | completed | lost | terminated",
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.0,
        comment="Overall average detection confidence across track points",
    )

    vehicle_class: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Consolidated vehicle classification (e.g. car, truck, motorcycle)"
    )

    vehicle_color: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Consolidated dominant color"
    )

    best_plate_text: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True,
        comment="Highest confidence OCR plate text reading observed along the track"
    )

    best_plate_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True,
        comment="OCR confidence associated with best_plate_text"
    )

    points_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Total number of track points in this track"
    )

    # Free-form tracker metadata (e.g. velocity vector, Kalman filter state, tracker name)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    camera: Mapped[Camera] = relationship("Camera", lazy="select")

    track_points: Mapped[list[TrackPoint]] = relationship(
        "TrackPoint",
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="TrackPoint.timestamp.asc()",
        lazy="select",
    )

    __table_args__ = (
        CheckConstraint(
            "start_time <= end_time",
            name="ck_vehicle_tracks_time_order",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'lost', 'terminated')",
            name="ck_vehicle_tracks_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_vehicle_tracks_confidence",
        ),
        CheckConstraint(
            "best_plate_confidence IS NULL OR (best_plate_confidence >= 0 AND best_plate_confidence <= 1)",
            name="ck_vehicle_tracks_best_plate_confidence",
        ),
        Index("ix_vehicle_tracks_camera_time", "camera_id", "start_time", "end_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleTrack id={self.id} track_id={self.track_id!r} "
            f"camera={self.camera_id} status={self.status!r} points={self.points_count}>"
        )


class TrackPoint(UUIDMixin, TimestampMixin, Base):
    """
    A single point/state along a single-camera vehicle track.

    Connects a VehicleTrack to a physical timestamp, position (bounding box),
    and optionally the underlying VehicleObservation event.
    """

    __tablename__ = "track_points"

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Observation timestamp for this point along the track",
    )

    frame_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Bounding box in normalised coordinates {x1, y1, x2, y2}
    bounding_box: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Vehicle bounding box {x1,y1,x2,y2} in image coordinates"
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=1.0,
        comment="Detection confidence score for this point",
    )

    estimated_speed_kmh: Mapped[float | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )

    plate_text: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plate_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    track: Mapped[VehicleTrack] = relationship("VehicleTrack", back_populates="track_points")
    observation: Mapped[VehicleObservation | None] = relationship("VehicleObservation", lazy="select")

    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_track_points_confidence",
        ),
        CheckConstraint(
            "plate_confidence IS NULL OR (plate_confidence >= 0 AND plate_confidence <= 1)",
            name="ck_track_points_plate_confidence",
        ),
        Index("ix_track_points_track_time", "track_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackPoint id={self.id} track={self.track_id} "
            f"time={self.timestamp.isoformat()} conf={self.confidence}>"
        )
