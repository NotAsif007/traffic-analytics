"""Unit tests for DashboardService: city overview, live map, investigation, and analytics summary."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import Alert
from app.models.camera import Camera
from app.models.road import Road
from app.models.vehicle_identity import VehicleIdentity
from app.models.vehicle_observation import VehicleObservation
from app.schemas.analytics import CongestionReportResponse
from app.schemas.dashboard import (
    AlertInvestigationResponse,
    CityOverviewResponse,
    LiveMapResponse,
    VehicleInvestigationResponse,
)
from app.services.dashboard import DashboardService

T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
CAM_ID = uuid.uuid4()
IDENTITY_ID = uuid.uuid4()
ALERT_ID = uuid.uuid4()


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    return session


@pytest.fixture
def dashboard_service(mock_session: AsyncMock) -> DashboardService:
    return DashboardService(mock_session)


@pytest.mark.unit
async def test_get_city_overview(dashboard_service: DashboardService) -> None:
    """City overview aggregates active camera count, observation count, traffic level, and hotspots."""
    cam1 = MagicMock(spec=Camera)
    cam1.id = CAM_ID
    cam1.status = "active"

    mock_cameras_result = MagicMock()
    mock_cameras_result.scalars().all.return_value = [cam1]

    mock_scalar_result = MagicMock()
    mock_scalar_result.scalar_one.return_value = 150

    mock_alerts_result = MagicMock()
    mock_alerts_result.scalars().all.return_value = []

    dashboard_service._session.execute = AsyncMock(
        side_effect=[mock_cameras_result, mock_scalar_result, mock_alerts_result]
    )

    with patch.object(
        dashboard_service._analytics,
        "get_congestion_report",
        return_value=CongestionReportResponse(
            timestamp=T0,
            summary_congestion_index=1.05,
            overall_status="free_flow",
            segments=[],
        ),
    ):
        overview = await dashboard_service.get_city_overview()

        assert isinstance(overview, CityOverviewResponse)
        assert overview.total_cameras_count == 1
        assert overview.active_cameras_count == 1
        assert overview.cameras_online_percentage == 100.0
        assert overview.vehicles_observed_today == 150
        assert overview.current_traffic_level == "moderate"


@pytest.mark.unit
async def test_get_live_map(dashboard_service: DashboardService) -> None:
    """Live map returns cameras, road network, active trajectories, and alert markers."""
    cam1 = MagicMock(spec=Camera)
    cam1.id = CAM_ID
    cam1.name = "C01"
    cam1.status = "active"
    cam1.location = MagicMock()
    cam1.location.coordinates = [77.5946, 12.9716]

    road1 = MagicMock(spec=Road)
    road1.id = uuid.uuid4()
    road1.name = "MG Road"
    road1.geometry = MagicMock()
    road1.geometry.model_dump.return_value = {
        "type": "LineString",
        "coordinates": [[77.59, 12.97], [77.60, 12.98]],
    }

    mock_cams_res = MagicMock()
    mock_cams_res.scalars().all.return_value = [cam1]

    mock_cnt_res = MagicMock()
    mock_cnt_res.scalar_one.return_value = 25

    mock_last_res = MagicMock()
    mock_last_res.scalar_one.return_value = T0

    mock_roads_res = MagicMock()
    mock_roads_res.scalars().all.return_value = [road1]

    mock_trajs_res = MagicMock()
    mock_trajs_res.scalars().all.return_value = []

    mock_alerts_res = MagicMock()
    mock_alerts_res.scalars().all.return_value = []

    dashboard_service._session.execute = AsyncMock(
        side_effect=[
            mock_cams_res,
            mock_cnt_res,
            mock_last_res,
            mock_roads_res,
            mock_trajs_res,
            mock_alerts_res,
        ]
    )

    live_map = await dashboard_service.get_live_map()

    assert isinstance(live_map, LiveMapResponse)
    assert len(live_map.cameras) == 1
    assert live_map.cameras[0].name == "C01"
    assert live_map.cameras[0].latitude == 12.9716
    assert len(live_map.road_segments) == 1


@pytest.mark.unit
async def test_investigate_vehicle(dashboard_service: DashboardService) -> None:
    """Vehicle investigation returns forensic timeline and plate observation evidence."""
    identity = MagicMock(spec=VehicleIdentity)
    identity.id = IDENTITY_ID
    identity.primary_plate = "KA01AB1234"
    identity.vehicle_class = "car"
    identity.vehicle_color = "white"
    identity.confidence = 0.95
    identity.first_seen_at = T0
    identity.last_seen_at = T0
    identity.total_sightings = 1

    obs = MagicMock(spec=VehicleObservation)
    obs.id = uuid.uuid4()
    obs.camera_id = CAM_ID
    obs.observed_at = T0
    obs.plate_text = "KA01AB1234"
    obs.plate_confidence = 0.95
    obs.detection_confidence = 0.98
    obs.vehicle_class = "car"
    obs.vehicle_color = "white"
    obs.frame_path = "s3://bucket/frames/obs1.jpg"
    obs.plate_crop_path = "s3://bucket/crops/plate1.jpg"
    obs.estimated_speed_kmh = 45.0

    mock_id_res = MagicMock()
    mock_id_res.scalar_one_or_none.return_value = identity

    mock_matches_res = MagicMock()
    mock_matches_res.scalars().all.return_value = []

    mock_obs_res = MagicMock()
    mock_obs_res.scalars().all.return_value = [obs]

    mock_alerts_res = MagicMock()
    mock_alerts_res.scalars().all.return_value = []

    dashboard_service._session.execute = AsyncMock(
        side_effect=[mock_id_res, mock_matches_res, mock_obs_res, mock_alerts_res]
    )

    cam = MagicMock(spec=Camera)
    cam.name = "C01"
    cam.location = MagicMock()
    cam.location.coordinates = [77.5946, 12.9716]
    dashboard_service._session.get = AsyncMock(return_value=cam)

    inv = await dashboard_service.investigate_vehicle(IDENTITY_ID)

    assert isinstance(inv, VehicleInvestigationResponse)
    assert inv.canonical_plate == "KA01AB1234"
    assert len(inv.camera_history) == 1
    assert inv.camera_history[0].camera_name == "C01"
    assert len(inv.plate_observations) == 1
    assert inv.plate_observations[0].image_path == "s3://bucket/frames/obs1.jpg"


@pytest.mark.unit
async def test_investigate_alert(dashboard_service: DashboardService) -> None:
    """Alert investigation returns explainable evidence and cameras involved."""
    alert = MagicMock(spec=Alert)
    alert.id = ALERT_ID
    alert.alert_code = "ALT-001"
    alert.alert_type = "BLACKLIST_MATCH"
    alert.severity = "critical"
    alert.status = "NEW"
    alert.confidence = 0.98
    alert.title = "Watchlist Plate Match"
    alert.description = "Matched stolen vehicle"
    alert.created_at = T0
    alert.acknowledged_at = None
    alert.acknowledged_by = None
    alert.resolved_at = None
    alert.resolved_by = None
    alert.resolution_notes = None
    alert.vehicle_identity_id = IDENTITY_ID
    alert.evidence = {"observed_plate": "KA01ST9999", "match_confidence": 1.0}
    alert.trajectory = None

    cam = MagicMock(spec=Camera)
    cam.id = CAM_ID
    cam.name = "C01"
    cam.direction = "NORTH"
    cam.location = MagicMock()
    cam.location.coordinates = [77.5946, 12.9716]
    alert.camera = cam

    veh_id = MagicMock(spec=VehicleIdentity)
    veh_id.primary_plate = "KA01ST9999"
    alert.vehicle_identity = veh_id

    mock_alert_res = MagicMock()
    mock_alert_res.scalar_one_or_none.return_value = alert

    dashboard_service._session.execute = AsyncMock(return_value=mock_alert_res)

    inv = await dashboard_service.investigate_alert(ALERT_ID)

    assert isinstance(inv, AlertInvestigationResponse)
    assert inv.alert_code == "ALT-001"
    assert inv.canonical_plate == "KA01ST9999"
    assert len(inv.cameras_involved) == 1
    assert inv.cameras_involved[0].name == "C01"
    assert inv.evidence["observed_plate"] == "KA01ST9999"
