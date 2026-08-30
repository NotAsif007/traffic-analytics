"""Unit tests for the AssociationEngine including synthetic scenarios and explainability."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.association.contracts import SightingContext
from app.association.engine import AssociationEngine

CAM_1 = uuid.uuid4()
CAM_2 = uuid.uuid4()
CAM_3 = uuid.uuid4()
CAM_6 = uuid.uuid4()

T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)


def _make_connection(
    src_cam: uuid.UUID, dst_cam: uuid.UUID, min_s: int = 60, max_s: int = 300, avg_s: int = 150
) -> MagicMock:
    conn = MagicMock()
    conn.source_camera_id = src_cam
    conn.destination_camera_id = dst_cam
    conn.min_travel_time_s = min_s
    conn.max_travel_time_s = max_s
    conn.avg_travel_time_s = avg_s
    return conn


@pytest.fixture
def engine() -> AssociationEngine:
    return AssociationEngine()


# ---------------------------------------------------------------------------
# Scenario 1: Exact Plate Match on Connected Road
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_exact_plate_match(engine: AssociationEngine) -> None:
    s1 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_1,
        timestamp=T0,
        plate_text="AS01AB1234",
        plate_confidence=0.96,
        vehicle_class="car",
        vehicle_color="white",
        direction="E",
    )
    s2 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_2,
        timestamp=T0 + timedelta(seconds=120),
        plate_text="AS01AB1234",
        plate_confidence=0.95,
        vehicle_class="car",
        vehicle_color="white",
        direction="E",
    )
    conn = _make_connection(CAM_1, CAM_2, min_s=60, max_s=240, avg_s=120)

    decision = engine.evaluate_pair(s1, s2, conn)
    assert decision.is_accepted is True
    assert decision.status == "accepted"
    assert decision.match_score >= 0.85
    assert "Exact license plate match" in decision.reasoning


# ---------------------------------------------------------------------------
# Scenario 2: One OCR Character Error (AS01AB1234 -> AS01AB1284)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_single_character_ocr_error(engine: AssociationEngine) -> None:
    s1 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_1,
        timestamp=T0,
        plate_text="AS01AB1234",
        plate_confidence=0.92,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )
    s2 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_3,
        timestamp=T0 + timedelta(minutes=5),  # 300s
        plate_text="AS01AB1284",  # 3 -> 8 substitution
        plate_confidence=0.90,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )
    conn = _make_connection(CAM_1, CAM_3, min_s=180, max_s=420, avg_s=300)

    decision = engine.evaluate_pair(s1, s2, conn)
    assert decision.is_accepted is True
    assert decision.status == "accepted"
    assert decision.match_score >= 0.75
    assert decision.signals.plate_similarity >= 0.85
    assert "AS01AB1234" in decision.reasoning


# ---------------------------------------------------------------------------
# Scenario 3: Missing / Unreadable Plate with Compatible Kinematics & Color
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_missing_plate_appearance_match(engine: AssociationEngine) -> None:
    s1 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_3,
        timestamp=T0 + timedelta(minutes=5),
        plate_text="AS01AB1284",
        plate_confidence=0.88,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )
    # Camera 6: Plate unreadable due to glare/rain, but same vehicle class/color
    s2 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_6,
        timestamp=T0 + timedelta(minutes=12),  # +7 mins (420s)
        plate_text=None,  # Unreadable plate
        plate_confidence=None,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )
    conn = _make_connection(CAM_3, CAM_6, min_s=300, max_s=600, avg_s=420)

    decision = engine.evaluate_pair(s1, s2, conn)
    # System should produce candidate or review/accepted score without hard error
    assert decision.match_score >= 0.60
    assert decision.status in ("accepted", "needs_review")
    assert "unreadable observation" in decision.reasoning


# ---------------------------------------------------------------------------
# Scenario 4: Different Vehicle with Similar Appearance (Plate Mismatch)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_different_vehicle_plate_mismatch(engine: AssociationEngine) -> None:
    s1 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_1,
        timestamp=T0,
        plate_text="AS01AB1234",
        plate_confidence=0.95,
        vehicle_class="car",
        vehicle_color="white",
    )
    s2 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_2,
        timestamp=T0 + timedelta(minutes=3),
        plate_text="DL04CD9999",  # Completely different vehicle
        plate_confidence=0.95,
        vehicle_class="car",
        vehicle_color="white",
    )
    conn = _make_connection(CAM_1, CAM_2, min_s=60, max_s=240)

    decision = engine.evaluate_pair(s1, s2, conn)
    assert decision.is_accepted is False
    assert decision.status in ("rejected", "needs_review")
    assert decision.signals.plate_similarity < 0.20


# ---------------------------------------------------------------------------
# Scenario 5: Impossible Travel Time (Speed Violation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_impossible_travel_time(engine: AssociationEngine) -> None:
    s1 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_1,
        timestamp=T0,
        plate_text="AS01AB1234",
        plate_confidence=0.95,
        vehicle_class="car",
    )
    # Target camera is 10km away (expected min travel 300s), but sighted in 3 seconds
    s2 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_2,
        timestamp=T0 + timedelta(seconds=3),  # Impossible 3s
        plate_text="AS01AB1234",
        plate_confidence=0.95,
        vehicle_class="car",
    )
    conn = _make_connection(CAM_1, CAM_2, min_s=300, max_s=900)

    decision = engine.evaluate_pair(s1, s2, conn)
    assert decision.is_accepted is False
    assert decision.signals.temporal_feasibility == 0.0
    assert decision.status == "rejected"


# ---------------------------------------------------------------------------
# Scenario 6: Incompatible Direction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scenario_opposing_direction(engine: AssociationEngine) -> None:
    s1 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_1,
        timestamp=T0,
        plate_text="AS01AB1234",
        direction="N",
    )
    s2 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_2,
        timestamp=T0 + timedelta(seconds=120),
        plate_text="AS01AB1234",
        direction="S",  # Opposing direction heading
    )
    conn = _make_connection(CAM_1, CAM_2, min_s=60, max_s=180)

    decision = engine.evaluate_pair(s1, s2, conn)
    assert decision.signals.direction_match == 0.2


# ---------------------------------------------------------------------------
# Critical Multi-Camera Chain Test: C01 (10:00) -> C03 (10:05) -> C06 (10:12)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_critical_multi_camera_association_chain(engine: AssociationEngine) -> None:
    """
    CRITICAL SPEC TEST:
    C01 (10:00): AS01AB1234 (Clear read, silver car)
    C03 (10:05): AS01AB1284 (Single OCR error 3->8, silver car)
    C06 (10:12): unreadable plate (silver car, plausible corridor travel)

    Validates that the association engine connects all 3 sightings into
    a single coherent trajectory hypothesis despite noisy and missing OCR.
    """
    s_c01 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_1,
        timestamp=T0,
        plate_text="AS01AB1234",
        plate_confidence=0.96,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )

    s_c03 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_3,
        timestamp=T0 + timedelta(minutes=5),
        plate_text="AS01AB1284",
        plate_confidence=0.89,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )

    s_c06 = SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=CAM_6,
        timestamp=T0 + timedelta(minutes=12),
        plate_text=None,  # Unreadable plate
        plate_confidence=None,
        vehicle_class="car",
        vehicle_color="silver",
        direction="E",
    )

    conn_1_3 = _make_connection(CAM_1, CAM_3, min_s=180, max_s=420, avg_s=300)
    conn_3_6 = _make_connection(CAM_3, CAM_6, min_s=300, max_s=600, avg_s=420)

    # Hop 1: C01 -> C03
    d1 = engine.evaluate_pair(s_c01, s_c03, conn_1_3)
    assert d1.is_accepted is True
    assert d1.match_score >= 0.75

    # Hop 2: C03 -> C06 (with unreadable plate at C06)
    d2 = engine.evaluate_pair(s_c03, s_c06, conn_3_6)
    assert d2.match_score >= 0.60
    assert d2.status in ("accepted", "needs_review")

    # Verify explainability narrative captures the progressive rationale
    assert "AS01AB1234" in d1.reasoning
    assert "unreadable observation" in d2.reasoning
