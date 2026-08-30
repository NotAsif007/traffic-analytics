"""Dashboard and Command Center dedicated read-optimized schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field

from app.schemas.common import AppBaseModel
from app.schemas.trajectory import TrajectoryTimelineSegment


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
    camera_name: Optional[str] = None
    severity: Optional[str] = None


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
    last_observation_time: Optional[datetime] = None


class MapRoadSegment(AppBaseModel):
    id: uuid.UUID
    name: str
    geometry_geojson: dict[str, Any]
    current_congestion_index: float = 1.0


class MapTrajectoryLine(AppBaseModel):
    trajectory_id: uuid.UUID
    vehicle_identity_id: uuid.UUID
    canonical_plate: Optional[str] = None
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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    camera_name: Optional[str] = None
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
    raw_plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    detection_confidence: float
    vehicle_class: str
    vehicle_color: str
    image_path: Optional[str] = None
    plate_crop_path: Optional[str] = None


class CameraVisitTimeline(AppBaseModel):
    step_number: int
    camera_id: uuid.UUID
    camera_name: str
    latitude: float
    longitude: float
    timestamp: datetime
    dwell_or_transit_seconds: Optional[float] = None
    segment_speed_kmh: Optional[float] = None


class VehicleInvestigationResponse(AppBaseModel):
    """
    Complete law enforcement forensic profile for a vehicle identity.
    """
    identity_id: uuid.UUID
    canonical_plate: Optional[str] = None
    vehicle_class: str
    vehicle_color: str
    overall_confidence: float
    first_seen_at: datetime
    last_seen_at: datetime
    total_sightings_count: int
    last_known_camera_name: Optional[str] = None
    last_known_coordinates: Optional[list[float]] = None  # [lon, lat]
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
    direction: Optional[str] = None


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
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    vehicle_identity_id: Optional[uuid.UUID] = None
    canonical_plate: Optional[str] = None
    cameras_involved: list[CameraBrief] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    trajectory_summary: Optional[MapTrajectoryLine] = None


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
