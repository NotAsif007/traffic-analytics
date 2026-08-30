"""Vehicle query endpoints — /api/v1/vehicles."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.trajectory import TrajectoryResponse
from app.services.trajectory import TrajectoryService

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _trajectory_service(db: DBSession) -> TrajectoryService:
    return TrajectoryService(db)


TrajectoryServiceDep = Annotated[TrajectoryService, Depends(_trajectory_service)]


@router.get(
    "/{identity_id}/trajectories",
    response_model=PaginatedResponse[TrajectoryResponse],
    summary="Retrieve all historical trajectories for a specific vehicle identity",
)
async def list_vehicle_trajectories(
    identity_id: uuid.UUID,
    svc: TrajectoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[TrajectoryResponse]:
    return await svc.list_vehicle_trajectories(
        vehicle_identity_id=identity_id, page=page, page_size=page_size
    )
