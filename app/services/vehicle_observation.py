"""VehicleObservation service — business logic for observation ingestion."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.vehicle_observation import VehicleObservation
from app.repositories.camera import CameraRepository
from app.repositories.vehicle_observation import VehicleObservationRepository
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_observation import (
    BulkObservationRejected,
    BulkObservationRequest,
    BulkObservationResponse,
    ObservationFilters,
    VehicleObservationCreate,
    VehicleObservationResponse,
    VehicleObservationStatusUpdate,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Mapping helper
# ---------------------------------------------------------------------------

from datetime import datetime, timezone

def _obs_to_response(obs: VehicleObservation) -> VehicleObservationResponse:
    """Convert ORM instance → response schema."""
    now = datetime.now(timezone.utc)
    return VehicleObservationResponse(
        id=obs.id or uuid.uuid4(),
        source=obs.source,
        source_observation_id=obs.source_observation_id,
        camera_id=obs.camera_id,
        observed_at=obs.observed_at,
        frame_number=obs.frame_number,
        vehicle_class=obs.vehicle_class,
        vehicle_color=obs.vehicle_color,
        bounding_box=obs.bounding_box,
        detection_confidence=float(obs.detection_confidence) if obs.detection_confidence else None,
        plate_text=obs.plate_text,
        plate_confidence=float(obs.plate_confidence) if obs.plate_confidence else None,
        plate_bbox=obs.plate_bbox,
        plate_region=obs.plate_region,
        frame_path=obs.frame_path,
        crop_path=obs.crop_path,
        plate_crop_path=obs.plate_crop_path,
        embedding_id=obs.embedding_id,
        embedding_model=obs.embedding_model,
        estimated_speed_kmh=float(obs.estimated_speed_kmh) if obs.estimated_speed_kmh else None,
        direction=obs.direction,
        lane=obs.lane,
        status=obs.status,
        rejection_reason=obs.rejection_reason,
        metadata=obs.metadata_,
        created_at=obs.created_at or now,
        updated_at=obs.updated_at or now,
    )


def _payload_to_orm(payload: VehicleObservationCreate) -> VehicleObservation:
    """Convert create schema → ORM instance (not yet persisted)."""
    return VehicleObservation(
        id=uuid.uuid4(),
        source=payload.source,
        source_observation_id=payload.source_observation_id,
        camera_id=payload.camera_id,
        observed_at=payload.observed_at,
        frame_number=payload.frame_number,
        vehicle_class=payload.vehicle_class,
        vehicle_color=payload.vehicle_color,
        bounding_box=payload.bounding_box.model_dump() if payload.bounding_box else None,
        detection_confidence=payload.detection_confidence,
        plate_text=payload.plate_text,
        plate_confidence=payload.plate_confidence,
        plate_bbox=payload.plate_bbox.model_dump() if payload.plate_bbox else None,
        plate_region=payload.plate_region,
        frame_path=payload.frame_path,
        crop_path=payload.crop_path,
        plate_crop_path=payload.plate_crop_path,
        embedding_id=payload.embedding_id,
        embedding_model=payload.embedding_model,
        estimated_speed_kmh=payload.estimated_speed_kmh,
        direction=payload.direction,
        lane=payload.lane,
        metadata_=payload.metadata_,
        status="detected",
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class VehicleObservationService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = VehicleObservationRepository(session)
        self._camera_repo = CameraRepository(session)

    # -----------------------------------------------------------------------
    # Single ingestion
    # -----------------------------------------------------------------------

    async def create_observation(
        self, payload: VehicleObservationCreate
    ) -> VehicleObservationResponse:
        """
        Ingest a single vehicle observation.

        Raises ConflictError if (source, source_observation_id) already exists.
        Raises NotFoundError if camera_id does not reference a known camera.
        """
        # Validate camera exists
        camera = await self._camera_repo.get_by_id(payload.camera_id)
        if not camera:
            raise NotFoundError("Camera", payload.camera_id)

        # Idempotency check
        existing = await self._repo.get_by_source(
            payload.source, payload.source_observation_id
        )
        if existing:
            raise ConflictError(
                "VehicleObservation",
                f"source='{payload.source}' source_observation_id='{payload.source_observation_id}' "
                "already exists",
            )

        obs = _payload_to_orm(payload)
        obs = await self._repo.create(obs)
        logger.info(
            "observation.created",
            obs_id=str(obs.id),
            source=obs.source,
            camera_id=str(obs.camera_id),
            plate=obs.plate_text,
        )
        return _obs_to_response(obs)

    # -----------------------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------------------

    async def get_observation(self, obs_id: uuid.UUID) -> VehicleObservationResponse:
        obs = await self._repo.get_by_id(obs_id)
        if not obs:
            raise NotFoundError("VehicleObservation", obs_id)
        return _obs_to_response(obs)

    async def list_observations(
        self,
        *,
        filters: ObservationFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[VehicleObservationResponse]:
        offset = (page - 1) * page_size
        records, total = await self._repo.list_observations(
            filters=filters, offset=offset, limit=page_size
        )
        items = [_obs_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    # -----------------------------------------------------------------------
    # Status update
    # -----------------------------------------------------------------------

    async def update_status(
        self,
        obs_id: uuid.UUID,
        payload: VehicleObservationStatusUpdate,
    ) -> VehicleObservationResponse:
        obs = await self._repo.get_by_id(obs_id)
        if not obs:
            raise NotFoundError("VehicleObservation", obs_id)

        updates: dict = {"status": payload.status}
        if payload.rejection_reason:
            updates["rejection_reason"] = payload.rejection_reason

        obs = await self._repo.update(obs, updates)
        return _obs_to_response(obs)

    # -----------------------------------------------------------------------
    # Bulk ingestion
    # -----------------------------------------------------------------------

    async def bulk_ingest(
        self, request: BulkObservationRequest
    ) -> BulkObservationResponse:
        """
        Ingest a batch of observations.

        Strategy:
        1. Pre-fetch all referenced camera IDs in one query.
        2. Pre-fetch all existing (source, source_observation_id) pairs in one query.
        3. For each item:
           a. Schema validation already done by FastAPI.
           b. Check camera existence from the pre-fetched set.
           c. Check duplicate from the pre-fetched set.
           d. If valid, create ORM instance and add to session.
        4. Flush once for all accepted records.

        This avoids N+1 queries against the database.
        """
        observations = request.observations

        # --- Pre-fetch cameras ---
        camera_ids = {obs.camera_id for obs in observations}
        from sqlalchemy import select as sa_select
        from app.models.camera import Camera
        cam_result = await self._repo._session.execute(
            sa_select(Camera).where(Camera.id.in_(camera_ids))
        )
        known_cameras: set[uuid.UUID] = {c.id for c in cam_result.scalars().all()}

        # --- Pre-fetch existing (source, source_observation_id) pairs ---
        source_pairs = [(obs.source, obs.source_observation_id) for obs in observations]
        existing_map = await self._repo.get_many_by_source(source_pairs)

        # --- Process each observation ---
        accepted: list[VehicleObservationResponse] = []
        rejected: list[BulkObservationRejected] = []
        orm_instances: list[VehicleObservation] = []

        # Track duplicates within the batch itself
        seen_in_batch: set[tuple[str, str]] = set()

        for idx, payload in enumerate(observations):
            errors: list[str] = []
            pair = (payload.source, payload.source_observation_id)

            # Camera existence
            if payload.camera_id not in known_cameras:
                errors.append(f"Camera {payload.camera_id} not found")

            # Existing record duplicate (pre-fetched)
            if pair in existing_map:
                errors.append(
                    f"Duplicate: source='{payload.source}' "
                    f"source_observation_id='{payload.source_observation_id}' already exists"
                )

            # Within-batch duplicate
            if pair in seen_in_batch:
                errors.append(
                    "Duplicate within this batch: "
                    f"source='{payload.source}' source_observation_id='{payload.source_observation_id}'"
                )

            if errors:
                rejected.append(
                    BulkObservationRejected(
                        index=idx,
                        source_observation_id=payload.source_observation_id,
                        reason="; ".join(errors),
                        errors=errors,
                    )
                )
                continue

            seen_in_batch.add(pair)
            orm_instances.append(_payload_to_orm(payload))

        # --- Persist all valid instances in a single flush ---
        for instance in orm_instances:
            self._repo._session.add(instance)

        if orm_instances:
            await self._repo._session.flush()
            for instance in orm_instances:
                await self._repo._session.refresh(instance)
            accepted = [_obs_to_response(obs) for obs in orm_instances]

        logger.info(
            "observation.bulk_ingest",
            total=len(observations),
            accepted=len(accepted),
            rejected=len(rejected),
        )

        return BulkObservationResponse(
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            accepted=accepted,
            rejected=rejected,
        )
