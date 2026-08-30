"""Unit tests for single-camera vehicle tracking algorithms and state transitions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.vehicle_observation import BoundingBox, VehicleObservationCreate
from app.tracking.contracts import calculate_iou
from app.tracking.iou_tracker import IoUSingleCameraTracker

CAMERA_A = uuid.uuid4()
CAMERA_B = uuid.uuid4()


def _make_obs(
    camera_id: uuid.UUID,
    timestamp: datetime,
    bbox: BoundingBox,
    vehicle_class: str = "car",
    plate_text: str | None = None,
    plate_confidence: float | None = None,
    detection_confidence: float = 0.95,
) -> VehicleObservationCreate:
    return VehicleObservationCreate(
        source="tracker-test",
        source_observation_id=f"obs-{uuid.uuid4()}",
        camera_id=camera_id,
        observed_at=timestamp,
        vehicle_class=vehicle_class,
        bounding_box=bbox,
        detection_confidence=detection_confidence,
        plate_text=plate_text,
        plate_confidence=plate_confidence,
    )


@pytest.mark.unit
def test_calculate_iou_identical_boxes() -> None:
    box = BoundingBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5)
    assert calculate_iou(box, box) == 1.0


@pytest.mark.unit
def test_calculate_iou_no_overlap() -> None:
    box1 = BoundingBox(x1=0.1, y1=0.1, x2=0.3, y2=0.3)
    box2 = BoundingBox(x1=0.6, y1=0.6, x2=0.9, y2=0.9)
    assert calculate_iou(box1, box2) == 0.0


@pytest.mark.unit
def test_calculate_iou_partial_overlap() -> None:
    box1 = BoundingBox(x1=0.0, y1=0.0, x2=0.4, y2=0.4)
    box2 = BoundingBox(x1=0.2, y1=0.2, x2=0.6, y2=0.6)
    # intersection: 0.2*0.2 = 0.04
    # union: 0.16 + 0.16 - 0.04 = 0.28
    # iou: 0.04 / 0.28 = 0.1429
    assert calculate_iou(box1, box2) == 0.1429


@pytest.mark.unit
def test_track_creation_single_vehicle() -> None:
    """Frame 1 detection initializes a single active track."""
    tracker = IoUSingleCameraTracker(iou_threshold=0.3)
    t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

    det = _make_obs(CAMERA_A, t0, BoundingBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4), plate_text="KA01AB1234")
    tracks = tracker.update(CAMERA_A, t0, [det], frame_number=1)

    assert len(tracks) == 1
    track = tracks[0]
    assert track.status == "active"
    assert track.camera_id == CAMERA_A
    assert track.hits == 1
    assert track.best_plate_text == "KA01AB1234"
    assert len(track.points) == 1
    assert track.points[0].timestamp == t0


@pytest.mark.unit
def test_track_update_consecutive_frames() -> None:
    """Frame 1 -> Frame 2 with overlapping bbox updates the existing track."""
    tracker = IoUSingleCameraTracker(iou_threshold=0.3)
    t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)

    det1 = _make_obs(CAMERA_A, t0, BoundingBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4), plate_text="KA01", plate_confidence=0.70)
    det2 = _make_obs(CAMERA_A, t1, BoundingBox(x1=0.12, y1=0.12, x2=0.42, y2=0.42), plate_text="KA01AB1234", plate_confidence=0.95)

    tracker.update(CAMERA_A, t0, [det1], frame_number=1)
    tracks = tracker.update(CAMERA_A, t1, [det2], frame_number=2)

    assert len(tracks) == 1
    track = tracks[0]
    assert track.hits == 2
    assert track.start_time == t0
    assert track.last_seen == t1
    assert len(track.points) == 2
    # Best plate upgraded to higher confidence read
    assert track.best_plate_text == "KA01AB1234"
    assert track.best_plate_confidence == 0.95


@pytest.mark.unit
def test_multiple_simultaneous_vehicles() -> None:
    """Two vehicles moving in the same frame maintain distinct track IDs."""
    tracker = IoUSingleCameraTracker(iou_threshold=0.3)
    t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=1)

    # Vehicle 1 on left lane, Vehicle 2 on right lane
    v1_f1 = _make_obs(CAMERA_A, t0, BoundingBox(x1=0.1, y1=0.2, x2=0.3, y2=0.5), vehicle_class="car")
    v2_f1 = _make_obs(CAMERA_A, t0, BoundingBox(x1=0.6, y1=0.2, x2=0.8, y2=0.5), vehicle_class="truck")

    v1_f2 = _make_obs(CAMERA_A, t1, BoundingBox(x1=0.12, y1=0.22, x2=0.32, y2=0.52), vehicle_class="car")
    v2_f2 = _make_obs(CAMERA_A, t1, BoundingBox(x1=0.62, y1=0.22, x2=0.82, y2=0.52), vehicle_class="truck")

    tracks_f1 = tracker.update(CAMERA_A, t0, [v1_f1, v2_f1], frame_number=1)
    assert len(tracks_f1) == 2
    ids_f1 = {t.track_id for t in tracks_f1}

    tracks_f2 = tracker.update(CAMERA_A, t1, [v1_f2, v2_f2], frame_number=2)
    assert len(tracks_f2) == 2
    ids_f2 = {t.track_id for t in tracks_f2}

    # Track IDs should be preserved
    assert ids_f1 == ids_f2


@pytest.mark.unit
def test_missing_observation_and_termination() -> None:
    """When a vehicle is missing for > max_lost_frames, the track terminates."""
    tracker = IoUSingleCameraTracker(iou_threshold=0.3, max_lost_frames=2)
    t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

    # Frame 1: Detection
    det = _make_obs(CAMERA_A, t0, BoundingBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4))
    tracker.update(CAMERA_A, t0, [det], frame_number=1)

    # Frame 2: Missing (lost frame 1)
    tracks_f2 = tracker.update(CAMERA_A, t0 + timedelta(seconds=1), [], frame_number=2)
    assert len(tracks_f2) == 1
    assert tracks_f2[0].status == "lost"

    # Frame 3: Missing (lost frame 2)
    tracks_f3 = tracker.update(CAMERA_A, t0 + timedelta(seconds=2), [], frame_number=3)
    assert len(tracks_f3) == 1
    assert tracks_f3[0].status == "lost"

    # Frame 4: Missing (lost frame 3 > max_lost_frames=2) -> Terminated
    tracker.update(CAMERA_A, t0 + timedelta(seconds=3), [], frame_number=4)
    active = tracker.get_active_tracks(CAMERA_A)
    assert len(active) == 0  # No longer in active list
