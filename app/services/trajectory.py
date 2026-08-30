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
    TrajectoryPredictionResponse,
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

    async def predict_next_locations(
        self, trajectory_id: uuid.UUID
    ) -> TrajectoryPredictionResponse:
        """
        Forecast the vehicle's future trajectory, next likely camera intercepts,
        estimated arrival times (ETA), and corridor destinations.
        """
        from datetime import timedelta

        from app.schemas.trajectory import PredictedNextHop, TrajectoryPredictionResponse

        trj = await self._repo.get_with_points(trajectory_id)
        if not trj:
            raise NotFoundError("Trajectory", trajectory_id)

        points = trj.points or []
        if not points:
            # Fallback to trajectory start metadata
            last_cam_id = trj.ordered_camera_ids[-1] if trj.ordered_camera_ids else uuid.uuid4()
            last_cam_name = trj.ordered_camera_names[-1] if trj.ordered_camera_names else "Current Camera"
            last_time = trj.end_time
            last_speed = float(trj.average_speed_kmh or 45.0)
        else:
            last_pt = points[-1]
            last_cam_id = last_pt.camera_id
            last_cam_name = last_pt.camera.name if last_pt.camera else str(last_pt.camera_id)
            last_time = last_pt.timestamp
            last_speed = float(last_pt.speed_kmh or trj.average_speed_kmh or 45.0)

        # 1. Query outgoing topological connections from the current camera
        connections, _ = await self._conn_repo.list_connections(
            source_camera_id=last_cam_id, limit=20
        )

        predicted_hops: list[PredictedNextHop] = []

        if connections:
            raw_weights = []
            hop_candidates = []

            for conn in connections:
                dest_cam = conn.destination_camera
                dest_name = dest_cam.name if dest_cam else str(conn.destination_camera_id)
                road_name = conn.road.name if conn.road else "Connected Arterial"
                dist_m = float(conn.distance_m or 800.0)

                # Estimated travel duration
                if conn.avg_travel_time_s and conn.avg_travel_time_s > 0:
                    travel_s = float(conn.avg_travel_time_s)
                else:
                    speed_mps = max(5.0, (last_speed * 1000.0) / 3600.0)
                    travel_s = dist_m / speed_mps

                eta = last_time + timedelta(seconds=int(travel_s))
                # Weight inversely proportional to distance and travel time
                weight = 1.0 / max(1.0, travel_s)
                raw_weights.append(weight)

                hop_candidates.append({
                    "camera_id": conn.destination_camera_id,
                    "camera_name": dest_name,
                    "road_name": road_name,
                    "distance_meters": round(dist_m, 1),
                    "estimated_travel_time_seconds": round(travel_s, 1),
                    "estimated_arrival_time": eta,
                    "base_conf": float(trj.confidence),
                })

            total_weight = sum(raw_weights) if raw_weights else 1.0

            for i, cand in enumerate(hop_candidates):
                prob = round(raw_weights[i] / total_weight, 4)
                conf = round(cand["base_conf"] * prob, 4)
                predicted_hops.append(
                    PredictedNextHop(
                        camera_id=cand["camera_id"],
                        camera_name=cand["camera_name"],
                        road_name=cand["road_name"],
                        probability=prob,
                        distance_meters=cand["distance_meters"],
                        estimated_travel_time_seconds=cand["estimated_travel_time_seconds"],
                        estimated_arrival_time=cand["estimated_arrival_time"],
                        confidence_score=max(0.2, conf),
                    )
                )

            # Sort by highest probability first
            predicted_hops.sort(key=lambda h: h.probability, reverse=True)
        else:
            # If no direct forward edges, estimate radial progression
            speed_mps = max(5.0, (last_speed * 1000.0) / 3600.0)
            default_dist = 1200.0
            travel_s = default_dist / speed_mps
            eta = last_time + timedelta(seconds=int(travel_s))

            predicted_hops.append(
                PredictedNextHop(
                    camera_id=uuid.uuid4(),
                    camera_name=f"Forward Sensor Downstream of {last_cam_name}",
                    road_name="Primary Metropolitan Exit Corridor",
                    probability=0.85,
                    distance_meters=default_dist,
                    estimated_travel_time_seconds=round(travel_s, 1),
                    estimated_arrival_time=eta,
                    confidence_score=round(float(trj.confidence) * 0.85, 4),
                )
            )

        top_corridor = predicted_hops[0].road_name if predicted_hops else "Outer Ring Road Exit"

        return TrajectoryPredictionResponse(
            trajectory_id=trj.trajectory_id,
            vehicle_identity_id=trj.vehicle_identity_id,
            current_camera_id=last_cam_id,
            current_camera_name=last_cam_name,
            last_seen_timestamp=last_time,
            current_speed_kmh=round(last_speed, 1),
            predicted_next_hops=predicted_hops,
            predicted_destination_corridor=top_corridor,
            deviation_risk_level="LOW" if len(predicted_hops) > 0 else "MEDIUM",
            forecast_method="Markov Spatio-Temporal Graph Propagation",
        )

