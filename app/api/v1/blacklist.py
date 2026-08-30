"""Blacklist/Watchlist API endpoints — /api/v1/blacklist."""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.alert import (
    BlacklistEntryCreate,
    BlacklistEntryResponse,
    BlacklistEntryUpdate,
    BlacklistFilters,
)
from app.schemas.common import PaginatedResponse
from app.services.alert import AlertService

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


def _alert_service(db: DBSession) -> AlertService:
    return AlertService(db)


AlertServiceDep = Annotated[AlertService, Depends(_alert_service)]


@router.post(
    "/",
    response_model=BlacklistEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a vehicle license plate to the active watchlist",
)
async def create_blacklist_entry(
    payload: BlacklistEntryCreate,
    svc: AlertServiceDep,
) -> BlacklistEntryResponse:
    return await svc.create_blacklist_entry(payload)


@router.get(
    "/",
    response_model=PaginatedResponse[BlacklistEntryResponse],
    summary="List watchlist entries with filters",
)
async def list_blacklist_entries(
    svc: AlertServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    plate_text: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> PaginatedResponse[BlacklistEntryResponse]:
    filters = BlacklistFilters(plate_text=plate_text, priority=priority, is_active=is_active)
    return await svc.list_blacklist_entries(filters=filters, page=page, page_size=page_size)


@router.get(
    "/{entry_id}",
    response_model=BlacklistEntryResponse,
    summary="Get a single watchlist entry",
)
async def get_blacklist_entry(
    entry_id: uuid.UUID,
    svc: AlertServiceDep,
) -> BlacklistEntryResponse:
    return await svc.get_blacklist_entry(entry_id)


@router.patch(
    "/{entry_id}",
    response_model=BlacklistEntryResponse,
    summary="Update a watchlist entry",
)
async def update_blacklist_entry(
    entry_id: uuid.UUID,
    payload: BlacklistEntryUpdate,
    svc: AlertServiceDep,
) -> BlacklistEntryResponse:
    return await svc.update_blacklist_entry(entry_id, payload)
