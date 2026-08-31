"""Alert and BlacklistEntry SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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
    from app.models.trajectory import Trajectory
    from app.models.vehicle_identity import VehicleIdentity
    from app.models.vehicle_observation import VehicleObservation


class BlacklistEntry(UUIDMixin, TimestampMixin, Base):
    """
    Target license plate entry for watchlist and law enforcement alerting.
    """

    __tablename__ = "blacklist_entries"

    plate_text: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="Normalized license plate text to watch"
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Reason for blacklisting, e.g. Stolen Vehicle, Tax Default, Amber Alert",
    )

    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="medium",
        index=True,
        comment="low | medium | high | critical",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this watchlist entry is actively monitored",
    )

    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    alerts: Mapped[list[Alert]] = relationship(
        "Alert", back_populates="blacklist_entry", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_blacklist_entries_priority",
        ),
        Index("ix_blacklist_active_plate", "plate_text", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<BlacklistEntry id={self.id} plate={self.plate_text!r} priority={self.priority!r}>"


class Alert(UUIDMixin, TimestampMixin, Base):
    """
    Confidence-aware, explainable intelligence alert.

    Guarantees:
    - Never uses subjective/criminal accusations; uses objective telemetry wording.
    - Preserves all underlying evidence (plate, confidences, speeds, camera IDs) in structured JSONB.
    """

    __tablename__ = "alerts"

    alert_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique human-readable alert code, e.g. ALT-20260830-0001",
    )

    alert_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="BLACKLIST_MATCH | ROUTE_ANOMALY | TRAVEL_TIME_ANOMALY | CAMERA_OFFLINE | UNUSUAL_VEHICLE_PATTERN",
    )

    severity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="medium",
        index=True,
        comment="low | medium | high | critical",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NEW",
        index=True,
        comment="NEW | ACKNOWLEDGED | RESOLVED | DISMISSED",
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.9,
        comment="Overall confidence score in the alert validity",
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Spatial-temporal context
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    vehicle_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_identities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    trajectory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trajectories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicle_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    blacklist_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blacklist_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Detailed structured evidence for courtroom/auditing explainability
    evidence: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Structured explainability evidence and raw signal values",
    )

    # Lifecycle audit trail
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    camera: Mapped[Camera | None] = relationship("Camera", lazy="selectin")
    vehicle_identity: Mapped[VehicleIdentity | None] = relationship(
        "VehicleIdentity", lazy="selectin"
    )
    trajectory: Mapped[Trajectory | None] = relationship("Trajectory", lazy="selectin")
    observation: Mapped[VehicleObservation | None] = relationship(
        "VehicleObservation", lazy="selectin"
    )
    blacklist_entry: Mapped[BlacklistEntry | None] = relationship(
        "BlacklistEntry", back_populates="alerts", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED')",
            name="ck_alerts_status",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_alerts_confidence",
        ),
        Index("ix_alerts_type_status", "alert_type", "status"),
        Index("ix_alerts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Alert id={self.id} code={self.alert_code!r} type={self.alert_type!r} status={self.status!r}>"
