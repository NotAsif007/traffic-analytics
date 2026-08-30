"""VehicleIdentity and VehicleMatch Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.schemas.common import AppBaseModel

VALID_IDENTITY_STATUSES = {"candidate", "accepted", "rejected", "needs_review"}


class VehicleMatchResponse(AppBaseModel):
    id: uuid.UUID
    vehicle_identity_id: uuid.UUID
    source_observation_id: uuid.UUID | None = None
    source_track_id: uuid.UUID | None = None
    source_camera_id: uuid.UUID
    target_observation_id: uuid.UUID | None = None
    target_track_id: uuid.UUID | None = None
    target_camera_id: uuid.UUID
    match_score: float = Field(..., ge=0.0, le=1.0)
    status: str
    signals: dict[str, Any]
    reasoning: str
    rejection_reason: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class VehicleIdentityBase(AppBaseModel):
    identity_code: str = Field(..., examples=["VID-20260830-0001"])
    primary_plate: str | None = Field(None, max_length=20, examples=["KA01AB1234"])
    plate_confidence: float | None = Field(None, ge=0.0, le=1.0)
    vehicle_class: str | None = Field(None, max_length=64, examples=["car", "truck"])
    vehicle_color: str | None = Field(None, max_length=32, examples=["white", "black"])
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    status: str = Field(
        default="candidate", examples=["candidate", "accepted", "rejected", "needs_review"]
    )
    first_seen_at: datetime
    last_seen_at: datetime
    total_sightings: int = Field(default=1, ge=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reid_embedding_id: str | None = None
    notes: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_IDENTITY_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_IDENTITY_STATUSES))}")
        return v


class VehicleIdentityCreate(VehicleIdentityBase):
    pass


class VehicleIdentityResponse(VehicleIdentityBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class VehicleIdentityDetailResponse(VehicleIdentityResponse):
    """Full detail of a vehicle identity including all associated match events."""

    matches: list[VehicleMatchResponse] = Field(default_factory=list)


class IdentityFilters(AppBaseModel):
    status: str | None = None
    primary_plate: str | None = None
    vehicle_class: str | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    seen_after: datetime | None = None
    seen_before: datetime | None = None


class AssociateSightingsRequest(AppBaseModel):
    """Request payload to manually or automatically trigger association for a sighting."""

    observation_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    max_search_window_minutes: int = Field(default=60, ge=1, le=1440)
