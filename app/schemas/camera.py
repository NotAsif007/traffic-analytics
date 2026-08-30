"""Camera Pydantic schemas."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import ConfigDict, Field, field_validator

from app.schemas.common import AppBaseModel
from app.schemas.road import GeoJSONGeometry

VALID_STATUSES = {"active", "inactive", "maintenance", "fault"}


class CameraBase(AppBaseModel):
    camera_id: str = Field(
        ..., min_length=1, max_length=64, examples=["CAM-001"]
    )
    name: str = Field(..., min_length=1, max_length=255, examples=["Junction Camera - MG Road N"])
    road_id: Optional[uuid.UUID] = None
    direction: Optional[str] = Field(
        None,
        max_length=32,
        examples=["N", "NE", "270"],
        description="Heading in degrees (0-359) or cardinal direction",
    )
    fov_degrees: Optional[int] = Field(None, ge=1, le=360, examples=[120])
    lane_count: Optional[int] = Field(None, ge=1, le=20, examples=[3])
    lane_coverage: Optional[str] = Field(None, max_length=64, examples=["1,2,3"])
    status: str = Field(
        default="active",
        examples=["active", "inactive", "maintenance", "fault"],
    )
    timezone: str = Field(default="Asia/Kolkata", max_length=64, examples=["Asia/Kolkata"])
    height_m: Optional[int] = Field(None, ge=1, le=50, examples=[6])
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    notes: Optional[str] = None
    location: Optional[GeoJSONGeometry] = Field(
        None, description="GeoJSON Point of camera position"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
        return v


class CameraCreate(CameraBase):
    """Request body for creating a camera."""
    pass


class CameraUpdate(AppBaseModel):
    """Request body for updating a camera (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    road_id: Optional[uuid.UUID] = None
    direction: Optional[str] = Field(None, max_length=32)
    fov_degrees: Optional[int] = Field(None, ge=1, le=360)
    lane_count: Optional[int] = Field(None, ge=1, le=20)
    lane_coverage: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = None
    timezone: Optional[str] = Field(None, max_length=64)
    height_m: Optional[int] = Field(None, ge=1, le=50)
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")
    notes: Optional[str] = None
    location: Optional[GeoJSONGeometry] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}")
        return v


class CameraResponse(CameraBase):
    """Full camera response including server-generated fields."""
    id: uuid.UUID
    road_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
