"""Command Center Dashboard API endpoints — /api/v1/dashboard."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession
from app.schemas.dashboard import (
    AlertInvestigationResponse,
    CityOverviewResponse,
    DashboardAnalyticsSummaryResponse,
    LiveMapResponse,
    VehicleInvestigationResponse,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _dashboard_service(db: DBSession) -> DashboardService:
    return DashboardService(db)


DashboardServiceDep = Annotated[DashboardService, Depends(_dashboard_service)]


@router.get(
    "/overview",
    response_model=CityOverviewResponse,
    summary="Get high-level city traffic, active cameras, congestion level, and alerts summary",
)
async def get_city_overview(
    svc: DashboardServiceDep,
) -> CityOverviewResponse:
    """
    Returns an aggregated high-level city operational overview for the top stats cards
    and summary widgets on the command center dashboard.
    """
    return await svc.get_city_overview()


@router.get(
    "/map",
    response_model=LiveMapResponse,
    summary="Get real-time GIS map layers: cameras, road network, active trajectories, and alerts",
)
async def get_live_map(
    svc: DashboardServiceDep,
) -> LiveMapResponse:
    """
    Returns complete geospatial layers optimized for Leaflet / Mapbox GIS rendering
    including camera markers, road polylines, moving trajectory paths, and alert pins.
    """
    return await svc.get_live_map()


@router.get(
    "/investigate/vehicle/{identity_id}",
    response_model=VehicleInvestigationResponse,
    summary="Retrieve complete forensic timeline and plate evidence for a vehicle identity",
)
async def investigate_vehicle(
    identity_id: uuid.UUID,
    svc: DashboardServiceDep,
) -> VehicleInvestigationResponse:
    """
    Returns detailed forensic dossier for a vehicle identity including all camera sightings,
    travel speeds, raw OCR plate detections, crop paths, and active alerts.
    """
    return await svc.investigate_vehicle(identity_id)


@router.get(
    "/investigate/alert/{alert_id}",
    response_model=AlertInvestigationResponse,
    summary="Retrieve detailed explainability dossier and evidence for a specific alert",
)
async def investigate_alert(
    alert_id: uuid.UUID,
    svc: DashboardServiceDep,
) -> AlertInvestigationResponse:
    """
    Returns the complete forensic evidence package used to trigger the alert,
    including vehicle profile, multi-camera trajectory, and raw signal confidences.
    """
    return await svc.investigate_alert(alert_id)


@router.get(
    "/analytics/summary",
    response_model=DashboardAnalyticsSummaryResponse,
    summary="Get consolidated traffic analytics summary for Executive Dashboard charts",
)
async def get_analytics_summary(
    svc: DashboardServiceDep,
) -> DashboardAnalyticsSummaryResponse:
    """
    Returns consolidated 24-hour volume trends, top congested corridors, frequent routes,
    and origin-destination flow matrices.
    """
    return await svc.get_analytics_summary()
