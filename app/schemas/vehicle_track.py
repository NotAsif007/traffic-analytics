"""VehicleTrack and TrackPoint Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import AppBaseModel
from app.schemas.vehicle_observation import BoundingBox

VALID_TRACK_STATUSES = {"active", "completed", "lost", "terminated"}


# ---------------------------------------------------------------------------
# TrackPoint Schemas
# ---------------------------------------------------------------------------


class TrackPointBase(AppBaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the track point (timezone-aware)")
    frame_number: int | None = Field(None, ge=0)
    bounding_box: BoundingBox | None = Field(
        None, description="Vehicle bounding box in normalised coordinates {x1,y1,x2,y2}"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    estimated_speed_kmh: float | None = Field(None, ge=0.0, le=500.0)
    plate_text: str | None = Field(None, max_length=20)
    plate_confidence: float | None = Field(None, ge=0.0, le=1.0)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class TrackPointCreate(TrackPointBase):
    camera_id: uuid.UUID
    observation_id: uuid.UUID | None = None


class TrackPointResponse(TrackPointBase):
    id: uuid.UUID
    track_id: uuid.UUID
    camera_id: uuid.UUID
    observation_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# VehicleTrack Schemas
# ---------------------------------------------------------------------------


class VehicleTrackBase(AppBaseModel):
    track_id: str = Field(..., min_length=1, max_length=64, examples=["TRK-CAM01-001"])
    camera_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: str = Field(default="active", examples=["active", "completed", "lost", "terminated"])
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    vehicle_class: str | None = Field(None, max_length=64, examples=["car", "truck", "motorcycle"])
    vehicle_color: str | None = Field(None, max_length=32, examples=["white", "black"])
    best_plate_text: str | None = Field(None, max_length=20, examples=["KA01AB1234"])
    best_plate_confidence: float | None = Field(None, ge=0.0, le=1.0)
    points_count: int = Field(default=0, ge=0)
    notes: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_TRACK_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_TRACK_STATUSES))}")
        return v

    @model_validator(mode="after")
    def validate_time_order(self) -> VehicleTrackBase:
        if self.start_time > self.end_time:
            raise ValueError("start_time must be less than or equal to end_time")
        return self


class VehicleTrackCreate(VehicleTrackBase):
    pass


class VehicleTrackUpdate(AppBaseModel):
    status: str | None = None
    end_time: datetime | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    vehicle_class: str | None = None
    vehicle_color: str | None = None
    best_plate_text: str | None = None
    best_plate_confidence: float | None = Field(None, ge=0.0, le=1.0)
    points_count: int | None = Field(None, ge=0)
    notes: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TRACK_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_TRACK_STATUSES))}")
        return v


class VehicleTrackResponse(VehicleTrackBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class VehicleTrackDetailResponse(VehicleTrackResponse):
    """Detailed track response including full chronological track points."""

    track_points: list[TrackPointResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Filter schema for list endpoint
# ---------------------------------------------------------------------------


class TrackFilters(AppBaseModel):
    camera_id: uuid.UUID | None = None
    status: str | None = None
    vehicle_class: str | None = None
    plate_text: str | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    start_after: datetime | None = None
    end_before: datetime | None = None
