"""Trajectory and TrajectoryPoint SQLAlchemy models for city-wide vehicle journeys."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
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
    from app.models.vehicle_identity import VehicleIdentity
    from app.models.vehicle_observation import VehicleObservation
    from app.models.vehicle_track import VehicleTrack


class Trajectory(UUIDMixin, TimestampMixin, Base):
    """
    A synthesized, continuous spatial-temporal journey of a VehicleIdentity
    through the city camera network.

    Properties:
    - Ordered progression of camera sightings over time.
    - Accumulated route distance, travel duration, and average speed.
    - Deterministically reproducible from input observation sequences.
    """

    __tablename__ = "trajectories"

    # Human/system reference, e.g. "TRJ-20260830-0001"
    trajectory_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable trajectory identifier",
    )

    vehicle_identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        index=True,
        comment="active | completed | terminated",
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.8,
        comment="Overall trajectory confidence based on sightings and route feasibility",
    )

    # Route metrics
    total_distance_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Total accumulated distance along the road network in meters",
    )

    total_travel_time_s: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total elapsed time in seconds from first to last sighting",
    )

    average_speed_kmh: Mapped[float | None] = mapped_column(
        Numeric(6, 2), nullable=True, comment="Average journey speed in km/h"
    )

    points_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of camera sightings along this trajectory",
    )

    # Ordered list of camera UUIDs (as strings) and names for fast queries
    ordered_camera_ids: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Ordered list of camera UUIDs visited along this trajectory",
    )

    ordered_camera_names: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Ordered list of camera identifiers/names (e.g. ['C01', 'C03', 'C06'])",
    )

    # PostGIS LineString geometry connecting camera GPS coordinates
    route_geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True),
        nullable=True,
        comment="Spatial PostGIS LineString geometry representing the route path",
    )

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    identity: Mapped[VehicleIdentity] = relationship("VehicleIdentity", lazy="selectin")
    points: Mapped[list[TrajectoryPoint]] = relationship(
        "TrajectoryPoint",
        back_populates="trajectory",
        cascade="all, delete-orphan",
        order_by="TrajectoryPoint.sequence_order.asc()",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "start_time <= end_time",
            name="ck_trajectories_time_order",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'terminated')",
            name="ck_trajectories_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_trajectories_confidence",
        ),
        CheckConstraint(
            "total_distance_m >= 0",
            name="ck_trajectories_distance_positive",
        ),
        CheckConstraint(
            "total_travel_time_s >= 0",
            name="ck_trajectories_time_positive",
        ),
        Index("ix_trajectories_identity_time", "vehicle_identity_id", "start_time", "end_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<Trajectory id={self.id} code={self.trajectory_id!r} "
            f"identity={self.vehicle_identity_id} status={self.status!r} points={self.points_count}>"
        )


class TrajectoryPoint(UUIDMixin, TimestampMixin, Base):
    """
    A single node / waypoint along a vehicle trajectory.
    """

    __tablename__ = "trajectory_points"

    trajectory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trajectories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sequence_order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="1-based chronological sequence order (1, 2, 3...)"
    )

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    plate_text: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plate_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Segment transition from previous waypoint
    segment_distance_m: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Distance in meters from the previous waypoint"
    )

    segment_duration_s: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Duration in seconds from the previous waypoint"
    )

    is_interpolated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if this point is an inferred intermediate hop along the road graph",
    )

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    trajectory: Mapped[Trajectory] = relationship("Trajectory", back_populates="points", lazy="selectin")
    camera: Mapped[Camera] = relationship("Camera", lazy="selectin")
    observation: Mapped[VehicleObservation | None] = relationship(
        "VehicleObservation", lazy="selectin"
    )
    track: Mapped[VehicleTrack | None] = relationship("VehicleTrack", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "sequence_order >= 1",
            name="ck_trajectory_points_sequence_order",
        ),
        Index("ix_trajectory_points_traj_seq", "trajectory_id", "sequence_order"),
    )

    def __repr__(self) -> str:
        return (
            f"<TrajectoryPoint id={self.id} traj={self.trajectory_id} "
            f"seq={self.sequence_order} cam={self.camera_id} time={self.timestamp.isoformat()}>"
        )
