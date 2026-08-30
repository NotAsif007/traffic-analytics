"""Urban Traffic Analytics endpoints — /api/v1/analytics/."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBSession
from app.schemas.analytics import (
    CameraHealthResponse,
    CongestionReportResponse,
    ODMatrixResponse,
    RouteFrequencyResponse,
    TrafficDensityResponse,
    TrafficVolumeResponse,
    TravelTimeStatsResponse,
    VehicleClassDistributionResponse,
)
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _analytics_service(db: DBSession) -> AnalyticsService:
    return AnalyticsService(db)


AnalyticsServiceDep = Annotated[AnalyticsService, Depends(_analytics_service)]


def _default_time_window(
    start_time: datetime | None, end_time: datetime | None
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end = end_time or now
    start = start_time or (end - timedelta(hours=24))
    return start, end


@router.get(
    "/volume",
    response_model=TrafficVolumeResponse,
    summary="Get traffic volume time-bucketed across cameras",
)
async def get_traffic_volume(
    svc: AnalyticsServiceDep,
    interval: str = Query("1h", description="1m | 5m | 15m | 1h | 1d"),
    start_time: datetime | None = Query(None, description="Start timestamp (default: 24h ago)"),
    end_time: datetime | None = Query(None, description="End timestamp (default: now)"),
    camera_id: uuid.UUID | None = Query(None, description="Filter by camera UUID"),
    road_id: uuid.UUID | None = Query(None, description="Filter by road UUID"),
    vehicle_class: str | None = Query(None, description="Filter by vehicle class"),
) -> TrafficVolumeResponse:
    start, end = _default_time_window(start_time, end_time)
    return await svc.get_traffic_volume(
        start_time=start,
        end_time=end,
        interval=interval,
        camera_id=camera_id,
        road_id=road_id,
        vehicle_class=vehicle_class,
    )


@router.get(
    "/class-distribution",
    response_model=VehicleClassDistributionResponse,
    summary="Get vehicle classification breakdown and percentages",
)
async def get_vehicle_class_distribution(
    svc: AnalyticsServiceDep,
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    camera_id: uuid.UUID | None = Query(None),
    road_id: uuid.UUID | None = Query(None),
) -> VehicleClassDistributionResponse:
    start, end = _default_time_window(start_time, end_time)
    return await svc.get_vehicle_class_distribution(
        start_time=start, end_time=end, camera_id=camera_id, road_id=road_id
    )


@router.get(
    "/density",
    response_model=TrafficDensityResponse,
    summary="Get traffic density metrics with transparent flow-theory methodology",
)
async def get_traffic_density(
    svc: AnalyticsServiceDep,
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    camera_id: uuid.UUID | None = Query(None),
    road_id: uuid.UUID | None = Query(None),
) -> TrafficDensityResponse:
    start, end = _default_time_window(start_time, end_time)
    return await svc.get_traffic_density(
        start_time=start, end_time=end, camera_id=camera_id, road_id=road_id
    )


@router.get(
    "/travel-times",
    response_model=TravelTimeStatsResponse,
    summary="Get mean, median, p85, and p95 travel times between connected camera pairs",
)
async def get_travel_time_stats(
    svc: AnalyticsServiceDep,
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    source_camera_id: uuid.UUID | None = Query(None),
    destination_camera_id: uuid.UUID | None = Query(None),
) -> TravelTimeStatsResponse:
    start, end = _default_time_window(start_time, end_time)
    return await svc.get_travel_time_stats(
        start_time=start,
        end_time=end,
        source_camera_id=source_camera_id,
        destination_camera_id=destination_camera_id,
    )


@router.get(
    "/congestion",
    response_model=CongestionReportResponse,
    summary="Get real-time congestion report comparing current travel times against baselines",
)
async def get_congestion_report(
    svc: AnalyticsServiceDep,
) -> CongestionReportResponse:
    return await svc.get_congestion_report()


@router.get(
    "/od-matrix",
    response_model=ODMatrixResponse,
    summary="Get Origin-Destination matrix from completed vehicle journeys",
)
async def get_od_matrix(
    svc: AnalyticsServiceDep,
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
) -> ODMatrixResponse:
    start, end = _default_time_window(start_time, end_time)
    return await svc.get_od_matrix(start_time=start, end_time=end)


@router.get(
    "/routes",
    response_model=RouteFrequencyResponse,
    summary="Get most frequently traveled multi-camera routes",
)
async def get_route_frequency(
    svc: AnalyticsServiceDep,
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
) -> RouteFrequencyResponse:
    start, end = _default_time_window(start_time, end_time)
    return await svc.get_route_frequency(start_time=start, end_time=end, limit=limit)


@router.get(
    "/camera-health",
    response_model=CameraHealthResponse,
    summary="Get real-time camera health, observations/minute throughput, and inactivity status",
)
async def get_camera_health(
    svc: AnalyticsServiceDep,
) -> CameraHealthResponse:
    return await svc.get_camera_health()
