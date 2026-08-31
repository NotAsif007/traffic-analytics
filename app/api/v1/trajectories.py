"""City-wide vehicle trajectory endpoints — /api/v1/trajectories."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.trajectory import (
    TrajectoryDetailResponse,
    TrajectoryFilters,
    TrajectoryPredictionResponse,
    TrajectoryResponse,
    TrajectoryTimelineResponse,
)
from app.services.trajectory import TrajectoryService

router = APIRouter(prefix="/trajectories", tags=["trajectories"])


def _trajectory_service(db: DBSession) -> TrajectoryService:
    return TrajectoryService(db)


TrajectoryServiceDep = Annotated[TrajectoryService, Depends(_trajectory_service)]


@router.get(
    "/",
    response_model=PaginatedResponse[TrajectoryResponse],
    summary="List vehicle trajectories with multi-criteria filtering",
)
async def list_trajectories(
    svc: TrajectoryServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vehicle_identity_id: uuid.UUID | None = Query(
        None, description="Filter by vehicle identity UUID"
    ),
    camera_id: uuid.UUID | None = Query(
        None, description="Filter trajectories passing through camera"
    ),
    status: str | None = Query(None, description="active | completed | terminated"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    start_after: datetime | None = Query(
        None, description="Filter trajectories started after timestamp"
    ),
    end_before: datetime | None = Query(
        None, description="Filter trajectories ended before timestamp"
    ),
) -> PaginatedResponse[TrajectoryResponse]:
    filters = TrajectoryFilters(
        vehicle_identity_id=vehicle_identity_id,
        camera_id=camera_id,
        status=status,
        min_confidence=min_confidence,
        start_after=start_after,
        end_before=end_before,
    )
    return await svc.list_trajectories(filters=filters, page=page, page_size=page_size)


@router.get(
    "/{trajectory_id}",
    response_model=TrajectoryDetailResponse,
    summary="Retrieve full trajectory details including all waypoints",
)
async def get_trajectory(
    trajectory_id: uuid.UUID,
    svc: TrajectoryServiceDep,
) -> TrajectoryDetailResponse:
    return await svc.get_trajectory_detail(trajectory_id)


@router.get(
    "/{trajectory_id}/timeline",
    response_model=TrajectoryTimelineResponse,
    summary="Retrieve a structured chronological journey timeline for a trajectory",
)
async def get_trajectory_timeline(
    trajectory_id: uuid.UUID,
    svc: TrajectoryServiceDep,
) -> TrajectoryTimelineResponse:
    return await svc.get_timeline(trajectory_id)


@router.get(
    "/{trajectory_id}/prediction",
    response_model=TrajectoryPredictionResponse,
    summary="Forecast future vehicle trajectory, next camera intercepts, and ETAs",
)
async def get_trajectory_prediction(
    trajectory_id: uuid.UUID,
    svc: TrajectoryServiceDep,
) -> TrajectoryPredictionResponse:
    return await svc.predict_next_locations(trajectory_id)

