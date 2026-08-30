"""Cross-camera association match endpoints — /api/v1/matches."""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_identity import VehicleMatchResponse
from app.services.vehicle_identity import VehicleIdentityService

router = APIRouter(prefix="/matches", tags=["matches"])


def _identity_service(db: DBSession) -> VehicleIdentityService:
    return VehicleIdentityService(db)


IdentityServiceDep = Annotated[VehicleIdentityService, Depends(_identity_service)]


@router.get(
    "/",
    response_model=PaginatedResponse[VehicleMatchResponse],
    summary="List cross-camera association matches with explainability data",
)
async def list_matches(
    svc: IdentityServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity_id: Optional[uuid.UUID] = Query(None, description="Filter by vehicle identity UUID"),
    status: Optional[str] = Query(None, description="candidate | accepted | rejected | needs_review"),
) -> PaginatedResponse[VehicleMatchResponse]:
    return await svc.list_matches(
        identity_id=identity_id, status=status, page=page, page_size=page_size
    )
