"""Unit tests for AnalyticsService calculations and metric formulas."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.trajectory import Trajectory
from app.models.vehicle_observation import VehicleObservation
from app.services.analytics import AnalyticsService

CAM_1 = uuid.uuid4()
CAM_2 = uuid.uuid4()
CAM_3 = uuid.uuid4()

T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=1)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def analytics_service(mock_session: AsyncMock) -> AnalyticsService:
    return AnalyticsService(mock_session)


def _make_obs(
    cam_id: uuid.UUID, ts: datetime, v_class: str = "car", speed: float = 40.0
) -> VehicleObservation:
    obs = MagicMock(spec=VehicleObservation)
    obs.id = uuid.uuid4()
    obs.camera_id = cam_id
    obs.observed_at = ts
    obs.vehicle_class = v_class
    obs.estimated_speed_kmh = speed
    return obs


@pytest.mark.unit
async def test_get_traffic_volume(
    analytics_service: AnalyticsService, mock_session: AsyncMock
) -> None:
    """Test volume aggregation across time buckets with vehicle class breakdowns."""
    obs_list = [
        _make_obs(CAM_1, T0 + timedelta(minutes=5), "car"),
        _make_obs(CAM_1, T0 + timedelta(minutes=15), "truck"),
        _make_obs(CAM_1, T0 + timedelta(minutes=25), "car"),
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = obs_list
    mock_session.execute.return_value = mock_result

    resp = await analytics_service.get_traffic_volume(
        start_time=T0, end_time=T1, interval="1h", camera_id=CAM_1
    )

    assert resp.total_vehicles == 3
    assert resp.interval == "1h"
    assert len(resp.buckets) == 1
    assert resp.buckets[0].vehicle_count == 3
    assert resp.buckets[0].vehicle_class_counts["car"] == 2
    assert resp.buckets[0].vehicle_class_counts["truck"] == 1


@pytest.mark.unit
async def test_get_vehicle_class_distribution(
    analytics_service: AnalyticsService, mock_session: AsyncMock
) -> None:
    """Test vehicle class distribution percentage calculation."""
    r1 = MagicMock()
    r1.vehicle_class = "car"
    r1.class_count = 80

    r2 = MagicMock()
    r2.vehicle_class = "bus"
    r2.class_count = 20

    mock_result = MagicMock()
    mock_result.all.return_value = [r1, r2]
    mock_session.execute.return_value = mock_result

    resp = await analytics_service.get_vehicle_class_distribution(start_time=T0, end_time=T1)

    assert resp.total_classified_vehicles == 100
    assert len(resp.distribution) == 2
    car_dist = next(d for d in resp.distribution if d.vehicle_class == "car")
    assert car_dist.percentage == 80.0
    bus_dist = next(d for d in resp.distribution if d.vehicle_class == "bus")
    assert bus_dist.percentage == 20.0


@pytest.mark.unit
async def test_get_traffic_density_fundamental_formula(
    analytics_service: AnalyticsService, mock_session: AsyncMock
) -> None:
    """
    Test density calculation:
    60 vehicles in 1 hour -> q = 60 veh/h.
    Speeds: all 40 km/h -> v_s = 40 km/h.
    Density k = 60 / 40 = 1.5 veh/km.
    """
    obs_list = [_make_obs(CAM_1, T0 + timedelta(minutes=i), speed=40.0) for i in range(60)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = obs_list
    mock_session.execute.return_value = mock_result

    mock_cam = MagicMock()
    mock_cam.name = "C01"
    mock_session.get.return_value = mock_cam

    resp = await analytics_service.get_traffic_density(start_time=T0, end_time=T1, camera_id=CAM_1)

    assert resp.flow_rate_veh_per_hour == 60.0
    assert resp.space_mean_speed_kmh == 40.0
    assert resp.density_veh_per_km == 1.5
    assert resp.density_level == "low"
    assert resp.camera_name == "C01"
    assert "k = q / v_s" in resp.methodology


@pytest.mark.unit
async def test_get_od_matrix_calculation(
    analytics_service: AnalyticsService, mock_session: AsyncMock
) -> None:
    """Test Origin-Destination matrix counts and averages from trajectories."""
    t1 = MagicMock(spec=Trajectory)
    t1.ordered_camera_ids = [CAM_1, CAM_2]
    t1.ordered_camera_names = ["C01", "C02"]
    t1.total_travel_time_s = 300
    t1.total_distance_m = 2500.0
    t1.points_count = 2

    t2 = MagicMock(spec=Trajectory)
    t2.ordered_camera_ids = [CAM_1, CAM_2]
    t2.ordered_camera_names = ["C01", "C02"]
    t2.total_travel_time_s = 360
    t2.total_distance_m = 2500.0
    t2.points_count = 2

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [t1, t2]
    mock_session.execute.return_value = mock_result

    resp = await analytics_service.get_od_matrix(start_time=T0, end_time=T1)

    assert resp.total_trips == 2
    assert len(resp.matrix) == 1
    cell = resp.matrix[0]
    assert cell.origin_camera_id == CAM_1
    assert cell.destination_camera_id == CAM_2
    assert cell.trip_count == 2
    assert cell.average_duration_seconds == 330.0
    assert cell.average_distance_meters == 2500.0


@pytest.mark.unit
async def test_get_route_frequency(
    analytics_service: AnalyticsService, mock_session: AsyncMock
) -> None:
    """Test top route frequency ranking."""
    t1 = MagicMock(spec=Trajectory)
    t1.ordered_camera_names = ["C01", "C03", "C06"]
    t1.total_travel_time_s = 720
    t1.total_distance_m = 6000.0

    t2 = MagicMock(spec=Trajectory)
    t2.ordered_camera_names = ["C01", "C03", "C06"]
    t2.total_travel_time_s = 700
    t2.total_distance_m = 6000.0

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [t1, t2]
    mock_session.execute.return_value = mock_result

    resp = await analytics_service.get_route_frequency(start_time=T0, end_time=T1, limit=5)

    assert resp.total_trips_analyzed == 2
    assert len(resp.top_routes) == 1
    top = resp.top_routes[0]
    assert top.route_summary == "C01 -> C03 -> C06"
    assert top.trip_count == 2
    assert top.percentage == 100.0
    assert top.average_distance_km == 6.0
