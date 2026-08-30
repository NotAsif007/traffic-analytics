"""VehicleTrack service — single-camera tracking business logic."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.vehicle_track import TrackPoint, VehicleTrack
from app.repositories.camera import CameraRepository
from app.repositories.vehicle_track import VehicleTrackRepository
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_observation import BoundingBox
from app.schemas.vehicle_track import (
    TrackFilters,
    TrackPointResponse,
    VehicleTrackCreate,
    VehicleTrackDetailResponse,
    VehicleTrackResponse,
)
from app.tracking.contracts import TrackState

logger = get_logger(__name__)


def _track_to_response(track: VehicleTrack) -> VehicleTrackResponse:
    return VehicleTrackResponse(
        id=track.id,
        track_id=track.track_id,
        camera_id=track.camera_id,
        start_time=track.start_time,
        end_time=track.end_time,
        status=track.status,
        confidence=float(track.confidence),
        vehicle_class=track.vehicle_class,
        vehicle_color=track.vehicle_color,
        best_plate_text=track.best_plate_text,
        best_plate_confidence=float(track.best_plate_confidence)
        if track.best_plate_confidence
        else None,
        points_count=track.points_count,
        notes=track.notes,
        metadata=track.metadata_,
        created_at=track.created_at,
        updated_at=track.updated_at,
    )


def _point_to_response(point: TrackPoint) -> TrackPointResponse:
    bbox = None
    if point.bounding_box:
        bbox = BoundingBox(**point.bounding_box)

    return TrackPointResponse(
        id=point.id,
        track_id=point.track_id,
        camera_id=point.camera_id,
        observation_id=point.observation_id,
        timestamp=point.timestamp,
        frame_number=point.frame_number,
        bounding_box=bbox,
        confidence=float(point.confidence),
        estimated_speed_kmh=float(point.estimated_speed_kmh) if point.estimated_speed_kmh else None,
        plate_text=point.plate_text,
        plate_confidence=float(point.plate_confidence) if point.plate_confidence else None,
        metadata=point.metadata_,
        created_at=point.created_at,
        updated_at=point.updated_at,
    )


class VehicleTrackService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = VehicleTrackRepository(session)
        self._camera_repo = CameraRepository(session)

    async def create_track(self, payload: VehicleTrackCreate) -> VehicleTrackResponse:
        camera = await self._camera_repo.get_by_id(payload.camera_id)
        if not camera:
            raise NotFoundError("Camera", payload.camera_id)

        track = VehicleTrack(
            id=uuid.uuid4(),
            track_id=payload.track_id,
            camera_id=payload.camera_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status=payload.status,
            confidence=payload.confidence,
            vehicle_class=payload.vehicle_class,
            vehicle_color=payload.vehicle_color,
            best_plate_text=payload.best_plate_text,
            best_plate_confidence=payload.best_plate_confidence,
            points_count=payload.points_count,
            notes=payload.notes,
            metadata_=payload.metadata_,
        )
        track = await self._repo.create(track)
        logger.info("vehicle_track.created", track_id=track.track_id, id=str(track.id))
        return _track_to_response(track)

    async def get_track(self, track_id: uuid.UUID) -> VehicleTrackResponse:
        track = await self._repo.get_by_id(track_id)
        if not track:
            raise NotFoundError("VehicleTrack", track_id)
        return _track_to_response(track)

    async def get_track_detail(self, track_id: uuid.UUID) -> VehicleTrackDetailResponse:
        track = await self._repo.get_with_points(track_id)
        if not track:
            raise NotFoundError("VehicleTrack", track_id)

        points = [_point_to_response(p) for p in (track.track_points or [])]
        base_resp = _track_to_response(track)
        return VehicleTrackDetailResponse(
            **base_resp.model_dump(),
            track_points=points,
        )

    async def list_tracks(
        self,
        *,
        filters: TrackFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[VehicleTrackResponse]:
        offset = (page - 1) * page_size
        records, total = await self._repo.list_tracks(
            filters=filters, offset=offset, limit=page_size
        )
        items = [_track_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def list_camera_tracks(
        self,
        camera_id: uuid.UUID,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[VehicleTrackResponse]:
        camera = await self._camera_repo.get_by_id(camera_id)
        if not camera:
            raise NotFoundError("Camera", camera_id)

        filters = TrackFilters(camera_id=camera_id, status=status)
        return await self.list_tracks(filters=filters, page=page, page_size=page_size)

    async def get_track_observations(self, track_id: uuid.UUID) -> list[TrackPointResponse]:
        track = await self._repo.get_by_id(track_id)
        if not track:
            raise NotFoundError("VehicleTrack", track_id)

        points = await self._repo.get_track_observations(track_id)
        return [_point_to_response(p) for p in points]

    async def persist_track_state(self, state: TrackState) -> VehicleTrackResponse:
        """Persist a live TrackState from the tracker engine into the database."""
        track = VehicleTrack(
            id=uuid.uuid4(),
            track_id=state.track_id,
            camera_id=state.camera_id,
            start_time=state.start_time,
            end_time=state.last_seen,
            status=state.status,
            confidence=state.confidence,
            vehicle_class=state.vehicle_class,
            vehicle_color=state.vehicle_color,
            best_plate_text=state.best_plate_text,
            best_plate_confidence=state.best_plate_confidence,
            points_count=len(state.points),
            metadata_=state.metadata_,
        )
        self._repo._session.add(track)
        await self._repo._session.flush()

        for pt in state.points:
            point_orm = TrackPoint(
                id=uuid.uuid4(),
                track_id=track.id,
                camera_id=state.camera_id,
                observation_id=pt.observation_id,
                timestamp=pt.timestamp,
                frame_number=pt.frame_number,
                bounding_box=pt.bbox.model_dump() if pt.bbox else None,
                confidence=pt.confidence,
                estimated_speed_kmh=pt.estimated_speed_kmh,
                plate_text=pt.plate_text,
                plate_confidence=pt.plate_confidence,
            )
            self._repo._session.add(point_orm)

        await self._repo._session.flush()
        await self._repo._session.refresh(track)
        return _track_to_response(track)
