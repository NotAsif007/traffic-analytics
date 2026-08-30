"""VehicleObservation Pydantic schemas.

Design note: AI outputs are uncertain.
Every detected value (plate, class, color, speed) is stored alongside
its confidence score. The API enforces this by accepting and returning
both the value AND its confidence wherever inference is involved.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import AppBaseModel

# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------

VALID_STATUSES = {"detected", "processed", "validated", "associated", "rejected"}

VALID_VEHICLE_CLASSES = {
    "car", "truck", "motorcycle", "bus", "van", "bicycle",
    "auto_rickshaw", "heavy_vehicle", "unknown",
}


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class BoundingBox(AppBaseModel):
    """
    Bounding box in normalised image coordinates.

    All values in range [0.0, 1.0] relative to image dimensions.
    x1,y1 = top-left corner; x2,y2 = bottom-right corner.
    """
    x1: float = Field(..., ge=0.0, le=1.0)
    y1: float = Field(..., ge=0.0, le=1.0)
    x2: float = Field(..., ge=0.0, le=1.0)
    y2: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_box(self) -> BoundingBox:
        if self.x2 <= self.x1:
            raise ValueError("x2 must be greater than x1")
        if self.y2 <= self.y1:
            raise ValueError("y2 must be greater than y1")
        return self


class ConfidenceValue(AppBaseModel):
    """A measured value paired with its confidence score."""
    value: str
    confidence: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Observation create schema
# ---------------------------------------------------------------------------

class VehicleObservationCreate(AppBaseModel):
    """
    Request body for ingesting a single vehicle observation.

    Mirrors exactly what an AI/ANPR pipeline would produce.
    All inference outputs carry a confidence score.
    """

    # Idempotency / provenance
    source: str = Field(
        ..., min_length=1, max_length=64,
        examples=["yolov8-lpr-v1"],
        description="Identifier of the AI pipeline/system that produced this observation"
    )
    source_observation_id: str = Field(
        ..., min_length=1, max_length=128,
        examples=["job-20260830-cam001-frame-000123"],
        description="Unique ID within the source pipeline — used for idempotency"
    )

    # Camera context
    camera_id: uuid.UUID = Field(..., description="UUID of the camera that made the observation")

    # When the vehicle was physically observed (must be timezone-aware)
    observed_at: datetime = Field(
        ...,
        description="Observation timestamp (UTC recommended). Must include timezone info."
    )
    frame_number: Optional[int] = Field(None, ge=0, description="Frame number within video stream")

    # ---- Vehicle detection ----
    vehicle_class: Optional[str] = Field(
        None, max_length=64, examples=["car", "truck", "motorcycle"]
    )
    vehicle_color: Optional[str] = Field(None, max_length=32, examples=["white", "black"])
    bounding_box: Optional[BoundingBox] = Field(
        None, description="Vehicle bounding box in normalised coordinates {x1,y1,x2,y2}"
    )
    detection_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, examples=[0.94],
        description="Vehicle detector confidence (0.0–1.0)"
    )

    # ---- Plate reading — uncertain by design ----
    plate_text: Optional[str] = Field(
        None, max_length=20, examples=["KA01AB1234"],
        description="Raw OCR output — not ground truth. Always pair with plate_confidence."
    )
    plate_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, examples=[0.91],
        description="OCR confidence for the plate reading (0.0–1.0)"
    )
    plate_bbox: Optional[BoundingBox] = None
    plate_region: Optional[str] = Field(None, max_length=16, examples=["KA", "IN"])

    # ---- Media references (paths, not blobs) ----
    frame_path: Optional[str] = Field(
        None, max_length=512,
        examples=["s3://traffic-frames/2026/08/30/cam-001/frame_000123.jpg"],
        description="Object-storage path to the source video frame"
    )
    crop_path: Optional[str] = Field(
        None, max_length=512,
        description="Object-storage path to the cropped vehicle image"
    )
    plate_crop_path: Optional[str] = Field(
        None, max_length=512,
        description="Object-storage path to the cropped plate image"
    )

    # ---- Embedding reference ----
    embedding_id: Optional[str] = Field(None, max_length=128)
    embedding_model: Optional[str] = Field(None, max_length=64, examples=["resnet50-reid-v2"])

    # ---- Kinematics ----
    estimated_speed_kmh: Optional[float] = Field(None, ge=0.0, le=500.0)
    direction: Optional[str] = Field(None, max_length=32, examples=["N", "270"])
    lane: Optional[int] = Field(None, ge=1, le=20)

    # ---- Metadata ----
    metadata_: Optional[dict[str, Any]] = Field(
        None, alias="metadata",
        description="Arbitrary pipeline metadata (model version, GPU node, inference ms, etc.)"
    )

    # ---- Validators ----

    @field_validator("observed_at")
    @classmethod
    def must_be_timezone_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware (include tzinfo)")
        return v

    @field_validator("vehicle_class")
    @classmethod
    def validate_vehicle_class(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_VEHICLE_CLASSES:
            raise ValueError(
                f"vehicle_class must be one of: {', '.join(sorted(VALID_VEHICLE_CLASSES))}"
            )
        return v

    @model_validator(mode="after")
    def plate_confidence_requires_plate_text(self) -> VehicleObservationCreate:
        """If plate_confidence is provided, plate_text must also be present."""
        if self.plate_confidence is not None and not self.plate_text:
            raise ValueError("plate_confidence provided without plate_text")
        return self


# ---------------------------------------------------------------------------
# Status update schema
# ---------------------------------------------------------------------------

class VehicleObservationStatusUpdate(AppBaseModel):
    """Update only the lifecycle status of an observation."""
    status: str = Field(..., description="New lifecycle status")
    rejection_reason: Optional[str] = Field(
        None, description="Required when status is 'rejected'"
    )

    @model_validator(mode="after")
    def validate_status_update(self) -> VehicleObservationStatusUpdate:
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"
            )
        if self.status == "rejected" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when setting status to 'rejected'")
        return self


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class VehicleObservationResponse(AppBaseModel):
    """Full observation response — mirrors the DB record."""
    id: uuid.UUID
    source: str
    source_observation_id: str
    camera_id: uuid.UUID
    observed_at: datetime
    frame_number: Optional[int] = None

    vehicle_class: Optional[str] = None
    vehicle_color: Optional[str] = None
    bounding_box: Optional[dict] = None
    detection_confidence: Optional[float] = None

    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    plate_bbox: Optional[dict] = None
    plate_region: Optional[str] = None

    frame_path: Optional[str] = None
    crop_path: Optional[str] = None
    plate_crop_path: Optional[str] = None

    embedding_id: Optional[str] = None
    embedding_model: Optional[str] = None

    estimated_speed_kmh: Optional[float] = None
    direction: Optional[str] = None
    lane: Optional[int] = None

    status: str
    rejection_reason: Optional[str] = None

    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Bulk ingestion schemas
# ---------------------------------------------------------------------------

class BulkObservationRequest(AppBaseModel):
    """Request body for bulk observation ingestion."""
    observations: list[VehicleObservationCreate] = Field(
        ..., min_length=1, max_length=500,
        description="List of observations to ingest (max 500 per request)"
    )


class BulkObservationRejected(AppBaseModel):
    """A single rejected item from a bulk ingestion request."""
    index: int = Field(..., description="0-based index of the rejected observation in the request")
    source_observation_id: Optional[str] = None
    reason: str = Field(..., description="Human-readable rejection reason")
    errors: list[str] = Field(default_factory=list, description="Detailed validation errors")


class BulkObservationResponse(AppBaseModel):
    """Response from bulk ingestion — reports accepted and rejected records."""
    accepted_count: int
    rejected_count: int
    accepted: list[VehicleObservationResponse]
    rejected: list[BulkObservationRejected]


# ---------------------------------------------------------------------------
# Filter parameters (used in list endpoint)
# ---------------------------------------------------------------------------

class ObservationFilters(AppBaseModel):
    """Query filters for listing observations."""
    camera_id: Optional[uuid.UUID] = None
    observed_after: Optional[datetime] = None
    observed_before: Optional[datetime] = None
    plate_text: Optional[str] = Field(
        None, max_length=20,
        description="Partial plate text match (case-insensitive)"
    )
    vehicle_class: Optional[str] = None
    min_detection_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[str] = None
    source: Optional[str] = None
