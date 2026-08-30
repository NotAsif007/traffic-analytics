"""Road CRUD endpoints — /api/v1/roads."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.schemas.common import PaginatedResponse
from app.schemas.road import RoadCreate, RoadResponse, RoadUpdate
from app.services.road import RoadService

router = APIRouter(prefix="/roads", tags=["roads"])


def _road_service(db: DBSession) -> RoadService:
    return RoadService(db)


RoadServiceDep = Annotated[RoadService, Depends(_road_service)]


@router.post("/", response_model=RoadResponse, status_code=status.HTTP_201_CREATED)
async def create_road(payload: RoadCreate, svc: RoadServiceDep) -> RoadResponse:
    """Create a new road segment."""
    return await svc.create_road(payload)


@router.get("/", response_model=PaginatedResponse[RoadResponse])
async def list_roads(
    svc: RoadServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    road_type: str | None = Query(None, description="Filter by road type"),
    direction: str | None = Query(
        None, description="Filter by direction (one_way_forward, one_way_reverse, two_way)"
    ),
) -> PaginatedResponse[RoadResponse]:
    """List all roads with optional filtering and pagination."""
    return await svc.list_roads(
        page=page, page_size=page_size, road_type=road_type, direction=direction
    )


@router.get("/near", response_model=list[RoadResponse])
async def roads_near_point(
    svc: RoadServiceDep,
    longitude: float = Query(..., ge=-180.0, le=180.0, description="WGS-84 longitude"),
    latitude: float = Query(..., ge=-90.0, le=90.0, description="WGS-84 latitude"),
    radius_m: float = Query(500.0, ge=1.0, le=10000.0, description="Search radius in metres"),
) -> list[RoadResponse]:
    """Find roads within a given radius of a GPS coordinate."""
    return await svc.find_roads_near(longitude, latitude, radius_m)


@router.get("/{road_id}", response_model=RoadResponse)
async def get_road(road_id: uuid.UUID, svc: RoadServiceDep) -> RoadResponse:
    """Retrieve a road by ID."""
    return await svc.get_road(road_id)


@router.patch("/{road_id}", response_model=RoadResponse)
async def update_road(road_id: uuid.UUID, payload: RoadUpdate, svc: RoadServiceDep) -> RoadResponse:
    """Partially update a road."""
    return await svc.update_road(road_id, payload)


@router.delete("/{road_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_road(road_id: uuid.UUID, svc: RoadServiceDep) -> None:
    """Delete a road (cameras on this road will have road_id set to NULL)."""
    await svc.delete_road(road_id)
