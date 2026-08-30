"""VehicleObservation SQLAlchemy model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.camera import Camera


class VehicleObservation(UUIDMixin, TimestampMixin, Base):
    """
    A single normalized vehicle observation produced by an AI/ANPR pipeline.

    Design principles:
    - AI outputs are UNCERTAIN. Every value that comes from inference
      (plate, vehicle class, color, speed) is stored alongside its
      confidence score. Nothing is treated as ground truth.
    - Source independence: the model does not care which AI system
      generated the observation. The `source` + `source_observation_id`
      fields provide idempotency and traceability back to any pipeline.
    - No binary blobs: images are stored in object storage (S3/GCS/MinIO).
      This model holds only path references.
    - Observation lifecycle: an observation progresses from `detected`
      through optional states to `associated` or `rejected`.
    """

    __tablename__ = "vehicle_observations"

    # -----------------------------------------------------------------------
    # Source / idempotency
    # -----------------------------------------------------------------------

    # The pipeline or system that produced this observation
    # e.g. "yolov8-lpr-v1", "mock-ingestor", "edge-node-3"
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Pipeline/system identifier that produced this observation"
    )

    # External ID assigned by the source pipeline (e.g. inference job ID + frame idx)
    # Combined with source, this forms the unique idempotency key.
    source_observation_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        comment="ID assigned by the source pipeline — unique per source"
    )

    # -----------------------------------------------------------------------
    # Camera / spatial context
    # -----------------------------------------------------------------------

    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------------------------
    # Temporal context
    # -----------------------------------------------------------------------

    # When the vehicle was physically observed (not when this record was created)
    observed_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp of the observation event (camera clock, UTC)",
    )

    # Optional frame metadata for tracing back to raw video
    frame_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # -----------------------------------------------------------------------
    # Vehicle detection
    # -----------------------------------------------------------------------

    vehicle_class: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Detected vehicle class: car | truck | motorcycle | bus | van | bicycle"
    )

    vehicle_color: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Detected dominant vehicle color"
    )

    # {x1: float, y1: float, x2: float, y2: float} — normalised 0..1
    bounding_box: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Vehicle bounding box in normalised coordinates {x1,y1,x2,y2}"
    )

    detection_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True,
        comment="Vehicle detector confidence (0.0–1.0)"
    )

    # -----------------------------------------------------------------------
    # Plate reading (OCR output — uncertain by design)
    # -----------------------------------------------------------------------

    plate_text: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True,
        comment="Raw OCR plate output — not ground truth"
    )

    plate_confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4), nullable=True,
        comment="OCR confidence for the plate reading (0.0–1.0)"
    )

    plate_bbox: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Plate bounding box {x1,y1,x2,y2} within the vehicle crop"
    )

    plate_region: Mapped[str | None] = mapped_column(
        String(16), nullable=True,
        comment="Detected plate region/country code (e.g. IN, MH, KA)"
    )

    # -----------------------------------------------------------------------
    # Media references — object-storage paths, never binary blobs
    # -----------------------------------------------------------------------

    # e.g. s3://traffic-frames/2026/08/30/cam-001/frame_000123.jpg
    frame_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Cropped vehicle image path
    crop_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Cropped plate image path
    plate_crop_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # -----------------------------------------------------------------------
    # Embedding reference (for cross-camera re-identification — Phase 4)
    # -----------------------------------------------------------------------

    # ID in the vector store (e.g. Pinecone/PGVector namespace)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Which model produced the embedding
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # -----------------------------------------------------------------------
    # Kinematics
    # -----------------------------------------------------------------------

    estimated_speed_kmh: Mapped[float | None] = mapped_column(
        Numeric(6, 2), nullable=True,
        comment="Estimated speed in km/h from the AI pipeline"
    )

    direction: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Movement direction: N/S/E/W or angle in degrees"
    )

    lane: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Lane number the vehicle was detected in (1-based)"
    )

    # -----------------------------------------------------------------------
    # Lifecycle status
    # -----------------------------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="detected", index=True,
        comment="detected | processed | validated | associated | rejected"
    )

    # Reason for rejection if status == rejected
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -----------------------------------------------------------------------
    # Free-form metadata
    # -----------------------------------------------------------------------

    # Arbitrary key-value pairs from the source pipeline
    # (model version, GPU node, inference time, etc.)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    camera: Mapped[Camera] = relationship("Camera", lazy="select")

    # -----------------------------------------------------------------------
    # Constraints and indexes
    # -----------------------------------------------------------------------

    __table_args__ = (
        # Idempotency: one (source, source_observation_id) pair only
        Index(
            "uix_vehicle_obs_source_obs_id",
            "source",
            "source_observation_id",
            unique=True,
        ),
        # Fast time-range queries per camera
        Index(
            "ix_vehicle_obs_camera_time",
            "camera_id",
            "observed_at",
        ),
        # Confidence check constraints
        CheckConstraint(
            "detection_confidence IS NULL OR (detection_confidence >= 0 AND detection_confidence <= 1)",
            name="ck_vehicle_obs_detection_confidence",
        ),
        CheckConstraint(
            "plate_confidence IS NULL OR (plate_confidence >= 0 AND plate_confidence <= 1)",
            name="ck_vehicle_obs_plate_confidence",
        ),
        # Status must be one of the valid lifecycle states
        CheckConstraint(
            "status IN ('detected', 'processed', 'validated', 'associated', 'rejected')",
            name="ck_vehicle_obs_status",
        ),
        # Speed must be positive if provided
        CheckConstraint(
            "estimated_speed_kmh IS NULL OR estimated_speed_kmh >= 0",
            name="ck_vehicle_obs_speed_positive",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<VehicleObservation id={self.id} "
            f"camera={self.camera_id} "
            f"plate={self.plate_text!r} "
            f"status={self.status!r}>"
        )
