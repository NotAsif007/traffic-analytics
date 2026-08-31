"""Trajectory and TrajectoryPoint Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import AppBaseModel
from app.schemas.road import GeoJSONGeometry

VALID_TRAJECTORY_STATUSES = {"active", "completed", "terminated"}


# ---------------------------------------------------------------------------
# TrajectoryPoint Schemas
# ---------------------------------------------------------------------------


class TrajectoryPointBase(AppBaseModel):
    sequence_order: int = Field(..., ge=1, description="1-based sequence order along trajectory")
    camera_id: uuid.UUID
    observation_id: uuid.UUID | None = None
    track_id: uuid.UUID | None = None
    timestamp: datetime
    plate_text: str | None = None
    plate_confidence: float | None = Field(None, ge=0.0, le=1.0)
    speed_kmh: float | None = Field(None, ge=0.0, le=500.0)
    segment_distance_m: float | None = Field(None, ge=0.0)
    segment_duration_s: float | None = Field(None, ge=0.0)
    is_interpolated: bool = Field(default=False)
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class TrajectoryPointCreate(TrajectoryPointBase):
    pass


class TrajectoryPointResponse(TrajectoryPointBase):
    id: uuid.UUID
    trajectory_id: uuid.UUID
    camera_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Trajectory Schemas
# ---------------------------------------------------------------------------


class TrajectoryBase(AppBaseModel):
    trajectory_id: str = Field(..., examples=["TRJ-20260830-0001"])
    vehicle_identity_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: str = Field(default="active", examples=["active", "completed", "terminated"])
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    total_distance_m: float = Field(default=0.0, ge=0.0)
    total_travel_time_s: int = Field(default=0, ge=0)
    average_speed_kmh: float | None = Field(None, ge=0.0, le=500.0)
    points_count: int = Field(default=1, ge=1)
    ordered_camera_ids: list[uuid.UUID] = Field(default_factory=list)
    ordered_camera_names: list[str] = Field(default_factory=list)
    notes: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_TRAJECTORY_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(VALID_TRAJECTORY_STATUSES))}"
            )
        return v

    @model_validator(mode="after")
    def validate_time_order(self) -> TrajectoryBase:
        if self.start_time > self.end_time:
            raise ValueError("start_time must be <= end_time")
        return self


class TrajectoryCreate(TrajectoryBase):
    pass


class TrajectoryResponse(TrajectoryBase):
    id: uuid.UUID
    route_geometry: GeoJSONGeometry | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrajectoryDetailResponse(TrajectoryResponse):
    """Detailed trajectory response including chronological points."""

    points: list[TrajectoryPointResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Timeline Schemas (Explainable Journey Representation)
# ---------------------------------------------------------------------------


class TrajectoryTimelineSegment(AppBaseModel):
    """Detailed segment description between two consecutive trajectory nodes."""

    from_sequence: int
    to_sequence: int
    from_camera_id: uuid.UUID
    from_camera_name: str | None = None
    to_camera_id: uuid.UUID
    to_camera_name: str | None = None
    from_timestamp: datetime
    to_timestamp: datetime
    elapsed_seconds: float
    distance_meters: float
    speed_kmh: float | None = None
    plate_text: str | None = None
    plate_confidence: float | None = None
    is_connected_road: bool
    segment_status: str = Field(default="plausible", description="plausible | speed_warning | gap")


class TrajectoryTimelineResponse(AppBaseModel):
    """Complete chronological audit timeline for a vehicle journey."""

    trajectory_id: str
    vehicle_identity_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    total_travel_time_seconds: int
    total_travel_time_formatted: str
    total_distance_km: float
    average_speed_kmh: float | None = None
    route_summary: str
    confidence: float
    status: str
    segments: list[TrajectoryTimelineSegment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Predictive Forward Trajectory Schemas
# ---------------------------------------------------------------------------


class PredictedNextHop(AppBaseModel):
    """Forecasted candidate next camera with arrival time and probability."""

    camera_id: uuid.UUID
    camera_name: str
    road_name: str | None = None
    probability: float = Field(..., ge=0.0, le=1.0, description="Markov transition probability [0-1]")
    distance_meters: float
    estimated_travel_time_seconds: float
    estimated_arrival_time: datetime
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class TrajectoryPredictionResponse(AppBaseModel):
    """Forward trajectory forecast predicting next camera intercepts and ETAs."""

    trajectory_id: str
    vehicle_identity_id: uuid.UUID
    current_camera_id: uuid.UUID
    current_camera_name: str
    last_seen_timestamp: datetime
    current_speed_kmh: float | None = None
    predicted_next_hops: list[PredictedNextHop] = Field(default_factory=list)
    predicted_destination_corridor: str | None = None
    deviation_risk_level: str = Field(default="LOW", description="LOW | MEDIUM | HIGH")
    forecast_method: str = "Markov Spatio-Temporal Graph Propagation"


# ---------------------------------------------------------------------------
# Query Filters
# ---------------------------------------------------------------------------


class TrajectoryFilters(AppBaseModel):
    vehicle_identity_id: uuid.UUID | None = None
    camera_id: uuid.UUID | None = None
    status: str | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    start_after: datetime | None = None
    end_before: datetime | None = None

