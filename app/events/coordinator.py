"""Real-time traffic event coordinator — orchestrates end-to-end observation pipeline."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.events.contracts import DomainEvent, EventType
from app.events.interfaces import EventBus
from app.schemas.vehicle_observation import VehicleObservationCreate
from app.services.alert import AlertService
from app.services.trajectory import TrajectoryService
from app.services.vehicle_identity import VehicleIdentityService
from app.services.vehicle_observation import VehicleObservationService

logger = get_logger(__name__)


class EventCoordinator:
    """
    Coordinates the continuous transformation:
    AI Observation -> Ingestion -> Single-Camera Tracking ->
    Cross-Camera Association -> Trajectory Update -> Alert & Anomaly Detection.
    """

    def __init__(
        self,
        session: AsyncSession,
        event_bus: EventBus,
    ) -> None:
        self._session = session
        self._bus = event_bus
        self._obs_service = VehicleObservationService(session)
        self._identity_service = VehicleIdentityService(session)
        self._trajectory_service = TrajectoryService(session)
        self._alert_service = AlertService(session)

    async def handle_vehicle_observed(self, payload: VehicleObservationCreate) -> dict[str, Any]:
        """
        Full real-time event pipeline handler for an incoming vehicle sighting.
        """
        # 1. Ingest observation into database
        obs_resp = await self._obs_service.create_observation(payload)
        obs_id = obs_resp.id

        await self._bus.publish(
            DomainEvent(
                event_type=EventType.VEHICLE_OBSERVED.value,
                source=payload.source,
                payload=obs_resp.model_dump(),
                idempotency_key=f"obs-{payload.source}-{payload.source_observation_id}",
            )
        )

        # 2. Check Blacklist Matches
        obs_model = await self._obs_service._repo.get_by_id(obs_id)
        alert = None
        if obs_model:
            alert = await self._alert_service.check_observation_blacklist(obs_model)
            if alert:
                await self._bus.publish(
                    DomainEvent(
                        event_type=EventType.ALERT_CREATED.value,
                        source="alert-engine",
                        payload={
                            "alert_id": str(alert.id),
                            "alert_code": alert.alert_code,
                            "type": alert.alert_type,
                        },
                    )
                )

        # 3. Run Cross-Camera Association
        identity_resp, match_resp = await self._identity_service.associate_observation(obs_id)

        if match_resp:
            await self._bus.publish(
                DomainEvent(
                    event_type=EventType.VEHICLE_MATCHED.value,
                    source="association-engine",
                    payload=match_resp.model_dump(),
                )
            )

        # 4. Update / Start Trajectory
        traj = None
        active_traj = await self._trajectory_service._repo.get_active_by_identity(identity_resp.id)
        if obs_model:
            if active_traj:
                try:
                    traj = await self._trajectory_service.append_observation(active_traj, obs_model)
                except Exception as e:
                    logger.warning("trajectory.append_failed_starting_new", error=str(e))
                    traj = await self._trajectory_service.start_trajectory(
                        identity_resp.id, obs_model
                    )
            else:
                traj = await self._trajectory_service.start_trajectory(identity_resp.id, obs_model)

            if traj:
                await self._bus.publish(
                    DomainEvent(
                        event_type=EventType.TRAJECTORY_UPDATED.value,
                        source="trajectory-engine",
                        payload={"trajectory_id": str(traj.id), "points_count": traj.points_count},
                    )
                )

        return {
            "observation": obs_resp,
            "identity": identity_resp,
            "match": match_resp,
            "trajectory_id": traj.trajectory_id if traj else None,
            "alert": alert.alert_code if alert else None,
        }
