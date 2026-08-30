"""VehicleTrack and TrackPoint Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import AppBaseModel
from app.schemas.vehicle_observation import BoundingBox

VALID_TRACK_STATUSES = {"active", "completed", "lost", "terminated"}


# ---------------------------------------------------------------------------
# TrackPoint Schemas
# ---------------------------------------------------------------------------

class TrackPointBase(AppBaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the track point (timezone-aware)")
    frame_number: Optional[int] = Field(None, ge=0)
    bounding_box: Optional[BoundingBox] = Field(
        None, description="Vehicle bounding box in normalised coordinates {x1,y1,x2,y2}"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    estimated_speed_kmh: Optional[float] = Field(None, ge=0.0, le=500.0)
    plate_text: Optional[str] = Field(None, max_length=20)
    plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class TrackPointCreate(TrackPointBase):
    camera_id: uuid.UUID
    observation_id: Optional[uuid.UUID] = None


class TrackPointResponse(TrackPointBase):
    id: uuid.UUID
    track_id: uuid.UUID
    camera_id: uuid.UUID
    observation_id: Optional[uuid.UUID] = None
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
    vehicle_class: Optional[str] = Field(None, max_length=64, examples=["car", "truck", "motorcycle"])
    vehicle_color: Optional[str] = Field(None, max_length=32, examples=["white", "black"])
    best_plate_text: Optional[str] = Field(None, max_length=20, examples=["KA01AB1234"])
    best_plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    points_count: int = Field(default=0, ge=0)
    notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")

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
    status: Optional[str] = None
    end_time: Optional[datetime] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    vehicle_class: Optional[str] = None
    vehicle_color: Optional[str] = None
    best_plate_text: Optional[str] = None
    best_plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    points_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
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
    camera_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    vehicle_class: Optional[str] = None
    plate_text: Optional[str] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    start_after: Optional[datetime] = None
    end_before: Optional[datetime] = None
