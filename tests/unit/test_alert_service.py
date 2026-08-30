"""Unit tests for AlertService: blacklist detection, anomaly generation, and lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import Alert, BlacklistEntry
from app.models.camera_connection import CameraConnection
from app.models.trajectory import Trajectory, TrajectoryPoint
from app.models.vehicle_observation import VehicleObservation
from app.schemas.alert import AlertActionRequest, BlacklistEntryCreate
from app.services.alert import AlertService

CAM_ID = uuid.uuid4()
T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def alert_service(mock_session: AsyncMock) -> AlertService:
    return AlertService(mock_session)


@pytest.fixture
def sample_blacklist_entry() -> BlacklistEntry:
    entry = MagicMock(spec=BlacklistEntry)
    entry.id = uuid.uuid4()
    entry.plate_text = "KA01AB1234"
    entry.reason = "Stolen vehicle bolo"
    entry.priority = "critical"
    entry.is_active = True
    entry.valid_from = None
    entry.valid_until = None
    entry.notes = None
    entry.metadata_ = None
    entry.created_at = T0
    entry.updated_at = T0
    return entry


@pytest.mark.unit
async def test_blacklist_match_exact_plate(
    alert_service: AlertService, sample_blacklist_entry: BlacklistEntry
) -> None:
    """Exact plate match triggers BLACKLIST_MATCH alert with evidence."""
    obs = MagicMock(spec=VehicleObservation)
    obs.id = uuid.uuid4()
    obs.camera_id = CAM_ID
    obs.observed_at = T0
    obs.plate_text = "KA01AB1234"
    obs.plate_confidence = 0.96

    with patch.object(
        alert_service._blacklist_repo, "find_active_entries", return_value=[sample_blacklist_entry]
    ):
        alert = await alert_service.check_observation_blacklist(obs)

        assert alert is not None
        assert alert.alert_type == "BLACKLIST_MATCH"
        assert alert.severity == "critical"
        assert alert.status == "NEW"
        assert alert.evidence["observed_plate"] == "KA01AB1234"
        assert alert.evidence["blacklist_plate"] == "KA01AB1234"
        assert alert.evidence["reason"] == "Stolen vehicle bolo"
        assert "Watchlist Plate Match" in alert.title


@pytest.mark.unit
async def test_blacklist_match_fuzzy_ocr_substitution(
    alert_service: AlertService, sample_blacklist_entry: BlacklistEntry
) -> None:
    """Plate with single character OCR substitution still flags with match confidence."""
    obs = MagicMock(spec=VehicleObservation)
    obs.id = uuid.uuid4()
    obs.camera_id = CAM_ID
    obs.observed_at = T0
    obs.plate_text = "KA01AB1284"  # 3 -> 8 substitution
    obs.plate_confidence = 0.90

    with patch.object(
        alert_service._blacklist_repo, "find_active_entries", return_value=[sample_blacklist_entry]
    ):
        alert = await alert_service.check_observation_blacklist(obs)

        assert alert is not None
        assert alert.alert_type == "BLACKLIST_MATCH"
        assert alert.evidence["match_similarity"] >= 0.85


@pytest.mark.unit
async def test_travel_time_speed_anomaly(
    alert_service: AlertService,
) -> None:
    """Transit of 5s on a road segment with 60s minimum triggers TRAVEL_TIME_ANOMALY."""
    traj = MagicMock(spec=Trajectory)
    traj.id = uuid.uuid4()
    traj.vehicle_identity_id = uuid.uuid4()

    p_from = MagicMock(spec=TrajectoryPoint)
    p_from.camera_id = uuid.uuid4()
    p_from.timestamp = T0

    p_to = MagicMock(spec=TrajectoryPoint)
    p_to.camera_id = CAM_ID
    p_to.timestamp = T0 + timedelta(seconds=5)  # 5s transit

    conn = MagicMock(spec=CameraConnection)
    conn.distance_m = 1000.0  # 1km in 5s = 720 km/h
    conn.min_travel_time_s = 60
    conn.max_travel_time_s = 180

    alert = await alert_service.check_travel_time_anomaly(traj, p_from, p_to, conn)

    assert alert is not None
    assert alert.alert_type == "TRAVEL_TIME_ANOMALY"
    assert alert.severity == "high"
    assert alert.evidence["actual_duration_seconds"] == 5.0
    assert alert.evidence["min_expected_seconds"] == 60
    assert "Travel Time Anomaly" in alert.title


@pytest.mark.unit
async def test_alert_lifecycle_workflow(
    alert_service: AlertService,
) -> None:
    """Test NEW -> ACKNOWLEDGED -> RESOLVED lifecycle transitions."""
    alert = MagicMock(spec=Alert)
    alert.id = uuid.uuid4()
    alert.alert_code = "ALT-001"
    alert.alert_type = "BLACKLIST_MATCH"
    alert.severity = "high"
    alert.status = "NEW"
    alert.confidence = 0.95
    alert.title = "Test"
    alert.description = "Test desc"
    alert.camera_id = None
    alert.camera = None
    alert.vehicle_identity_id = None
    alert.trajectory_id = None
    alert.observation_id = None
    alert.blacklist_entry_id = None
    alert.evidence = {}
    alert.acknowledged_at = None
    alert.acknowledged_by = None
    alert.resolved_at = None
    alert.resolved_by = None
    alert.dismissed_at = None
    alert.dismissed_by = None
    alert.resolution_notes = None
    alert.metadata_ = None
    alert.created_at = T0
    alert.updated_at = T0

    with patch.object(alert_service._alert_repo, "get_by_id", return_value=alert):
        ack = await alert_service.acknowledge_alert(
            alert.id, AlertActionRequest(action_by="officer_1", notes="Dispatching patrol")
        )
        assert alert.status == "ACKNOWLEDGED"
        assert alert.acknowledged_by == "officer_1"

        res = await alert_service.resolve_alert(
            alert.id, AlertActionRequest(action_by="officer_1", notes="Vehicle intercepted")
        )
        assert alert.status == "RESOLVED"
        assert alert.resolved_by == "officer_1"
