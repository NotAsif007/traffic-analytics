"""Dashboard and Command Center dedicated read-optimized schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import AppBaseModel

# ---------------------------------------------------------------------------
# City Overview Schemas
# ---------------------------------------------------------------------------


class CongestionHotspot(AppBaseModel):
    corridor_name: str
    source_camera_name: str
    destination_camera_name: str
    congestion_index: float
    current_travel_time_s: float
    baseline_travel_time_s: float
    severity: str = Field(..., description="low | moderate | high | severe")


class RecentActivityItem(AppBaseModel):
    activity_type: str = Field(..., description="OBSERVATION | ALERT | TRAJECTORY_UPDATE")
    title: str
    description: str
    timestamp: datetime
    camera_name: str | None = None
    severity: str | None = None


class CityOverviewResponse(AppBaseModel):
    """
    Read-optimized high-level summary of city-wide traffic and surveillance operations.
    """

    generated_at: datetime
    active_cameras_count: int
    total_cameras_count: int
    cameras_online_percentage: float
    vehicles_observed_today: int
    current_traffic_level: str = Field(..., description="low | moderate | heavy | congested")
    active_alerts_count: int
    critical_alerts_count: int
    congestion_hotspots: list[CongestionHotspot] = Field(default_factory=list)
    recent_activity: list[RecentActivityItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Live Map Schemas
# ---------------------------------------------------------------------------


class MapCameraNode(AppBaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    status: str = Field(..., description="online | stale | offline")
    current_intensity: str = Field(..., description="low | moderate | high")
    observations_last_hour: int
    last_observation_time: datetime | None = None


class MapRoadSegment(AppBaseModel):
    id: uuid.UUID
    name: str
    geometry_geojson: dict[str, Any]
    current_congestion_index: float = 1.0


class MapTrajectoryLine(AppBaseModel):
    trajectory_id: uuid.UUID
    vehicle_identity_id: uuid.UUID
    canonical_plate: str | None = None
    coordinates: list[list[float]] = Field(
        ..., description="List of [lon, lat] coordinate pairs along route"
    )
    confidence: float
    start_time: datetime
    last_seen_time: datetime
    total_distance_m: float
    camera_names: list[str] = Field(default_factory=list)


class MapAlertMarker(AppBaseModel):
    id: uuid.UUID
    alert_code: str
    alert_type: str
    severity: str
    latitude: float | None = None
    longitude: float | None = None
    camera_name: str | None = None
    title: str
    timestamp: datetime


class LiveMapResponse(AppBaseModel):
    """
    Read-optimized GIS spatial payload for real-time map rendering.
    """

    generated_at: datetime
    cameras: list[MapCameraNode] = Field(default_factory=list)
    road_segments: list[MapRoadSegment] = Field(default_factory=list)
    active_trajectories: list[MapTrajectoryLine] = Field(default_factory=list)
    active_alerts: list[MapAlertMarker] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Vehicle Investigation Schemas
# ---------------------------------------------------------------------------


class PlateObservationEvidence(AppBaseModel):
    observation_id: uuid.UUID
    camera_id: uuid.UUID
    camera_name: str
    timestamp: datetime
    raw_plate_text: str | None = None
    plate_confidence: float | None = None
    detection_confidence: float
    vehicle_class: str
    vehicle_color: str
    image_path: str | None = None
    plate_crop_path: str | None = None


class CameraVisitTimeline(AppBaseModel):
    step_number: int
    camera_id: uuid.UUID
    camera_name: str
    latitude: float
    longitude: float
    timestamp: datetime
    dwell_or_transit_seconds: float | None = None
    segment_speed_kmh: float | None = None


class VehicleInvestigationResponse(AppBaseModel):
    """
    Complete law enforcement forensic profile for a vehicle identity.
    """

    identity_id: uuid.UUID
    canonical_plate: str | None = None
    vehicle_class: str
    vehicle_color: str
    overall_confidence: float
    first_seen_at: datetime
    last_seen_at: datetime
    total_sightings_count: int
    last_known_camera_name: str | None = None
    last_known_coordinates: list[float] | None = None  # [lon, lat]
    camera_history: list[CameraVisitTimeline] = Field(default_factory=list)
    plate_observations: list[PlateObservationEvidence] = Field(default_factory=list)
    active_alerts: list[MapAlertMarker] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Alert Investigation Schemas
# ---------------------------------------------------------------------------


class CameraBrief(AppBaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    direction: str | None = None


class AlertInvestigationResponse(AppBaseModel):
    """
    Complete forensic dossier and explainability breakdown for a triggered alert.
    """

    alert_id: uuid.UUID
    alert_code: str
    alert_type: str
    severity: str
    status: str
    confidence: float
    title: str
    description: str
    created_at: datetime
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_notes: str | None = None
    vehicle_identity_id: uuid.UUID | None = None
    canonical_plate: str | None = None
    cameras_involved: list[CameraBrief] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    trajectory_summary: MapTrajectoryLine | None = None


# ---------------------------------------------------------------------------
# Consolidated Dashboard Analytics Schema
# ---------------------------------------------------------------------------


class DashboardAnalyticsSummaryResponse(AppBaseModel):
    """
    Consolidated metrics summary tailored for the Executive Dashboard overview.
    """

    generated_at: datetime
    total_vehicles_past_24h: int
    hourly_volume_trend: list[dict[str, Any]] = Field(default_factory=list)
    top_congested_corridors: list[CongestionHotspot] = Field(default_factory=list)
    top_frequent_routes: list[dict[str, Any]] = Field(default_factory=list)
    top_od_flows: list[dict[str, Any]] = Field(default_factory=list)
