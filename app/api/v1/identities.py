"""Cross-camera vehicle identity endpoints — /api/v1/identities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_identity import (
    AssociateSightingsRequest,
    IdentityFilters,
    VehicleIdentityCreate,
    VehicleIdentityDetailResponse,
    VehicleIdentityResponse,
    VehicleMatchResponse,
)
from app.services.vehicle_identity import VehicleIdentityService

router = APIRouter(prefix="/identities", tags=["identities"])


def _identity_service(db: DBSession) -> VehicleIdentityService:
    return VehicleIdentityService(db)


IdentityServiceDep = Annotated[VehicleIdentityService, Depends(_identity_service)]


@router.post(
    "/",
    response_model=VehicleIdentityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a vehicle identity hypothesis directly",
)
async def create_identity(
    payload: VehicleIdentityCreate,
    svc: IdentityServiceDep,
) -> VehicleIdentityResponse:
    return await svc.create_identity(payload)


@router.get(
    "/",
    response_model=PaginatedResponse[VehicleIdentityResponse],
    summary="List cross-camera vehicle identities with filters",
)
async def list_identities(
    svc: IdentityServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: Optional[str] = Query(None, description="candidate | accepted | rejected | needs_review"),
    primary_plate: Optional[str] = Query(None, description="Partial plate text match"),
    vehicle_class: Optional[str] = Query(None, description="Filter by vehicle class"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    seen_after: Optional[datetime] = Query(None, description="Seen after timestamp"),
    seen_before: Optional[datetime] = Query(None, description="Seen before timestamp"),
) -> PaginatedResponse[VehicleIdentityResponse]:
    filters = IdentityFilters(
        status=status,
        primary_plate=primary_plate,
        vehicle_class=vehicle_class,
        min_confidence=min_confidence,
        seen_after=seen_after,
        seen_before=seen_before,
    )
    return await svc.list_identities(filters=filters, page=page, page_size=page_size)


@router.get(
    "/{identity_id}",
    response_model=VehicleIdentityDetailResponse,
    summary="Retrieve a vehicle identity and all its cross-camera association events",
)
async def get_identity(
    identity_id: uuid.UUID,
    svc: IdentityServiceDep,
) -> VehicleIdentityDetailResponse:
    return await svc.get_identity_detail(identity_id)


@router.post(
    "/associate",
    summary="Trigger cross-camera vehicle association for an observation",
    description="Evaluates candidate identities against spatio-temporal and appearance signals.",
)
async def associate_observation(
    request: AssociateSightingsRequest,
    svc: IdentityServiceDep,
) -> dict[str, Any]:
    if not request.observation_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="observation_id is required")

    identity, match = await svc.associate_observation(
        observation_id=request.observation_id,
        search_window_minutes=request.max_search_window_minutes,
    )
    return {
        "identity": identity,
        "match": match,
    }
