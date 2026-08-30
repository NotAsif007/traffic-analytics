"""VehicleIdentity and VehicleMatch SQLAlchemy models for cross-camera association."""

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
    from app.models.vehicle_track import VehicleTrack


class VehicleIdentity(UUIDMixin, TimestampMixin, Base):
    """
    A city-wide vehicle identity hypothesis spanning observations across multiple cameras.

    Architectural Rule:
    - Represents a synthesized physical vehicle identity derived by the association engine.
    - Multiple observations and single-camera tracks link to this entity via VehicleMatch records.
    - Supports human operator review and manual merging.
    """

    __tablename__ = "vehicle_identities"

    # Human-readable reference code, e.g. "VID-20260830-0001"
    identity_code: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True,
        comment="Human-readable city-wide identity reference"
    )

    # Consensus or highest-confidence plate text
    primary_plate: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True,
        comment="Best consensus license plate reading"
    )

    plate_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True,
        comment="Confidence of primary plate reading"
    )

    # Consensus vehicle classification and appearance
    vehicle_class: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    vehicle_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vehicle_make: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Lifecycle / Association status
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="candidate", index=True,
        comment="candidate | accepted | rejected | needs_review",
    )

    # Spatio-temporal lifespan of this identity
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    total_sightings: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="Count of distinct camera sightings linked to this identity"
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False, default=0.5,
        comment="Aggregate confidence score of this identity hypothesis"
    )

    # Vector embedding reference for visual re-ID
    reid_embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Free-form metadata (e.g. operator review notes, merge history)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    matches: Mapped[list[VehicleMatch]] = relationship(
        "VehicleMatch",
        back_populates="identity",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        CheckConstraint(
            "first_seen_at <= last_seen_at",
            name="ck_vehicle_identities_time_order",
        ),
        CheckConstraint(
            "status IN ('candidate', 'accepted', 'rejected', 'needs_review')",
            name="ck_vehicle_identities_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_vehicle_identities_confidence",
        ),
        CheckConstraint(
            "plate_confidence IS NULL OR (plate_confidence >= 0 AND plate_confidence <= 1)",
            name="ck_vehicle_identities_plate_confidence",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleIdentity id={self.id} code={self.identity_code!r} "
            f"plate={self.primary_plate!r} status={self.status!r}>"
        )


class VehicleMatch(UUIDMixin, TimestampMixin, Base):
    """
    Detailed record of an association link between two sightings/tracks.

    Explainability Guarantee:
    - Stores the composite `match_score`.
    - Preserves individual signal contributions (`signals` JSONB).
    - Preserves human/machine readable `reasoning` explaining why the link was formed.
    """

    __tablename__ = "vehicle_matches"

    vehicle_identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The prior sighting / track
    source_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # The newly matched sighting / track
    target_observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_tracks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Overall match score in [0.0, 1.0]
    match_score: Mapped[float] = mapped_column(
        Numeric(5, 4), nullable=False,
        comment="Composite association score calculated across all signals"
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="accepted", index=True,
        comment="candidate | accepted | rejected | needs_review"
    )

    # Breakdown of individual signal scores for explainability
    # e.g. {"plate_similarity": 0.88, "appearance_similarity": 0.92, "temporal_feasibility": 0.97, ...}
    signals: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="Signal-by-signal score breakdown for explainability"
    )

    # Human-readable justification of the association decision
    reasoning: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Explainable rationale behind the association"
    )

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    identity: Mapped[VehicleIdentity] = relationship("VehicleIdentity", back_populates="matches")
    source_camera: Mapped[Camera] = relationship("Camera", foreign_keys=[source_camera_id], lazy="select")
    target_camera: Mapped[Camera] = relationship("Camera", foreign_keys=[target_camera_id], lazy="select")
    source_observation: Mapped[VehicleObservation | None] = relationship(
        "VehicleObservation", foreign_keys=[source_observation_id], lazy="select"
    )
    target_observation: Mapped[VehicleObservation | None] = relationship(
        "VehicleObservation", foreign_keys=[target_observation_id], lazy="select"
    )
    source_track: Mapped[VehicleTrack | None] = relationship(
        "VehicleTrack", foreign_keys=[source_track_id], lazy="select"
    )
    target_track: Mapped[VehicleTrack | None] = relationship(
        "VehicleTrack", foreign_keys=[target_track_id], lazy="select"
    )

    __table_args__ = (
        CheckConstraint(
            "match_score >= 0 AND match_score <= 1",
            name="ck_vehicle_matches_match_score",
        ),
        CheckConstraint(
            "status IN ('candidate', 'accepted', 'rejected', 'needs_review')",
            name="ck_vehicle_matches_status",
        ),
        Index("ix_vehicle_matches_cameras", "source_camera_id", "target_camera_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleMatch id={self.id} identity={self.vehicle_identity_id} "
            f"score={self.match_score} status={self.status!r}>"
        )
