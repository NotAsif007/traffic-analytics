"""Alerts API endpoints — /api/v1/alerts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.alert import (
    AlertActionRequest,
    AlertDetailResponse,
    AlertFilters,
    AlertResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.alert import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_service(db: DBSession) -> AlertService:
    return AlertService(db)


AlertServiceDep = Annotated[AlertService, Depends(_alert_service)]


@router.get(
    "/",
    response_model=PaginatedResponse[AlertResponse],
    summary="List confidence-aware alerts with multi-criteria filtering",
)
async def list_alerts(
    svc: AlertServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    alert_type: Optional[str] = Query(None, description="BLACKLIST_MATCH | ROUTE_ANOMALY | TRAVEL_TIME_ANOMALY | CAMERA_OFFLINE"),
    severity: Optional[str] = Query(None, description="low | medium | high | critical"),
    status: Optional[str] = Query(None, description="NEW | ACKNOWLEDGED | RESOLVED | DISMISSED"),
    camera_id: Optional[uuid.UUID] = Query(None),
    vehicle_identity_id: Optional[uuid.UUID] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    created_after: Optional[datetime] = Query(None),
    created_before: Optional[datetime] = Query(None),
) -> PaginatedResponse[AlertResponse]:
    filters = AlertFilters(
        alert_type=alert_type,
        severity=severity,
        status=status,
        camera_id=camera_id,
        vehicle_identity_id=vehicle_identity_id,
        min_confidence=min_confidence,
        created_after=created_after,
        created_before=created_before,
    )
    return await svc.list_alerts(filters=filters, page=page, page_size=page_size)


@router.get(
    "/{alert_id}",
    response_model=AlertDetailResponse,
    summary="Retrieve alert details and complete explainability evidence",
)
async def get_alert(
    alert_id: uuid.UUID,
    svc: AlertServiceDep,
) -> AlertDetailResponse:
    return await svc.get_alert(alert_id)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an active alert",
)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    action: AlertActionRequest,
    svc: AlertServiceDep,
) -> AlertResponse:
    return await svc.acknowledge_alert(alert_id, action)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Mark an alert as resolved",
)
async def resolve_alert(
    alert_id: uuid.UUID,
    action: AlertActionRequest,
    svc: AlertServiceDep,
) -> AlertResponse:
    return await svc.resolve_alert(alert_id, action)


@router.post(
    "/{alert_id}/dismiss",
    response_model=AlertResponse,
    summary="Dismiss an alert as false positive or non-actionable",
)
async def dismiss_alert(
    alert_id: uuid.UUID,
    action: AlertActionRequest,
    svc: AlertServiceDep,
) -> AlertResponse:
    return await svc.dismiss_alert(alert_id, action)
