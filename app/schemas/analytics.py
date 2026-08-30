"""Pydantic schemas for Urban Traffic Analytics."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from app.schemas.common import AppBaseModel


# ---------------------------------------------------------------------------
# 1. Traffic Volume
# ---------------------------------------------------------------------------

class TrafficVolumeBucket(AppBaseModel):
    bucket_start: datetime
    bucket_end: datetime
    camera_id: Optional[uuid.UUID] = None
    camera_name: Optional[str] = None
    vehicle_count: int
    vehicle_class_counts: dict[str, int] = Field(default_factory=dict)


class TrafficVolumeResponse(AppBaseModel):
    interval: str = Field(..., description="1m | 5m | 15m | 1h | 1d")
    start_time: datetime
    end_time: datetime
    total_vehicles: int
    buckets: list[TrafficVolumeBucket] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. Vehicle-Class Distribution
# ---------------------------------------------------------------------------

class VehicleClassCount(AppBaseModel):
    vehicle_class: str
    count: int
    percentage: float = Field(..., ge=0.0, le=100.0)


class VehicleClassDistributionResponse(AppBaseModel):
    start_time: datetime
    end_time: datetime
    total_classified_vehicles: int
    distribution: list[VehicleClassCount] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 3. Traffic Density (Transparent Methodology)
# ---------------------------------------------------------------------------

class TrafficDensityResponse(AppBaseModel):
    camera_id: Optional[uuid.UUID] = None
    camera_name: Optional[str] = None
    road_id: Optional[uuid.UUID] = None
    road_name: Optional[str] = None
    start_time: datetime
    end_time: datetime
    flow_rate_veh_per_hour: float
    space_mean_speed_kmh: float
    density_veh_per_km: float
    density_level: str = Field(..., description="low | moderate | high | congested")
    methodology: str = Field(
        default=(
            "Density (k, in vehicles/km) is calculated using the fundamental traffic flow theory equation: "
            "k = q / v_s, where q is the observed hourly flow rate (vehicles/hour) and v_s is the "
            "space-mean speed (km/h) across observed vehicle trajectory points."
        ),
        description="Explicit mathematical definition of density measurement for transparent reporting",
    )


# ---------------------------------------------------------------------------
# 4. Average Travel Time & Percentiles
# ---------------------------------------------------------------------------

class PairTravelTime(AppBaseModel):
    source_camera_id: uuid.UUID
    source_camera_name: Optional[str] = None
    destination_camera_id: uuid.UUID
    destination_camera_name: Optional[str] = None
    sample_count: int
    mean_travel_time_seconds: float
    median_travel_time_seconds: float
    p85_travel_time_seconds: float
    p95_travel_time_seconds: float
    min_travel_time_seconds: float
    max_travel_time_seconds: float


class TravelTimeStatsResponse(AppBaseModel):
    start_time: datetime
    end_time: datetime
    pairs: list[PairTravelTime] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 5. Congestion Indicator
# ---------------------------------------------------------------------------

class CongestionSegment(AppBaseModel):
    source_camera_id: uuid.UUID
    source_camera_name: Optional[str] = None
    destination_camera_id: uuid.UUID
    destination_camera_name: Optional[str] = None
    current_mean_travel_time_s: float
    baseline_travel_time_s: float
    congestion_indicator: float = Field(
        ...,
        description="Ratio of current travel time to baseline (1.0 = normal, >1.3 = heavy, >2.0 = severe)",
    )
    status: str = Field(..., description="free_flow | moderate | heavy | severe")


class CongestionReportResponse(AppBaseModel):
    timestamp: datetime
    summary_congestion_index: float
    overall_status: str
    segments: list[CongestionSegment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. Origin-Destination Matrix
# ---------------------------------------------------------------------------

class ODMatrixCell(AppBaseModel):
    origin_camera_id: uuid.UUID
    origin_camera_name: Optional[str] = None
    destination_camera_id: uuid.UUID
    destination_camera_name: Optional[str] = None
    trip_count: int
    average_duration_seconds: float
    average_distance_meters: float


class ODMatrixResponse(AppBaseModel):
    start_time: datetime
    end_time: datetime
    total_trips: int
    matrix: list[ODMatrixCell] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 7. Route Frequency
# ---------------------------------------------------------------------------

class RouteFrequencyItem(AppBaseModel):
    route_camera_names: list[str]
    route_summary: str
    trip_count: int
    percentage: float
    average_duration_seconds: float
    average_distance_km: float


class RouteFrequencyResponse(AppBaseModel):
    start_time: datetime
    end_time: datetime
    total_trips_analyzed: int
    top_routes: list[RouteFrequencyItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 8. Camera Health & Telemetry
# ---------------------------------------------------------------------------

class CameraHealthItem(AppBaseModel):
    camera_id: uuid.UUID
    camera_name: str
    status: str = Field(..., description="online | stale | offline | error")
    observations_last_hour: int
    observations_per_minute: float
    last_observation_at: Optional[datetime] = None
    inactivity_seconds: Optional[int] = None


class CameraHealthResponse(AppBaseModel):
    timestamp: datetime
    total_cameras: int
    online_cameras: int
    offline_cameras: int
    cameras: list[CameraHealthItem] = Field(default_factory=list)
