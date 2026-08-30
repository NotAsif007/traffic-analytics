"""Command Center Dashboard service — read-optimized data consolidation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.alert import Alert
from app.models.camera import Camera
from app.models.road import Road
from app.models.trajectory import Trajectory
from app.models.vehicle_identity import VehicleIdentity, VehicleMatch
from app.models.vehicle_observation import VehicleObservation
from app.schemas.dashboard import (
    AlertInvestigationResponse,
    CameraBrief,
    CameraVisitTimeline,
    CityOverviewResponse,
    CongestionHotspot,
    DashboardAnalyticsSummaryResponse,
    LiveMapResponse,
    MapAlertMarker,
    MapCameraNode,
    MapRoadSegment,
    MapTrajectoryLine,
    PlateObservationEvidence,
    RecentActivityItem,
    VehicleInvestigationResponse,
)
from app.services.analytics import AnalyticsService

logger = get_logger(__name__)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._analytics = AnalyticsService(session)

    async def get_city_overview(self) -> CityOverviewResponse:
        """
        Produce a high-level summary of city traffic, active cameras, congestion, and alerts.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Cameras
        cams_result = await self._session.execute(select(Camera))
        all_cameras = list(cams_result.scalars().all())
        total_cams = len(all_cameras)
        active_cams = sum(1 for c in all_cameras if c.status == "active")
        online_pct = (active_cams / total_cams * 100.0) if total_cams > 0 else 0.0

        # 2. Observations today
        obs_today_q = (
            select(func.count())
            .select_from(VehicleObservation)
            .where(VehicleObservation.observed_at >= today_start)
        )
        obs_today = (await self._session.execute(obs_today_q)).scalar_one()

        # 3. Active alerts
        alerts_q = select(Alert).where(Alert.status.in_(["NEW", "ACKNOWLEDGED"]))
        active_alerts = list((await self._session.execute(alerts_q)).scalars().all())
        active_alerts_count = len(active_alerts)
        critical_alerts_count = sum(1 for a in active_alerts if a.severity in ("critical", "high"))

        # 4. Traffic Level & Congestion Hotspots
        congest_report = await self._analytics.get_congestion_report()
        hotspots: list[CongestionHotspot] = []
        for pair in congest_report.segments:
            if pair.congestion_indicator > 1.2:
                sev = (
                    "severe"
                    if pair.congestion_indicator > 2.0
                    else "high"
                    if pair.congestion_indicator > 1.5
                    else "moderate"
                )
                hotspots.append(
                    CongestionHotspot(
                        corridor_name=f"{pair.source_camera_name} → {pair.destination_camera_name}",
                        source_camera_name=pair.source_camera_name or "Source",
                        destination_camera_name=pair.destination_camera_name or "Dest",
                        congestion_index=pair.congestion_indicator,
                        current_travel_time_s=pair.current_mean_travel_time_s,
                        baseline_travel_time_s=pair.baseline_travel_time_s,
                        severity=sev,
                    )
                )

        traffic_level = "low"
        if len(hotspots) >= 3 or congest_report.summary_congestion_index > 1.5:
            traffic_level = "congested"
        elif len(hotspots) >= 1 or congest_report.summary_congestion_index > 1.2:
            traffic_level = "heavy"
        elif obs_today > 100:
            traffic_level = "moderate"

        # 5. Recent activity
        recent_activity: list[RecentActivityItem] = []
        for a in sorted(active_alerts, key=lambda x: x.created_at, reverse=True)[:5]:
            recent_activity.append(
                RecentActivityItem(
                    activity_type="ALERT",
                    title=a.title,
                    description=a.description,
                    timestamp=a.created_at,
                    camera_name=a.camera.name if a.camera else None,
                    severity=a.severity,
                )
            )

        return CityOverviewResponse(
            generated_at=now,
            active_cameras_count=active_cams,
            total_cameras_count=total_cams,
            cameras_online_percentage=round(online_pct, 2),
            vehicles_observed_today=obs_today,
            current_traffic_level=traffic_level,
            active_alerts_count=active_alerts_count,
            critical_alerts_count=critical_alerts_count,
            congestion_hotspots=hotspots,
            recent_activity=recent_activity,
        )

    async def get_live_map(self) -> LiveMapResponse:
        """
        Produce complete GIS layer with cameras, road network, active trajectories, and alerts.
        """
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        # 1. Cameras with intensity
        cams_result = await self._session.execute(select(Camera))
        cameras = list(cams_result.scalars().all())

        map_cameras: list[MapCameraNode] = []
        for cam in cameras:
            cnt_q = (
                select(func.count())
                .select_from(VehicleObservation)
                .where(
                    VehicleObservation.camera_id == cam.id,
                    VehicleObservation.observed_at >= one_hour_ago,
                )
            )
            obs_cnt = (await self._session.execute(cnt_q)).scalar_one()

            last_q = select(func.max(VehicleObservation.observed_at)).where(
                VehicleObservation.camera_id == cam.id
            )
            last_seen = (await self._session.execute(last_q)).scalar_one()

            intensity = "high" if obs_cnt > 50 else "moderate" if obs_cnt > 10 else "low"
            lat = cam.location.coordinates[1] if cam.location else 0.0
            lon = cam.location.coordinates[0] if cam.location else 0.0

            map_cameras.append(
                MapCameraNode(
                    id=cam.id,
                    name=cam.name,
                    latitude=lat,
                    longitude=lon,
                    status="online" if cam.status == "active" else "offline",
                    current_intensity=intensity,
                    observations_last_hour=obs_cnt,
                    last_observation_time=last_seen,
                )
            )

        # 2. Road segments
        roads_result = await self._session.execute(select(Road))
        roads = list(roads_result.scalars().all())
        map_roads: list[MapRoadSegment] = []
        for r in roads:
            geom = (
                r.geometry.model_dump() if r.geometry else {"type": "LineString", "coordinates": []}
            )
            map_roads.append(
                MapRoadSegment(
                    id=r.id,
                    name=r.name,
                    geometry_geojson=geom,
                    current_congestion_index=1.0,
                )
            )

        # 3. Active Trajectories
        trajs_result = await self._session.execute(
            select(Trajectory)
            .where(Trajectory.status == "active")
            .options(selectinload(Trajectory.identity))
            .limit(50)
        )
        active_trajs = list(trajs_result.scalars().all())
        map_trajs: list[MapTrajectoryLine] = []
        for t in active_trajs:
            plate = t.identity.primary_plate if t.identity else None
            coords: list[list[float]] = []
            if t.route_geometry:
                coords = [list(c) for c in t.route_geometry.coordinates]

            map_trajs.append(
                MapTrajectoryLine(
                    trajectory_id=t.id,
                    vehicle_identity_id=t.vehicle_identity_id,
                    canonical_plate=plate,
                    coordinates=coords,
                    confidence=float(t.confidence),
                    start_time=t.start_time,
                    last_seen_time=t.end_time,
                    total_distance_m=float(t.total_distance_m),
                    camera_names=t.ordered_camera_names or [],
                )
            )

        # 4. Active Alerts
        alerts_result = await self._session.execute(
            select(Alert)
            .where(Alert.status.in_(["NEW", "ACKNOWLEDGED"]))
            .options(selectinload(Alert.camera))
            .limit(50)
        )
        active_alerts = list(alerts_result.scalars().all())
        map_alerts: list[MapAlertMarker] = []
        for a in active_alerts:
            lat = a.camera.location.coordinates[1] if a.camera and a.camera.location else None
            lon = a.camera.location.coordinates[0] if a.camera and a.camera.location else None
            cam_name = a.camera.name if a.camera else None
            map_alerts.append(
                MapAlertMarker(
                    id=a.id,
                    alert_code=a.alert_code,
                    alert_type=a.alert_type,
                    severity=a.severity,
                    latitude=lat,
                    longitude=lon,
                    camera_name=cam_name,
                    title=a.title,
                    timestamp=a.created_at,
                )
            )

        return LiveMapResponse(
            generated_at=now,
            cameras=map_cameras,
            road_segments=map_roads,
            active_trajectories=map_trajs,
            active_alerts=map_alerts,
        )

    async def investigate_vehicle(self, identity_id: uuid.UUID) -> VehicleInvestigationResponse:
        """
        Assemble comprehensive forensic dossier for a physical vehicle identity.
        """
        result = await self._session.execute(
            select(VehicleIdentity).where(VehicleIdentity.id == identity_id)
        )
        identity = result.scalar_one_or_none()
        if not identity:
            raise NotFoundError("VehicleIdentity", identity_id)

        # Find linked observations via VehicleMatch
        matches_result = await self._session.execute(
            select(VehicleMatch).where(VehicleMatch.vehicle_identity_id == identity_id)
        )
        matches = list(matches_result.scalars().all())
        obs_ids: set[uuid.UUID] = set()
        for m in matches:
            if m.source_observation_id:
                obs_ids.add(m.source_observation_id)
            if m.target_observation_id:
                obs_ids.add(m.target_observation_id)

        # Observations query
        observations: list[VehicleObservation] = []
        if obs_ids:
            obs_res = await self._session.execute(
                select(VehicleObservation).where(VehicleObservation.id.in_(obs_ids))
            )
            observations = list(obs_res.scalars().all())
        elif identity.primary_plate:
            obs_res = await self._session.execute(
                select(VehicleObservation).where(
                    VehicleObservation.plate_text == identity.primary_plate
                )
            )
            observations = list(obs_res.scalars().all())

        sorted_obs = sorted(observations, key=lambda x: x.observed_at)
        timeline: list[CameraVisitTimeline] = []
        plate_evidences: list[PlateObservationEvidence] = []

        last_cam_name = None
        last_coords = None

        for idx, obs in enumerate(sorted_obs):
            cam = await self._session.get(Camera, obs.camera_id)
            cam_name = cam.name if cam else f"CAM-{str(obs.camera_id)[:4]}"
            lat = cam.location.coordinates[1] if cam and cam.location else 0.0
            lon = cam.location.coordinates[0] if cam and cam.location else 0.0

            last_cam_name = cam_name
            last_coords = [lon, lat]

            transit_s = None
            speed_kmh = None
            if idx > 0:
                transit_s = (obs.observed_at - sorted_obs[idx - 1].observed_at).total_seconds()
                if obs.estimated_speed_kmh:
                    speed_kmh = float(obs.estimated_speed_kmh)

            timeline.append(
                CameraVisitTimeline(
                    step_number=idx + 1,
                    camera_id=obs.camera_id,
                    camera_name=cam_name,
                    latitude=lat,
                    longitude=lon,
                    timestamp=obs.observed_at,
                    dwell_or_transit_seconds=transit_s,
                    segment_speed_kmh=speed_kmh,
                )
            )

            plate_evidences.append(
                PlateObservationEvidence(
                    observation_id=obs.id,
                    camera_id=obs.camera_id,
                    camera_name=cam_name,
                    timestamp=obs.observed_at,
                    raw_plate_text=obs.plate_text,
                    plate_confidence=float(obs.plate_confidence) if obs.plate_confidence else None,
                    detection_confidence=float(obs.detection_confidence),
                    vehicle_class=obs.vehicle_class or identity.vehicle_class or "unknown",
                    vehicle_color=obs.vehicle_color or identity.vehicle_color or "unknown",
                    image_path=obs.frame_path,
                    plate_crop_path=obs.plate_crop_path,
                )
            )

        # Active alerts on this vehicle
        alerts_result = await self._session.execute(
            select(Alert)
            .where(Alert.vehicle_identity_id == identity_id)
            .options(selectinload(Alert.camera))
        )
        alerts = list(alerts_result.scalars().all())
        map_alerts: list[MapAlertMarker] = []
        for a in alerts:
            lat = a.camera.location.coordinates[1] if a.camera and a.camera.location else None
            lon = a.camera.location.coordinates[0] if a.camera and a.camera.location else None
            map_alerts.append(
                MapAlertMarker(
                    id=a.id,
                    alert_code=a.alert_code,
                    alert_type=a.alert_type,
                    severity=a.severity,
                    latitude=lat,
                    longitude=lon,
                    camera_name=a.camera.name if a.camera else None,
                    title=a.title,
                    timestamp=a.created_at,
                )
            )

        return VehicleInvestigationResponse(
            identity_id=identity.id,
            canonical_plate=identity.primary_plate,
            vehicle_class=identity.vehicle_class or "unknown",
            vehicle_color=identity.vehicle_color or "unknown",
            overall_confidence=float(identity.confidence),
            first_seen_at=identity.first_seen_at,
            last_seen_at=identity.last_seen_at,
            total_sightings_count=identity.total_sightings,
            last_known_camera_name=last_cam_name,
            last_known_coordinates=last_coords,
            camera_history=timeline,
            plate_observations=plate_evidences,
            active_alerts=map_alerts,
        )

    async def investigate_alert(self, alert_id: uuid.UUID) -> AlertInvestigationResponse:
        """
        Assemble complete explainability and forensic evidence for a specific alert.
        """
        result = await self._session.execute(
            select(Alert)
            .where(Alert.id == alert_id)
            .options(
                selectinload(Alert.camera),
                selectinload(Alert.vehicle_identity),
                selectinload(Alert.trajectory),
            )
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise NotFoundError("Alert", alert_id)

        cameras_involved: list[CameraBrief] = []
        if alert.camera:
            lat = alert.camera.location.coordinates[1] if alert.camera.location else 0.0
            lon = alert.camera.location.coordinates[0] if alert.camera.location else 0.0
            cameras_involved.append(
                CameraBrief(
                    id=alert.camera.id,
                    name=alert.camera.name,
                    latitude=lat,
                    longitude=lon,
                    direction=alert.camera.direction,
                )
            )

        traj_summary = None
        if alert.trajectory:
            t = alert.trajectory
            plate = alert.vehicle_identity.primary_plate if alert.vehicle_identity else None
            coords: list[list[float]] = []
            if t.route_geometry:
                coords = [list(c) for c in t.route_geometry.coordinates]
            traj_summary = MapTrajectoryLine(
                trajectory_id=t.id,
                vehicle_identity_id=t.vehicle_identity_id,
                canonical_plate=plate,
                coordinates=coords,
                confidence=float(t.confidence),
                start_time=t.start_time,
                last_seen_time=t.end_time,
                total_distance_m=float(t.total_distance_m),
                camera_names=t.ordered_camera_names or [],
            )

        canonical_plate = alert.vehicle_identity.primary_plate if alert.vehicle_identity else None

        return AlertInvestigationResponse(
            alert_id=alert.id,
            alert_code=alert.alert_code,
            alert_type=alert.alert_type,
            severity=alert.severity,
            status=alert.status,
            confidence=float(alert.confidence),
            title=alert.title,
            description=alert.description,
            created_at=alert.created_at,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
            resolution_notes=alert.resolution_notes,
            vehicle_identity_id=alert.vehicle_identity_id,
            canonical_plate=canonical_plate,
            cameras_involved=cameras_involved,
            evidence=alert.evidence or {},
            trajectory_summary=traj_summary,
        )

    async def get_analytics_summary(self) -> DashboardAnalyticsSummaryResponse:
        """
        Produce unified analytics payload for Executive Dashboard visualizations.
        """
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        # 1. Total volume past 24h
        obs_count_q = (
            select(func.count())
            .select_from(VehicleObservation)
            .where(VehicleObservation.observed_at >= one_day_ago)
        )
        total_24h = (await self._session.execute(obs_count_q)).scalar_one()

        # 2. Hourly volume trend
        vol_resp = await self._analytics.get_traffic_volume(
            interval="1h", start_time=one_day_ago, end_time=now
        )
        hourly_trend = [
            {
                "bucket": b.timestamp_bucket.isoformat(),
                "total": b.total_volume,
                "classes": b.by_vehicle_class,
            }
            for b in vol_resp.buckets
        ]

        # 3. Congestion hotspots
        congest_report = await self._analytics.get_congestion_report()
        top_congested: list[CongestionHotspot] = []
        for pair in congest_report.segments:
            if pair.congestion_indicator > 1.1:
                sev = (
                    "severe"
                    if pair.congestion_indicator > 2.0
                    else "high"
                    if pair.congestion_indicator > 1.5
                    else "moderate"
                )
                top_congested.append(
                    CongestionHotspot(
                        corridor_name=f"{pair.source_camera_name} → {pair.destination_camera_name}",
                        source_camera_name=pair.source_camera_name or "Source",
                        destination_camera_name=pair.destination_camera_name or "Dest",
                        congestion_index=pair.congestion_indicator,
                        current_travel_time_s=pair.current_mean_travel_time_s,
                        baseline_travel_time_s=pair.baseline_travel_time_s,
                        severity=sev,
                    )
                )

        # 4. Top Routes & OD Flows
        routes_resp = await self._analytics.get_route_frequency(limit=5)
        top_routes = [r.model_dump() for r in routes_resp.routes]

        od_resp = await self._analytics.get_od_matrix(limit=5)
        top_od = [od.model_dump() for od in od_resp.matrix]

        return DashboardAnalyticsSummaryResponse(
            generated_at=now,
            total_vehicles_past_24h=total_24h,
            hourly_volume_trend=hourly_trend,
            top_congested_corridors=top_congested,
            top_frequent_routes=top_routes,
            top_od_flows=top_od,
        )
