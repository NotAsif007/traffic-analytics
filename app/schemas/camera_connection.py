"""CameraConnection Pydantic schemas."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import ConfigDict, Field, model_validator

from app.schemas.common import AppBaseModel

VALID_CONNECTION_TYPES = {"direct", "via_junction", "u_turn", "merge"}


class CameraConnectionBase(AppBaseModel):
    source_camera_id: uuid.UUID
    destination_camera_id: uuid.UUID
    road_id: Optional[uuid.UUID] = None
    min_travel_time_s: int = Field(..., gt=0, examples=[30], description="Minimum plausible travel time (seconds)")
    max_travel_time_s: int = Field(..., gt=0, examples=[120], description="Maximum plausible travel time (seconds)")
    avg_travel_time_s: Optional[int] = Field(None, gt=0, examples=[60])
    distance_m: Optional[float] = Field(None, gt=0, examples=[850.0], description="Route distance in metres")
    connection_type: Optional[str] = Field(None, examples=["direct"])
    notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")

    @model_validator(mode="after")
    def validate_connection(self) -> CameraConnectionBase:
        # Source and destination must differ
        if self.source_camera_id == self.destination_camera_id:
            raise ValueError("source_camera_id and destination_camera_id must be different")
        # min must be <= max
        if self.min_travel_time_s > self.max_travel_time_s:
            raise ValueError(
                "min_travel_time_s must be less than or equal to max_travel_time_s"
            )
        # avg must be within bounds if provided
        if self.avg_travel_time_s is not None:
            if not (self.min_travel_time_s <= self.avg_travel_time_s <= self.max_travel_time_s):
                raise ValueError(
                    "avg_travel_time_s must be between min_travel_time_s and max_travel_time_s"
                )
        # connection_type must be valid if provided
        if self.connection_type and self.connection_type not in VALID_CONNECTION_TYPES:
            raise ValueError(
                f"connection_type must be one of: {', '.join(sorted(VALID_CONNECTION_TYPES))}"
            )
        return self


class CameraConnectionCreate(CameraConnectionBase):
    """Request body for creating a camera connection."""
    pass


class CameraConnectionUpdate(AppBaseModel):
    """Request body for updating a connection (all fields optional)."""
    road_id: Optional[uuid.UUID] = None
    min_travel_time_s: Optional[int] = Field(None, gt=0)
    max_travel_time_s: Optional[int] = Field(None, gt=0)
    avg_travel_time_s: Optional[int] = Field(None, gt=0)
    distance_m: Optional[float] = Field(None, gt=0)
    connection_type: Optional[str] = None
    notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(None, alias="metadata")


class CameraConnectionResponse(CameraConnectionBase):
    """Full connection response including server-generated fields."""
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
