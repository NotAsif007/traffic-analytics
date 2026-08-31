"""Vehicle observation endpoints — /api/v1/observations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DBSession
from app.api.v1.events import get_event_bus
from app.events.contracts import DomainEvent, EventType
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_observation import (
    BulkObservationRequest,
    BulkObservationResponse,
    ObservationFilters,
    VehicleObservationCreate,
    VehicleObservationResponse,
    VehicleObservationStatusUpdate,
)
from app.services.vehicle_observation import VehicleObservationService

router = APIRouter(prefix="/observations", tags=["observations"])


def _obs_service(db: DBSession) -> VehicleObservationService:
    return VehicleObservationService(db)


ObsServiceDep = Annotated[VehicleObservationService, Depends(_obs_service)]


# ---------------------------------------------------------------------------
# Single observation endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=VehicleObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single vehicle observation",
    description=(
        "Accepts a single normalized observation from any AI/ANPR pipeline. "
        "Returns 409 if the (source, source_observation_id) pair already exists."
    ),
)
async def create_observation(
    payload: VehicleObservationCreate,
    svc: ObsServiceDep,
) -> VehicleObservationResponse:
    obs = await svc.create_observation(payload)
    bus = get_event_bus()
    await bus.publish(
        DomainEvent(
            event_type=EventType.VEHICLE_OBSERVED.value,
            source=payload.source,
            payload=obs.model_dump(mode="json"),
            idempotency_key=f"obs-{payload.source}-{payload.source_observation_id}",
        )
    )
    return obs


@router.get(
    "/",
    response_model=PaginatedResponse[VehicleObservationResponse],
    summary="List observations with filtering",
)
async def list_observations(
    svc: ObsServiceDep,
    # Pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    # Filters
    camera_id: uuid.UUID | None = Query(None, description="Filter by camera UUID"),
    observed_after: datetime | None = Query(
        None, description="Filter observations after this timestamp (ISO 8601 with tz)"
    ),
    observed_before: datetime | None = Query(
        None, description="Filter observations before this timestamp (ISO 8601 with tz)"
    ),
    plate_text: str | None = Query(
        None, max_length=20, description="Partial case-insensitive plate text match"
    ),
    vehicle_class: str | None = Query(None, description="Exact vehicle class filter"),
    min_detection_confidence: float | None = Query(
        None, ge=0.0, le=1.0, description="Minimum detection confidence threshold"
    ),
    min_plate_confidence: float | None = Query(
        None, ge=0.0, le=1.0, description="Minimum plate OCR confidence threshold"
    ),
    status: str | None = Query(
        None,
        description="Filter by lifecycle status: detected|processed|validated|associated|rejected",
    ),
    source: str | None = Query(None, description="Filter by pipeline source identifier"),
) -> PaginatedResponse[VehicleObservationResponse]:
    filters = ObservationFilters(
        camera_id=camera_id,
        observed_after=observed_after,
        observed_before=observed_before,
        plate_text=plate_text,
        vehicle_class=vehicle_class,
        min_detection_confidence=min_detection_confidence,
        min_plate_confidence=min_plate_confidence,
        status=status,
        source=source,
    )
    return await svc.list_observations(filters=filters, page=page, page_size=page_size)


@router.get(
    "/{observation_id}",
    response_model=VehicleObservationResponse,
    summary="Retrieve a single observation",
)
async def get_observation(
    observation_id: uuid.UUID,
    svc: ObsServiceDep,
) -> VehicleObservationResponse:
    return await svc.get_observation(observation_id)


@router.patch(
    "/{observation_id}/status",
    response_model=VehicleObservationResponse,
    summary="Update observation lifecycle status",
    description=(
        "Transition an observation through its lifecycle. "
        "When setting status to 'rejected', a rejection_reason is required."
    ),
)
async def update_observation_status(
    observation_id: uuid.UUID,
    payload: VehicleObservationStatusUpdate,
    svc: ObsServiceDep,
) -> VehicleObservationResponse:
    return await svc.update_status(observation_id, payload)


# ---------------------------------------------------------------------------
# Bulk ingestion
# ---------------------------------------------------------------------------


@router.post(
    "/bulk",
    response_model=BulkObservationResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk ingest vehicle observations",
    description=(
        "Ingest up to 500 observations in a single request. "
        "Each observation is validated independently. "
        "The response reports which observations were accepted and which were rejected, "
        "with per-item error details. "
        "The entire accepted set is committed atomically — "
        "rejected items do not affect accepted ones."
    ),
)
async def bulk_ingest_observations(
    request: BulkObservationRequest,
    svc: ObsServiceDep,
) -> BulkObservationResponse:
    res = await svc.bulk_ingest(request)
    bus = get_event_bus()
    for acc in res.accepted:
        await bus.publish(
            DomainEvent(
                event_type=EventType.VEHICLE_OBSERVED.value,
                source=acc.source,
                payload=acc.model_dump(mode="json"),
                idempotency_key=f"obs-{acc.source}-{acc.source_observation_id}",
            )
        )
    return res
