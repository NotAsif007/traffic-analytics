"""Trajectory service — city-wide vehicle trajectory reconstruction and analytics."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.trajectory import Trajectory, TrajectoryPoint
from app.models.vehicle_observation import VehicleObservation
from app.repositories.camera import CameraRepository
from app.repositories.camera_connection import CameraConnectionRepository
from app.repositories.trajectory import TrajectoryRepository
from app.repositories.vehicle_identity import VehicleIdentityRepository
from app.schemas.common import PaginatedResponse
from app.schemas.trajectory import (
    TrajectoryDetailResponse,
    TrajectoryFilters,
    TrajectoryPointResponse,
    TrajectoryResponse,
    TrajectoryTimelineResponse,
    TrajectoryTimelineSegment,
)
from app.services.road import _geometry_to_geojson

logger = get_logger(__name__)


def _point_to_response(pt: TrajectoryPoint) -> TrajectoryPointResponse:
    cam_name = pt.camera.name if pt.camera else None
    return TrajectoryPointResponse(
        id=pt.id,
        trajectory_id=pt.trajectory_id,
        sequence_order=pt.sequence_order,
        camera_id=pt.camera_id,
        camera_name=cam_name,
        observation_id=pt.observation_id,
        track_id=pt.track_id,
        timestamp=pt.timestamp,
        plate_text=pt.plate_text,
        plate_confidence=float(pt.plate_confidence) if pt.plate_confidence else None,
        speed_kmh=float(pt.speed_kmh) if pt.speed_kmh else None,
        segment_distance_m=pt.segment_distance_m,
        segment_duration_s=pt.segment_duration_s,
        is_interpolated=pt.is_interpolated,
        metadata=pt.metadata_,
        created_at=pt.created_at,
        updated_at=pt.updated_at,
    )


def _trajectory_to_response(trj: Trajectory) -> TrajectoryResponse:
    geom = _geometry_to_geojson(trj.route_geometry)
    return TrajectoryResponse(
        id=trj.id,
        trajectory_id=trj.trajectory_id,
        vehicle_identity_id=trj.vehicle_identity_id,
        start_time=trj.start_time,
        end_time=trj.end_time,
        status=trj.status,
        confidence=float(trj.confidence),
        total_distance_m=trj.total_distance_m,
        total_travel_time_s=trj.total_travel_time_s,
        average_speed_kmh=float(trj.average_speed_kmh) if trj.average_speed_kmh else None,
        points_count=trj.points_count,
        ordered_camera_ids=[uuid.UUID(str(cid)) for cid in trj.ordered_camera_ids],
        ordered_camera_names=trj.ordered_camera_names,
        route_geometry=geom,
        notes=trj.notes,
        metadata=trj.metadata_,
        created_at=trj.created_at,
        updated_at=trj.updated_at,
    )


class TrajectoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = TrajectoryRepository(session)
        self._identity_repo = VehicleIdentityRepository(session)
        self._camera_repo = CameraRepository(session)
        self._conn_repo = CameraConnectionRepository(session)

    async def get_trajectory(self, trajectory_id: uuid.UUID) -> TrajectoryResponse:
        trj = await self._repo.get_by_id(trajectory_id)
        if not trj:
            raise NotFoundError("Trajectory", trajectory_id)
        return _trajectory_to_response(trj)

    async def get_trajectory_detail(self, trajectory_id: uuid.UUID) -> TrajectoryDetailResponse:
        trj = await self._repo.get_with_points(trajectory_id)
        if not trj:
            raise NotFoundError("Trajectory", trajectory_id)

        points = [_point_to_response(p) for p in (trj.points or [])]
        base_resp = _trajectory_to_response(trj)
        return TrajectoryDetailResponse(
            **base_resp.model_dump(),
            points=points,
        )

    async def list_trajectories(
        self,
        *,
        filters: TrajectoryFilters,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TrajectoryResponse]:
        offset = (page - 1) * page_size
        records, total = await self._repo.list_trajectories(
            filters=filters, offset=offset, limit=page_size
        )
        items = [_trajectory_to_response(r) for r in records]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def list_vehicle_trajectories(
        self,
        vehicle_identity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[TrajectoryResponse]:
        ident = await self._identity_repo.get_by_id(vehicle_identity_id)
        if not ident:
            raise NotFoundError("VehicleIdentity", vehicle_identity_id)

        filters = TrajectoryFilters(vehicle_identity_id=vehicle_identity_id)
        return await self.list_trajectories(filters=filters, page=page, page_size=page_size)

    async def start_trajectory(
        self,
        vehicle_identity_id: uuid.UUID,
        obs: VehicleObservation,
    ) -> Trajectory:
        """Initialize a new trajectory starting from a vehicle observation."""
        camera = await self._camera_repo.get_by_id(obs.camera_id)
        camera_name = camera.name if camera else str(obs.camera_id)

        code_tag = f"TRJ-{obs.observed_at.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

        traj = Trajectory(
            id=uuid.uuid4(),
            trajectory_id=code_tag,
            vehicle_identity_id=vehicle_identity_id,
            start_time=obs.observed_at,
            end_time=obs.observed_at,
            status="active",
            confidence=float(obs.detection_confidence or 0.85),
            total_distance_m=0.0,
            total_travel_time_s=0,
            average_speed_kmh=float(obs.estimated_speed_kmh) if obs.estimated_speed_kmh else 0.0,
            points_count=1,
            ordered_camera_ids=[str(obs.camera_id)],
            ordered_camera_names=[camera_name],
        )
        self._repo._session.add(traj)
        await self._repo._session.flush()

        point = TrajectoryPoint(
            id=uuid.uuid4(),
            trajectory_id=traj.id,
            sequence_order=1,
            camera_id=obs.camera_id,
            observation_id=obs.id,
            timestamp=obs.observed_at,
            plate_text=obs.plate_text,
            plate_confidence=obs.plate_confidence,
            speed_kmh=obs.estimated_speed_kmh,
            segment_distance_m=0.0,
            segment_duration_s=0.0,
            is_interpolated=False,
        )
        self._repo._session.add(point)
        await self._repo._session.flush()
        await self._repo._session.refresh(traj)
        return traj

    async def append_observation(
        self,
        trajectory: Trajectory,
        obs: VehicleObservation,
    ) -> Trajectory:
        """
        Append a new observation to an existing trajectory.
        Validates transition feasibility, recalculates metrics, and updates geometry.
        """
        # Fetch the latest trajectory point to validate transition
        trj_with_points = await self._repo.get_with_points(trajectory.id)
        points = trj_with_points.points if trj_with_points and trj_with_points.points else []
        last_pt = points[-1] if points else None

        if last_pt:
            delta_seconds = (obs.observed_at - last_pt.timestamp).total_seconds()
            if delta_seconds < 0:
                raise ValidationError(
                    "Cannot append observation with timestamp earlier than previous point"
                )

            # Look up connection between cameras
            conn = await self._conn_repo.get_by_camera_pair(last_pt.camera_id, obs.camera_id)
            segment_dist_m = conn.distance_m if (conn and conn.distance_m) else 500.0

            # Calculate speed on this segment
            speed_kmh = (segment_dist_m / max(1.0, delta_seconds)) * 3.6
            if delta_seconds > 0 and speed_kmh > 200.0:
                logger.warning(
                    "trajectory.high_speed_warning",
                    speed_kmh=speed_kmh,
                    traj_id=trajectory.trajectory_id,
                )

            seq_order = len(points) + 1
        else:
            delta_seconds = 0.0
            segment_dist_m = 0.0
            speed_kmh = float(obs.estimated_speed_kmh or 0.0)
            seq_order = 1

        camera = await self._camera_repo.get_by_id(obs.camera_id)
        camera_name = camera.name if camera else str(obs.camera_id)

        new_point = TrajectoryPoint(
            id=uuid.uuid4(),
            trajectory_id=trajectory.id,
            sequence_order=seq_order,
            camera_id=obs.camera_id,
            observation_id=obs.id,
            timestamp=obs.observed_at,
            plate_text=obs.plate_text,
            plate_confidence=obs.plate_confidence,
            speed_kmh=obs.estimated_speed_kmh or speed_kmh,
            segment_distance_m=segment_dist_m,
            segment_duration_s=delta_seconds,
            is_interpolated=False,
        )
        self._repo._session.add(new_point)

        # Update trajectory summary metrics
        trajectory.end_time = obs.observed_at
        trajectory.total_distance_m += segment_dist_m
        trajectory.total_travel_time_s = int(
            (obs.observed_at - trajectory.start_time).total_seconds()
        )
        trajectory.points_count = seq_order

        if trajectory.total_travel_time_s > 0:
            trajectory.average_speed_kmh = round(
                (trajectory.total_distance_m / trajectory.total_travel_time_s) * 3.6, 2
            )

        trajectory.ordered_camera_ids = list(trajectory.ordered_camera_ids) + [str(obs.camera_id)]
        trajectory.ordered_camera_names = list(trajectory.ordered_camera_names) + [camera_name]

        await self._repo._session.flush()
        await self._repo._session.refresh(trajectory)
        return trajectory

    async def get_timeline(self, trajectory_id: uuid.UUID) -> TrajectoryTimelineResponse:
        """Generate structured chronological journey timeline."""
        trj = await self._repo.get_with_points(trajectory_id)
        if not trj:
            raise NotFoundError("Trajectory", trajectory_id)

        points = trj.points or []
        segments: list[TrajectoryTimelineSegment] = []

        for i in range(1, len(points)):
            p_prev = points[i - 1]
            p_curr = points[i]

            elapsed = (p_curr.timestamp - p_prev.timestamp).total_seconds()
            dist = p_curr.segment_distance_m or 0.0
            spd = (dist / max(1.0, elapsed)) * 3.6 if elapsed > 0 else 0.0

            conn = await self._conn_repo.get_by_camera_pair(p_prev.camera_id, p_curr.camera_id)
            is_connected = conn is not None

            status_label = "plausible"
            if spd > 120.0:
                status_label = "speed_warning"
            elif elapsed > 1800.0:
                status_label = "gap"

            segments.append(
                TrajectoryTimelineSegment(
                    from_sequence=p_prev.sequence_order,
                    to_sequence=p_curr.sequence_order,
                    from_camera_id=p_prev.camera_id,
                    from_camera_name=p_prev.camera.name if p_prev.camera else None,
                    to_camera_id=p_curr.camera_id,
                    to_camera_name=p_curr.camera.name if p_curr.camera else None,
                    from_timestamp=p_prev.timestamp,
                    to_timestamp=p_curr.timestamp,
                    elapsed_seconds=elapsed,
                    distance_meters=dist,
                    speed_kmh=round(spd, 2),
                    plate_text=p_curr.plate_text or p_prev.plate_text,
                    plate_confidence=float(p_curr.plate_confidence)
                    if p_curr.plate_confidence
                    else None,
                    is_connected_road=is_connected,
                    segment_status=status_label,
                )
            )

        mins = trj.total_travel_time_s // 60
        secs = trj.total_travel_time_s % 60
        time_formatted = f"{mins} min {secs} sec" if mins > 0 else f"{secs} sec"
        route_str = " -> ".join(trj.ordered_camera_names)

        return TrajectoryTimelineResponse(
            trajectory_id=trj.trajectory_id,
            vehicle_identity_id=trj.vehicle_identity_id,
            start_time=trj.start_time,
            end_time=trj.end_time,
            total_travel_time_seconds=trj.total_travel_time_s,
            total_travel_time_formatted=time_formatted,
            total_distance_km=round(trj.total_distance_m / 1000.0, 3),
            average_speed_kmh=float(trj.average_speed_kmh) if trj.average_speed_kmh else None,
            route_summary=route_str,
            confidence=float(trj.confidence),
            status=trj.status,
            segments=segments,
        )
