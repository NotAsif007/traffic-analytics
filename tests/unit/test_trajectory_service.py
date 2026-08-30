"""Unit tests for TrajectoryService and timeline reconstruction."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.models.trajectory import Trajectory, TrajectoryPoint
from app.models.vehicle_observation import VehicleObservation
from app.services.trajectory import TrajectoryService

VID_ID = uuid.uuid4()
CAM_1_ID = uuid.uuid4()
CAM_3_ID = uuid.uuid4()
CAM_6_ID = uuid.uuid4()

T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def trajectory_service(mock_session: AsyncMock) -> TrajectoryService:
    return TrajectoryService(mock_session)


@pytest.fixture
def sample_camera_1() -> MagicMock:
    cam = MagicMock()
    cam.id = CAM_1_ID
    cam.name = "C01"
    return cam


@pytest.fixture
def sample_camera_3() -> MagicMock:
    cam = MagicMock()
    cam.id = CAM_3_ID
    cam.name = "C03"
    return cam


@pytest.fixture
def sample_camera_6() -> MagicMock:
    cam = MagicMock()
    cam.id = CAM_6_ID
    cam.name = "C06"
    return cam


def _make_obs(
    cam_id: uuid.UUID, timestamp: datetime, plate: str | None = "AS01AB1234"
) -> VehicleObservation:
    obs = MagicMock(spec=VehicleObservation)
    obs.id = uuid.uuid4()
    obs.camera_id = cam_id
    obs.observed_at = timestamp
    obs.detection_confidence = 0.95
    obs.plate_text = plate
    obs.plate_confidence = 0.92
    obs.estimated_speed_kmh = 45.0
    return obs


@pytest.mark.unit
async def test_start_trajectory(
    trajectory_service: TrajectoryService, sample_camera_1: MagicMock
) -> None:
    obs = _make_obs(CAM_1_ID, T0)
    with patch.object(trajectory_service._camera_repo, "get_by_id", return_value=sample_camera_1):
        traj = await trajectory_service.start_trajectory(VID_ID, obs)
        assert traj.vehicle_identity_id == VID_ID
        assert traj.start_time == T0
        assert traj.end_time == T0
        assert traj.points_count == 1
        assert traj.ordered_camera_names == ["C01"]


@pytest.mark.unit
async def test_append_observation_success(
    trajectory_service: TrajectoryService, sample_camera_3: MagicMock
) -> None:
    """Appending a sighting 5 minutes later to C03 increases duration and updates route."""
    t1 = T0 + timedelta(minutes=5)
    obs2 = _make_obs(CAM_3_ID, t1, plate="AS01AB1284")

    # Mock existing trajectory with 1 point
    pt1 = MagicMock(spec=TrajectoryPoint)
    pt1.sequence_order = 1
    pt1.camera_id = CAM_1_ID
    pt1.timestamp = T0

    traj = MagicMock(spec=Trajectory)
    traj.id = uuid.uuid4()
    traj.trajectory_id = "TRJ-001"
    traj.start_time = T0
    traj.end_time = T0
    traj.total_distance_m = 0.0
    traj.total_travel_time_s = 0
    traj.points_count = 1
    traj.ordered_camera_ids = [str(CAM_1_ID)]
    traj.ordered_camera_names = ["C01"]
    traj.points = [pt1]

    conn = MagicMock()
    conn.distance_m = 2500.0

    with (
        patch.object(trajectory_service._repo, "get_with_points", return_value=traj),
        patch.object(trajectory_service._camera_repo, "get_by_id", return_value=sample_camera_3),
        patch.object(trajectory_service._conn_repo, "get_by_camera_pair", return_value=conn),
    ):
        updated = await trajectory_service.append_observation(traj, obs2)
        assert updated.end_time == t1
        assert updated.total_travel_time_s == 300  # 5 minutes
        assert updated.total_distance_m == 2500.0
        assert updated.points_count == 2
        assert updated.ordered_camera_names == ["C01", "C03"]


@pytest.mark.unit
async def test_reject_impossible_time_transition(
    trajectory_service: TrajectoryService,
) -> None:
    """Cannot append an observation that occurred before the previous point."""
    pt1 = MagicMock(spec=TrajectoryPoint)
    pt1.sequence_order = 1
    pt1.camera_id = CAM_1_ID
    pt1.timestamp = T0

    traj = MagicMock(spec=Trajectory)
    traj.id = uuid.uuid4()
    traj.points = [pt1]

    # Earlier timestamp (time travel)
    earlier_obs = _make_obs(CAM_3_ID, T0 - timedelta(minutes=10))

    with patch.object(trajectory_service._repo, "get_with_points", return_value=traj):
        with pytest.raises(ValidationError, match="earlier than previous point"):
            await trajectory_service.append_observation(traj, earlier_obs)


@pytest.mark.unit
async def test_timeline_reconstruction_three_camera_progression(
    trajectory_service: TrajectoryService,
    sample_camera_1: MagicMock,
    sample_camera_3: MagicMock,
    sample_camera_6: MagicMock,
) -> None:
    """
    CRITICAL SPECIFICATION TEST:
    C01 (10:00) -> C03 (10:05) -> C06 (10:12)
    Produces Trajectory with route 'C01 -> C03 -> C06' and total travel time = 12 minutes.
    """
    t0 = T0
    t1 = T0 + timedelta(minutes=5)
    t2 = T0 + timedelta(minutes=12)

    p1 = MagicMock(spec=TrajectoryPoint)
    p1.sequence_order = 1
    p1.camera_id = CAM_1_ID
    p1.camera = sample_camera_1
    p1.timestamp = t0
    p1.plate_text = "AS01AB1234"
    p1.plate_confidence = 0.95
    p1.segment_distance_m = 0.0

    p2 = MagicMock(spec=TrajectoryPoint)
    p2.sequence_order = 2
    p2.camera_id = CAM_3_ID
    p2.camera = sample_camera_3
    p2.timestamp = t1
    p2.plate_text = "AS01AB1284"
    p2.plate_confidence = 0.89
    p2.segment_distance_m = 2500.0

    p3 = MagicMock(spec=TrajectoryPoint)
    p3.sequence_order = 3
    p3.camera_id = CAM_6_ID
    p3.camera = sample_camera_6
    p3.timestamp = t2
    p3.plate_text = None
    p3.plate_confidence = None
    p3.segment_distance_m = 3500.0

    traj = MagicMock(spec=Trajectory)
    traj.id = uuid.uuid4()
    traj.trajectory_id = "TRJ-20260830-0001"
    traj.vehicle_identity_id = VID_ID
    traj.start_time = t0
    traj.end_time = t2
    traj.total_travel_time_s = 720  # 12 minutes
    traj.total_distance_m = 6000.0  # 6.0 km
    traj.average_speed_kmh = 30.0
    traj.confidence = 0.88
    traj.status = "completed"
    traj.ordered_camera_names = ["C01", "C03", "C06"]
    traj.points = [p1, p2, p3]

    with (
        patch.object(trajectory_service._repo, "get_with_points", return_value=traj),
        patch.object(trajectory_service._conn_repo, "get_by_camera_pair", return_value=MagicMock()),
    ):
        timeline = await trajectory_service.get_timeline(traj.id)

        assert timeline.trajectory_id == "TRJ-20260830-0001"
        assert timeline.total_travel_time_seconds == 720
        assert "12 min" in timeline.total_travel_time_formatted
        assert timeline.total_distance_km == 6.0
        assert timeline.route_summary == "C01 -> C03 -> C06"
        assert len(timeline.segments) == 2

        # Segment 1: C01 -> C03 (5 mins, 2.5km)
        s1 = timeline.segments[0]
        assert s1.from_camera_name == "C01"
        assert s1.to_camera_name == "C03"
        assert s1.elapsed_seconds == 300.0
        assert s1.distance_meters == 2500.0

        # Segment 2: C03 -> C06 (7 mins, 3.5km)
        s2 = timeline.segments[1]
        assert s2.from_camera_name == "C03"
        assert s2.to_camera_name == "C06"
        assert s2.elapsed_seconds == 420.0
        assert s2.distance_meters == 3500.0
