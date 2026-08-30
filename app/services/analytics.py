"""Urban traffic analytics service — data-driven intelligence calculations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.camera import Camera
from app.models.camera_connection import CameraConnection
from app.models.road import Road
from app.models.trajectory import Trajectory, TrajectoryPoint
from app.models.vehicle_observation import VehicleObservation
from app.schemas.analytics import (
    CameraHealthItem,
    CameraHealthResponse,
    CongestionReportResponse,
    CongestionSegment,
    ODMatrixCell,
    ODMatrixResponse,
    PairTravelTime,
    RouteFrequencyItem,
    RouteFrequencyResponse,
    TrafficDensityResponse,
    TrafficVolumeBucket,
    TrafficVolumeResponse,
    TravelTimeStatsResponse,
    VehicleClassCount,
    VehicleClassDistributionResponse,
)

logger = get_logger(__name__)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_traffic_volume(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1h",
        camera_id: uuid.UUID | None = None,
        road_id: uuid.UUID | None = None,
        vehicle_class: str | None = None,
    ) -> TrafficVolumeResponse:
        """Compute traffic volume bucketed by time interval across cameras."""
        query = select(VehicleObservation).where(
            VehicleObservation.observed_at >= start_time,
            VehicleObservation.observed_at <= end_time,
        )

        if camera_id:
            query = query.where(VehicleObservation.camera_id == camera_id)
        if vehicle_class:
            query = query.where(VehicleObservation.vehicle_class == vehicle_class)
        if road_id:
            # Join with camera to filter by road
            query = query.join(Camera, VehicleObservation.camera_id == Camera.id).where(
                Camera.road_id == road_id
            )

        result = await self._session.execute(query.order_by(VehicleObservation.observed_at.asc()))
        observations = list(result.scalars().all())

        # Determine interval delta
        interval_seconds = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "1d": 86400,
        }.get(interval, 3600)

        # Bucket observations
        buckets_map: dict[datetime, dict[str, Any]] = {}
        curr = start_time
        while curr < end_time:
            b_end = min(curr + timedelta(seconds=interval_seconds), end_time)
            buckets_map[curr] = {
                "bucket_start": curr,
                "bucket_end": b_end,
                "count": 0,
                "classes": {},
            }
            curr = b_end

        for obs in observations:
            # Find matching bucket
            for _b_start, b_data in buckets_map.items():
                if b_data["bucket_start"] <= obs.observed_at < b_data["bucket_end"]:
                    b_data["count"] += 1
                    cls_name = obs.vehicle_class or "unknown"
                    b_data["classes"][cls_name] = b_data["classes"].get(cls_name, 0) + 1
                    break

        buckets = [
            TrafficVolumeBucket(
                bucket_start=d["bucket_start"],
                bucket_end=d["bucket_end"],
                camera_id=camera_id,
                vehicle_count=d["count"],
                vehicle_class_counts=d["classes"],
            )
            for d in buckets_map.values()
        ]

        return TrafficVolumeResponse(
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            total_vehicles=len(observations),
            buckets=buckets,
        )

    async def get_vehicle_class_distribution(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        camera_id: uuid.UUID | None = None,
        road_id: uuid.UUID | None = None,
    ) -> VehicleClassDistributionResponse:
        """Compute vehicle classification counts and percentage distribution."""
        query = select(
            VehicleObservation.vehicle_class,
            func.count(VehicleObservation.id).label("class_count"),
        ).where(
            VehicleObservation.observed_at >= start_time,
            VehicleObservation.observed_at <= end_time,
        )

        if camera_id:
            query = query.where(VehicleObservation.camera_id == camera_id)
        if road_id:
            query = query.join(Camera, VehicleObservation.camera_id == Camera.id).where(
                Camera.road_id == road_id
            )

        query = query.group_by(VehicleObservation.vehicle_class)
        rows = (await self._session.execute(query)).all()

        total = sum(r.class_count for r in rows)
        distribution = []
        for r in rows:
            cls_name = r.vehicle_class or "unknown"
            pct = round((r.class_count / total) * 100.0, 2) if total > 0 else 0.0
            distribution.append(
                VehicleClassCount(vehicle_class=cls_name, count=r.class_count, percentage=pct)
            )

        return VehicleClassDistributionResponse(
            start_time=start_time,
            end_time=end_time,
            total_classified_vehicles=total,
            distribution=distribution,
        )

    async def get_traffic_density(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        camera_id: uuid.UUID | None = None,
        road_id: uuid.UUID | None = None,
    ) -> TrafficDensityResponse:
        """
        Calculate traffic density using Greenshields fundamental traffic flow theory:
        Density (k) = Flow Rate (q) / Space Mean Speed (v_s).
        """
        # 1. Total observed vehicles in window
        query = select(VehicleObservation).where(
            VehicleObservation.observed_at >= start_time,
            VehicleObservation.observed_at <= end_time,
        )
        if camera_id:
            query = query.where(VehicleObservation.camera_id == camera_id)
        if road_id:
            query = query.join(Camera, VehicleObservation.camera_id == Camera.id).where(
                Camera.road_id == road_id
            )

        obs_rows = (await self._session.execute(query)).scalars().all()
        vehicle_count = len(obs_rows)

        duration_hours = max((end_time - start_time).total_seconds() / 3600.0, 0.01)
        flow_rate = round(vehicle_count / duration_hours, 2)

        # 2. Space mean speed
        speeds = [
            float(o.estimated_speed_kmh)
            for o in obs_rows
            if o.estimated_speed_kmh and float(o.estimated_speed_kmh) > 0
        ]
        # Space-mean speed is the harmonic mean of individual speeds
        space_mean_speed = round(len(speeds) / sum(1.0 / s for s in speeds), 2) if speeds else 40.0

        # 3. Density = q / v_s (vehicles per km)
        density = round(flow_rate / max(space_mean_speed, 1.0), 2)

        # Level of service / density classification
        if density < 15.0:
            level = "low"
        elif density < 35.0:
            level = "moderate"
        elif density < 60.0:
            level = "high"
        else:
            level = "congested"

        cam_name = None
        if camera_id:
            cam = await self._session.get(Camera, camera_id)
            cam_name = cam.name if cam else None

        road_name = None
        if road_id:
            road = await self._session.get(Road, road_id)
            road_name = road.name if road else None

        return TrafficDensityResponse(
            camera_id=camera_id,
            camera_name=cam_name,
            road_id=road_id,
            road_name=road_name,
            start_time=start_time,
            end_time=end_time,
            flow_rate_veh_per_hour=flow_rate,
            space_mean_speed_kmh=space_mean_speed,
            density_veh_per_km=density,
            density_level=level,
        )

    async def get_travel_time_stats(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        source_camera_id: uuid.UUID | None = None,
        destination_camera_id: uuid.UUID | None = None,
    ) -> TravelTimeStatsResponse:
        """Calculate mean, median, p85, p95, min, max travel times between camera pairs."""
        # Query camera connections
        conn_query = select(CameraConnection)
        if source_camera_id:
            conn_query = conn_query.where(CameraConnection.source_camera_id == source_camera_id)
        if destination_camera_id:
            conn_query = conn_query.where(
                CameraConnection.destination_camera_id == destination_camera_id
            )

        connections = (await self._session.execute(conn_query)).scalars().all()
        pairs_stats: list[PairTravelTime] = []

        for conn in connections:
            # Query trajectory points representing transit from source to dest
            # Find points at destination camera whose previous point was source camera
            pts_query = select(TrajectoryPoint).where(
                TrajectoryPoint.camera_id == conn.destination_camera_id,
                TrajectoryPoint.timestamp >= start_time,
                TrajectoryPoint.timestamp <= end_time,
                TrajectoryPoint.segment_duration_s.isnot(None),
                TrajectoryPoint.segment_duration_s > 0,
            )
            pts = (await self._session.execute(pts_query)).scalars().all()

            durations = [float(p.segment_duration_s) for p in pts if p.segment_duration_s]
            if not durations:
                # If no real-time samples, fallback to connection bounds
                avg_s = float(
                    conn.avg_travel_time_s or (conn.min_travel_time_s + conn.max_travel_time_s) / 2
                )
                min_s = float(conn.min_travel_time_s)
                max_s = float(conn.max_travel_time_s)
                pairs_stats.append(
                    PairTravelTime(
                        source_camera_id=conn.source_camera_id,
                        source_camera_name=conn.source_camera.name if conn.source_camera else None,
                        destination_camera_id=conn.destination_camera_id,
                        destination_camera_name=conn.destination_camera.name
                        if conn.destination_camera
                        else None,
                        sample_count=0,
                        mean_travel_time_seconds=avg_s,
                        median_travel_time_seconds=avg_s,
                        p85_travel_time_seconds=avg_s * 1.15,
                        p95_travel_time_seconds=avg_s * 1.30,
                        min_travel_time_seconds=min_s,
                        max_travel_time_seconds=max_s,
                    )
                )
            else:
                arr = np.array(durations)
                pairs_stats.append(
                    PairTravelTime(
                        source_camera_id=conn.source_camera_id,
                        source_camera_name=conn.source_camera.name if conn.source_camera else None,
                        destination_camera_id=conn.destination_camera_id,
                        destination_camera_name=conn.destination_camera.name
                        if conn.destination_camera
                        else None,
                        sample_count=len(durations),
                        mean_travel_time_seconds=round(float(np.mean(arr)), 2),
                        median_travel_time_seconds=round(float(np.median(arr)), 2),
                        p85_travel_time_seconds=round(float(np.percentile(arr, 85)), 2),
                        p95_travel_time_seconds=round(float(np.percentile(arr, 95)), 2),
                        min_travel_time_seconds=round(float(np.min(arr)), 2),
                        max_travel_time_seconds=round(float(np.max(arr)), 2),
                    )
                )

        return TravelTimeStatsResponse(
            start_time=start_time,
            end_time=end_time,
            pairs=pairs_stats,
        )

    async def get_congestion_report(self) -> CongestionReportResponse:
        """Compare current travel times against expected baselines."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        stats_resp = await self.get_travel_time_stats(start_time=one_hour_ago, end_time=now)
        segments: list[CongestionSegment] = []
        indicators: list[float] = []

        for p in stats_resp.pairs:
            # Baseline is expected average travel time
            baseline = p.median_travel_time_seconds or 120.0
            current = p.mean_travel_time_seconds
            ci = round(current / max(1.0, baseline), 2)
            indicators.append(ci)

            if ci <= 1.0:
                status = "free_flow"
            elif ci <= 1.3:
                status = "moderate"
            elif ci <= 2.0:
                status = "heavy"
            else:
                status = "severe"

            segments.append(
                CongestionSegment(
                    source_camera_id=p.source_camera_id,
                    source_camera_name=p.source_camera_name,
                    destination_camera_id=p.destination_camera_id,
                    destination_camera_name=p.destination_camera_name,
                    current_mean_travel_time_s=current,
                    baseline_travel_time_s=baseline,
                    congestion_indicator=ci,
                    status=status,
                )
            )

        avg_ci = round(float(np.mean(indicators)), 2) if indicators else 1.0
        overall_status = (
            "free_flow" if avg_ci <= 1.0 else ("moderate" if avg_ci <= 1.3 else "heavy")
        )

        return CongestionReportResponse(
            timestamp=now,
            summary_congestion_index=avg_ci,
            overall_status=overall_status,
            segments=segments,
        )

    async def get_od_matrix(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
    ) -> ODMatrixResponse:
        """Calculate Origin-Destination trip matrix from completed trajectories."""
        query = select(Trajectory).where(
            Trajectory.start_time >= start_time,
            Trajectory.end_time <= end_time,
            Trajectory.points_count >= 2,
        )
        trajs = (await self._session.execute(query)).scalars().all()

        od_map: dict[tuple[str, str], dict[str, Any]] = {}

        for t in trajs:
            if len(t.ordered_camera_ids) >= 2:
                orig_id = str(t.ordered_camera_ids[0])
                dest_id = str(t.ordered_camera_ids[-1])
                orig_name = t.ordered_camera_names[0] if t.ordered_camera_names else orig_id
                dest_name = t.ordered_camera_names[-1] if t.ordered_camera_names else dest_id

                key = (orig_id, dest_id)
                if key not in od_map:
                    od_map[key] = {
                        "origin_camera_id": uuid.UUID(orig_id),
                        "origin_camera_name": orig_name,
                        "destination_camera_id": uuid.UUID(dest_id),
                        "destination_camera_name": dest_name,
                        "trip_count": 0,
                        "durations": [],
                        "distances": [],
                    }
                od_map[key]["trip_count"] += 1
                od_map[key]["durations"].append(t.total_travel_time_s)
                od_map[key]["distances"].append(t.total_distance_m)

        matrix = [
            ODMatrixCell(
                origin_camera_id=d["origin_camera_id"],
                origin_camera_name=d["origin_camera_name"],
                destination_camera_id=d["destination_camera_id"],
                destination_camera_name=d["destination_camera_name"],
                trip_count=d["trip_count"],
                average_duration_seconds=round(float(np.mean(d["durations"])), 2),
                average_distance_meters=round(float(np.mean(d["distances"])), 2),
            )
            for d in od_map.values()
        ]

        return ODMatrixResponse(
            start_time=start_time,
            end_time=end_time,
            total_trips=len(trajs),
            matrix=matrix,
        )

    async def get_route_frequency(
        self,
        *,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10,
    ) -> RouteFrequencyResponse:
        """Identify commonly observed multi-camera routes."""
        query = select(Trajectory).where(
            Trajectory.start_time >= start_time,
            Trajectory.end_time <= end_time,
        )
        trajs = (await self._session.execute(query)).scalars().all()

        route_map: dict[str, dict[str, Any]] = {}
        for t in trajs:
            names = t.ordered_camera_names or []
            if not names:
                continue
            r_str = " -> ".join(names)
            if r_str not in route_map:
                route_map[r_str] = {
                    "names": names,
                    "summary": r_str,
                    "count": 0,
                    "durations": [],
                    "distances_m": [],
                }
            route_map[r_str]["count"] += 1
            route_map[r_str]["durations"].append(t.total_travel_time_s)
            route_map[r_str]["distances_m"].append(t.total_distance_m)

        total_trajs = len(trajs)
        sorted_routes = sorted(route_map.values(), key=lambda x: x["count"], reverse=True)[:limit]

        items = [
            RouteFrequencyItem(
                route_camera_names=r["names"],
                route_summary=r["summary"],
                trip_count=r["count"],
                percentage=round((r["count"] / max(1, total_trajs)) * 100.0, 2),
                average_duration_seconds=round(float(np.mean(r["durations"])), 2),
                average_distance_km=round(float(np.mean(r["distances_m"])) / 1000.0, 3),
            )
            for r in sorted_routes
        ]

        return RouteFrequencyResponse(
            start_time=start_time,
            end_time=end_time,
            total_trips_analyzed=total_trajs,
            top_routes=items,
        )

    async def get_camera_health(self) -> CameraHealthResponse:
        """Track observations/minute, last sighting, inactivity, and status for all cameras."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        cameras = (await self._session.execute(select(Camera))).scalars().all()
        health_items: list[CameraHealthItem] = []
        online_count = 0
        offline_count = 0

        for cam in cameras:
            # Query observations in last hour
            count_q = select(func.count(VehicleObservation.id)).where(
                VehicleObservation.camera_id == cam.id,
                VehicleObservation.observed_at >= one_hour_ago,
            )
            obs_hour = (await self._session.execute(count_q)).scalar_one()

            # Query last observation
            last_q = (
                select(VehicleObservation.observed_at)
                .where(VehicleObservation.camera_id == cam.id)
                .order_by(VehicleObservation.observed_at.desc())
                .limit(1)
            )
            last_seen = (await self._session.execute(last_q)).scalar_one_or_none()

            inactivity_s = int((now - last_seen).total_seconds()) if last_seen else None
            obs_per_min = round(obs_hour / 60.0, 2)

            if inactivity_s is not None and inactivity_s <= 300:
                cam_status = "online"
                online_count += 1
            elif inactivity_s is not None and inactivity_s <= 1800:
                cam_status = "stale"
                online_count += 1
            else:
                cam_status = "offline"
                offline_count += 1

            health_items.append(
                CameraHealthItem(
                    camera_id=cam.id,
                    camera_name=cam.name,
                    status=cam_status,
                    observations_last_hour=obs_hour,
                    observations_per_minute=obs_per_min,
                    last_observation_at=last_seen,
                    inactivity_seconds=inactivity_s,
                )
            )

        return CameraHealthResponse(
            timestamp=now,
            total_cameras=len(cameras),
            online_cameras=online_count,
            offline_cameras=offline_count,
            cameras=health_items,
        )
