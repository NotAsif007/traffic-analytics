"""Alert and Anomaly detection service — explainable threat and traffic alerting."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.anpr.matcher import PlateMatcher
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.alert import Alert, BlacklistEntry
from app.models.camera import Camera
from app.models.camera_connection import CameraConnection
from app.models.trajectory import Trajectory, TrajectoryPoint
from app.models.vehicle_observation import VehicleObservation
from app.repositories.alert import AlertRepository, BlacklistRepository
from app.repositories.camera import CameraRepository
from app.schemas.alert import (
    AlertActionRequest,
    AlertCreate,
    AlertDetailResponse,
    AlertFilters,
    AlertResponse,
    BlacklistEntryCreate,
    BlacklistEntryResponse,
    BlacklistEntryUpdate,
    BlacklistFilters,
)
from app.schemas.common import PaginatedResponse

logger = get_logger(__name__)


def _alert_to_response(a: Alert) -> AlertResponse:
    cam_name = a.camera.name if a.camera else None
    return AlertResponse(
        id=a.id,
        alert_code=a.alert_code,
        alert_type=a.alert_type,
        severity=a.severity,
        status=a.status,
        confidence=float(a.confidence),
        title=a.title,
        description=a.description,
        camera_id=a.camera_id,
        camera_name=cam_name,
        vehicle_identity_id=a.vehicle_identity_id,
        trajectory_id=a.trajectory_id,
        observation_id=a.observation_id,
        blacklist_entry_id=a.blacklist_entry_id,
        evidence=a.evidence or {},
        acknowledged_at=a.acknowledged_at,
        acknowledged_by=a.acknowledged_by,
        resolved_at=a.resolved_at,
        resolved_by=a.resolved_by,
        dismissed_at=a.dismissed_at,
        dismissed_by=a.dismissed_by,
        resolution_notes=a.resolution_notes,
        metadata=a.metadata_,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _blacklist_to_response(b: BlacklistEntry) -> BlacklistEntryResponse:
    return BlacklistEntryResponse(
        id=b.id,
        plate_text=b.plate_text,
        reason=b.reason,
        priority=b.priority,
        is_active=b.is_active,
        valid_from=b.valid_from,
        valid_until=b.valid_until,
        notes=b.notes,
        metadata=b.metadata_,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._alert_repo = AlertRepository(session)
        self._blacklist_repo = BlacklistRepository(session)
        self._camera_repo = CameraRepository(session)
        self._plate_matcher = PlateMatcher()

    # -----------------------------------------------------------------------
    # Blacklist Management
    # -----------------------------------------------------------------------

    async def create_blacklist_entry(
        self, payload: BlacklistEntryCreate
    ) -> BlacklistEntryResponse:
        entry = BlacklistEntry(
            id=uuid.uuid4(),
            plate_text=payload.plate_text.upper().replace(" ", ""),
            reason=payload.reason,
            priority=payload.priority,
            is_active=payload.is_active,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
            notes=payload.notes,
            metadata_=payload.metadata_,
        )
        entry = await self._blacklist_repo.create(entry)
        return _blacklist_to_response(entry)

    async def get_blacklist_entry(self, entry_id: uuid.UUID) -> BlacklistEntryResponse:
        entry = await self._blacklist_repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError("BlacklistEntry", entry_id)
        return _blacklist_to_response(entry)

    async def update_blacklist_entry(
        self, entry_id: uuid.UUID, payload: BlacklistEntryUpdate
    ) -> BlacklistEntryResponse:
        entry = await self._blacklist_repo.get_by_id(entry_id)
        if not entry:
            raise NotFoundError("BlacklistEntry", entry_id)

        if payload.reason is not None:
            entry.reason = payload.reason
        if payload.priority is not None:
            entry.priority = payload.priority
        if payload.is_active is not None:
            entry.is_active = payload.is_active
        if payload.valid_from is not None:
            entry.valid_from = payload.valid_from
        if payload.valid_until is not None:
            entry.valid_until = payload.valid_until
        if payload.notes is not None:
            entry.notes = payload.notes
        if payload.metadata_ is not None:
            entry.metadata_ = payload.metadata_

        await self._session.flush()
        await self._session.refresh(entry)
        return _blacklist_to_response(entry)

    async def list_blacklist_entries(
        self,
        *,
        filters: BlacklistFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[BlacklistEntryResponse]:
        offset = (page - 1) * page_size
        records, total = await self._blacklist_repo.list_entries(
            filters=filters, offset=offset, limit=page_size
        )
        items = [_blacklist_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    # -----------------------------------------------------------------------
    # Alert Queries & Lifecycle Transitions
    # -----------------------------------------------------------------------

    async def get_alert(self, alert_id: uuid.UUID) -> AlertDetailResponse:
        alert = await self._alert_repo.get_with_relations(alert_id)
        if not alert:
            raise NotFoundError("Alert", alert_id)
        return AlertDetailResponse(**_alert_to_response(alert).model_dump())

    async def list_alerts(
        self,
        *,
        filters: AlertFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[AlertResponse]:
        offset = (page - 1) * page_size
        records, total = await self._alert_repo.list_alerts(
            filters=filters, offset=offset, limit=page_size
        )
        items = [_alert_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def acknowledge_alert(
        self, alert_id: uuid.UUID, action: AlertActionRequest
    ) -> AlertResponse:
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert", alert_id)

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = action.action_by
        if action.notes:
            alert.resolution_notes = action.notes

        await self._session.flush()
        await self._session.refresh(alert)
        return _alert_to_response(alert)

    async def resolve_alert(
        self, alert_id: uuid.UUID, action: AlertActionRequest
    ) -> AlertResponse:
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert", alert_id)

        alert.status = "RESOLVED"
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = action.action_by
        if action.notes:
            alert.resolution_notes = action.notes

        await self._session.flush()
        await self._session.refresh(alert)
        return _alert_to_response(alert)

    async def dismiss_alert(
        self, alert_id: uuid.UUID, action: AlertActionRequest
    ) -> AlertResponse:
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise NotFoundError("Alert", alert_id)

        alert.status = "DISMISSED"
        alert.dismissed_at = datetime.now(timezone.utc)
        alert.dismissed_by = action.action_by
        if action.notes:
            alert.resolution_notes = action.notes

        await self._session.flush()
        await self._session.refresh(alert)
        return _alert_to_response(alert)

    # -----------------------------------------------------------------------
    # Automated Alert Generators (Confidence & Evidence Preserving)
    # -----------------------------------------------------------------------

    async def check_observation_blacklist(
        self, obs: VehicleObservation
    ) -> Optional[Alert]:
        """
        Check if an observation matches any active watchlist/blacklist entry.
        Generates an explainable BLACKLIST_MATCH alert preserving all evidence.
        """
        if not obs.plate_text:
            return None

        active_entries = await self._blacklist_repo.find_active_entries()
        for entry in active_entries:
            comp = self._plate_matcher.compare(obs.plate_text, entry.plate_text)
            if comp.similarity_score >= 0.85:
                # Match detected
                alert_code = f"ALT-BLK-{obs.observed_at.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
                title = f"Watchlist Plate Match: {entry.plate_text}"
                desc = (
                    f"Observed vehicle plate '{obs.plate_text}' matched active watchlist entry "
                    f"'{entry.plate_text}' ({comp.similarity_score * 100:.1f}% similarity) for '{entry.reason}'."
                )

                evidence = {
                    "observed_plate": obs.plate_text,
                    "plate_confidence": float(obs.plate_confidence) if obs.plate_confidence else None,
                    "blacklist_plate": entry.plate_text,
                    "match_similarity": comp.similarity_score,
                    "match_type": comp.match_type,
                    "reason": entry.reason,
                    "priority": entry.priority,
                    "camera_id": str(obs.camera_id),
                    "timestamp": obs.observed_at.isoformat(),
                }

                alert = Alert(
                    id=uuid.uuid4(),
                    alert_code=alert_code,
                    alert_type="BLACKLIST_MATCH",
                    severity=entry.priority,
                    status="NEW",
                    confidence=comp.similarity_score,
                    title=title,
                    description=desc,
                    camera_id=obs.camera_id,
                    observation_id=obs.id,
                    blacklist_entry_id=entry.id,
                    evidence=evidence,
                )
                self._session.add(alert)
                await self._session.flush()
                await self._session.refresh(alert)
                logger.warn("alert.blacklist_match", code=alert_code, plate=obs.plate_text)
                return alert

        return None

    async def check_travel_time_anomaly(
        self,
        trajectory: Trajectory,
        p_from: TrajectoryPoint,
        p_to: TrajectoryPoint,
        conn: Optional[CameraConnection],
    ) -> Optional[Alert]:
        """
        Check for impossible travel times (extreme speed violation) between camera nodes.
        Generates explainable TRAVEL_TIME_ANOMALY alert.
        """
        delta_seconds = (p_to.timestamp - p_from.timestamp).total_seconds()
        if delta_seconds <= 0:
            return None

        if conn and conn.min_travel_time_s and delta_seconds < conn.min_travel_time_s:
            speed_kmh = (conn.distance_m / max(1.0, delta_seconds)) * 3.6 if conn.distance_m else 0.0

            alert_code = f"ALT-TIM-{p_to.timestamp.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
            title = "Travel Time Anomaly Detected"
            desc = (
                f"Vehicle transit duration of {delta_seconds:.0f}s is significantly below the minimum "
                f"expected travel time of {conn.min_travel_time_s}s between cameras."
            )

            evidence = {
                "from_camera_id": str(p_from.camera_id),
                "to_camera_id": str(p_to.camera_id),
                "actual_duration_seconds": delta_seconds,
                "min_expected_seconds": conn.min_travel_time_s,
                "max_expected_seconds": conn.max_travel_time_s,
                "calculated_speed_kmh": round(speed_kmh, 2),
                "trajectory_id": str(trajectory.id),
            }

            alert = Alert(
                id=uuid.uuid4(),
                alert_code=alert_code,
                alert_type="TRAVEL_TIME_ANOMALY",
                severity="high" if speed_kmh > 150.0 else "medium",
                status="NEW",
                confidence=0.95,
                title=title,
                description=desc,
                camera_id=p_to.camera_id,
                vehicle_identity_id=trajectory.vehicle_identity_id,
                trajectory_id=trajectory.id,
                evidence=evidence,
            )
            self._session.add(alert)
            await self._session.flush()
            await self._session.refresh(alert)
            return alert

        return None
