"""VehicleIdentity service — cross-camera association business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.association.contracts import AssociationDecision, SightingContext
from app.association.engine import AssociationEngine
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.vehicle_identity import VehicleIdentity, VehicleMatch
from app.models.vehicle_observation import VehicleObservation
from app.models.vehicle_track import VehicleTrack
from app.repositories.camera_connection import CameraConnectionRepository
from app.repositories.vehicle_identity import VehicleIdentityRepository, VehicleMatchRepository
from app.repositories.vehicle_observation import VehicleObservationRepository
from app.repositories.vehicle_track import VehicleTrackRepository
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_identity import (
    IdentityFilters,
    VehicleIdentityCreate,
    VehicleIdentityDetailResponse,
    VehicleIdentityResponse,
    VehicleMatchResponse,
)

logger = get_logger(__name__)


def _identity_to_response(ident: VehicleIdentity) -> VehicleIdentityResponse:
    return VehicleIdentityResponse(
        id=ident.id,
        identity_code=ident.identity_code,
        primary_plate=ident.primary_plate,
        plate_confidence=float(ident.plate_confidence) if ident.plate_confidence else None,
        vehicle_class=ident.vehicle_class,
        vehicle_color=ident.vehicle_color,
        vehicle_make=ident.vehicle_make,
        vehicle_model=ident.vehicle_model,
        status=ident.status,
        first_seen_at=ident.first_seen_at,
        last_seen_at=ident.last_seen_at,
        total_sightings=ident.total_sightings,
        confidence=float(ident.confidence),
        reid_embedding_id=ident.reid_embedding_id,
        notes=ident.notes,
        metadata=ident.metadata_,
        created_at=ident.created_at,
        updated_at=ident.updated_at,
    )


def _match_to_response(m: VehicleMatch) -> VehicleMatchResponse:
    return VehicleMatchResponse(
        id=m.id,
        vehicle_identity_id=m.vehicle_identity_id,
        source_observation_id=m.source_observation_id,
        source_track_id=m.source_track_id,
        source_camera_id=m.source_camera_id,
        target_observation_id=m.target_observation_id,
        target_track_id=m.target_track_id,
        target_camera_id=m.target_camera_id,
        match_score=float(m.match_score),
        status=m.status,
        signals=m.signals,
        reasoning=m.reasoning,
        rejection_reason=m.rejection_reason,
        metadata=m.metadata_,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class VehicleIdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self._identity_repo = VehicleIdentityRepository(session)
        self._match_repo = VehicleMatchRepository(session)
        self._obs_repo = VehicleObservationRepository(session)
        self._track_repo = VehicleTrackRepository(session)
        self._conn_repo = CameraConnectionRepository(session)
        self._engine = AssociationEngine()

    async def create_identity(self, payload: VehicleIdentityCreate) -> VehicleIdentityResponse:
        ident = VehicleIdentity(
            id=uuid.uuid4(),
            identity_code=payload.identity_code,
            primary_plate=payload.primary_plate,
            plate_confidence=payload.plate_confidence,
            vehicle_class=payload.vehicle_class,
            vehicle_color=payload.vehicle_color,
            vehicle_make=payload.vehicle_make,
            vehicle_model=payload.vehicle_model,
            status=payload.status,
            first_seen_at=payload.first_seen_at,
            last_seen_at=payload.last_seen_at,
            total_sightings=payload.total_sightings,
            confidence=payload.confidence,
            reid_embedding_id=payload.reid_embedding_id,
            notes=payload.notes,
            metadata_=payload.metadata_,
        )
        ident = await self._identity_repo.create(ident)
        return _identity_to_response(ident)

    async def get_identity(self, identity_id: uuid.UUID) -> VehicleIdentityResponse:
        ident = await self._identity_repo.get_by_id(identity_id)
        if not ident:
            raise NotFoundError("VehicleIdentity", identity_id)
        return _identity_to_response(ident)

    async def get_identity_detail(self, identity_id: uuid.UUID) -> VehicleIdentityDetailResponse:
        ident = await self._identity_repo.get_with_matches(identity_id)
        if not ident:
            raise NotFoundError("VehicleIdentity", identity_id)

        matches = [_match_to_response(m) for m in (ident.matches or [])]
        base_resp = _identity_to_response(ident)
        return VehicleIdentityDetailResponse(
            **base_resp.model_dump(),
            matches=matches,
        )

    async def list_identities(
        self,
        *,
        filters: IdentityFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[VehicleIdentityResponse]:
        offset = (page - 1) * page_size
        records, total = await self._identity_repo.list_identities(
            filters=filters, offset=offset, limit=page_size
        )
        items = [_identity_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def list_matches(
        self,
        *,
        identity_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[VehicleMatchResponse]:
        offset = (page - 1) * page_size
        records, total = await self._match_repo.list_matches(
            identity_id=identity_id, status=status, offset=offset, limit=page_size
        )
        items = [_match_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def associate_observation(
        self,
        observation_id: uuid.UUID,
        search_window_minutes: int = 60,
    ) -> tuple[VehicleIdentityResponse, Optional[VehicleMatchResponse]]:
        """
        Cross-camera associate a newly ingested vehicle observation.

        1. Evaluates candidate identities within the search window.
        2. If a plausible match is accepted or reviewed: links observation to existing identity.
        3. If no match: creates a new VehicleIdentity hypothesis.
        """
        obs = await self._obs_repo.get_by_id(observation_id)
        if not obs:
            raise NotFoundError("VehicleObservation", observation_id)

        target_context = SightingContext(
            sighting_id=obs.id,
            is_track=False,
            camera_id=obs.camera_id,
            timestamp=obs.observed_at,
            plate_text=obs.plate_text,
            plate_confidence=float(obs.plate_confidence) if obs.plate_confidence else None,
            vehicle_class=obs.vehicle_class,
            vehicle_color=obs.vehicle_color,
            direction=obs.direction,
            speed_kmh=float(obs.estimated_speed_kmh) if obs.estimated_speed_kmh else None,
            embedding_id=obs.embedding_id,
        )

        window_start = obs.observed_at - timedelta(minutes=search_window_minutes)
        candidates = await self._identity_repo.find_recent_identities(window_start)

        best_decision: Optional[AssociationDecision] = None
        best_candidate: Optional[VehicleIdentity] = None
        best_source_obs_id: Optional[uuid.UUID] = None
        best_source_cam_id: Optional[uuid.UUID] = None

        for ident in candidates:
            # Check camera connection
            # Find the most recent match/sighting in this identity to compare against
            # In simple terms, use identity's last known state
            source_context = SightingContext(
                sighting_id=ident.id,
                is_track=False,
                camera_id=ident.matches[-1].target_camera_id if ident.matches else obs.camera_id,
                timestamp=ident.last_seen_at,
                plate_text=ident.primary_plate,
                plate_confidence=float(ident.plate_confidence) if ident.plate_confidence else None,
                vehicle_class=ident.vehicle_class,
                vehicle_color=ident.vehicle_color,
                embedding_id=ident.reid_embedding_id,
            )

            # Look up connection between cameras
            conn = await self._conn_repo.get_by_camera_pair(
                source_context.camera_id, target_context.camera_id
            )

            decision = self._engine.evaluate_pair(source_context, target_context, conn)

            if decision.is_accepted or decision.status == "needs_review":
                if not best_decision or decision.match_score > best_decision.match_score:
                    best_decision = decision
                    best_candidate = ident
                    best_source_cam_id = source_context.camera_id
                    best_source_obs_id = (
                        ident.matches[-1].target_observation_id if ident.matches else None
                    )

        # Apply match or create new hypothesis
        if best_candidate and best_decision:
            # Update existing identity
            best_candidate.total_sightings += 1
            best_candidate.last_seen_at = max(best_candidate.last_seen_at, obs.observed_at)

            # Update primary plate if this sighting has higher OCR confidence
            if (
                obs.plate_text
                and (obs.plate_confidence or 0.0) > (best_candidate.plate_confidence or 0.0)
            ):
                best_candidate.primary_plate = obs.plate_text
                best_candidate.plate_confidence = obs.plate_confidence

            # Recalculate identity confidence
            best_candidate.confidence = round(
                (float(best_candidate.confidence) + best_decision.match_score) / 2.0, 4
            )

            match_record = VehicleMatch(
                id=uuid.uuid4(),
                vehicle_identity_id=best_candidate.id,
                source_observation_id=best_source_obs_id,
                source_camera_id=best_source_cam_id or obs.camera_id,
                target_observation_id=obs.id,
                target_camera_id=obs.camera_id,
                match_score=best_decision.match_score,
                status=best_decision.status,
                signals=best_decision.signals.model_dump(),
                reasoning=best_decision.reasoning,
            )
            self._identity_repo._session.add(match_record)
            await self._identity_repo._session.flush()

            # Mark observation as associated
            obs.status = "associated"
            await self._identity_repo._session.flush()
            await self._identity_repo._session.refresh(best_candidate)
            await self._identity_repo._session.refresh(match_record)

            logger.info(
                "association.matched",
                identity_code=best_candidate.identity_code,
                score=best_decision.match_score,
                status=best_decision.status,
            )
            return _identity_to_response(best_candidate), _match_to_response(match_record)

        # Otherwise create a new VehicleIdentity hypothesis
        code_tag = f"VID-{obs.observed_at.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        new_ident = VehicleIdentity(
            id=uuid.uuid4(),
            identity_code=code_tag,
            primary_plate=obs.plate_text,
            plate_confidence=obs.plate_confidence,
            vehicle_class=obs.vehicle_class,
            vehicle_color=obs.vehicle_color,
            status="candidate",
            first_seen_at=obs.observed_at,
            last_seen_at=obs.observed_at,
            total_sightings=1,
            confidence=float(obs.detection_confidence or 0.8),
            reid_embedding_id=obs.embedding_id,
        )
        self._identity_repo._session.add(new_ident)
        obs.status = "associated"
        await self._identity_repo._session.flush()
        await self._identity_repo._session.refresh(new_ident)

        logger.info("association.new_identity_created", identity_code=new_ident.identity_code)
        return _identity_to_response(new_ident), None
