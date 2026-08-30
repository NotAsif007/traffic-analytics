"""Unit tests for AssociationScorer signal computations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.association.contracts import ScoringWeights, SightingContext
from app.association.scorer import AssociationScorer


def _make_sighting(
    camera_id: uuid.UUID,
    timestamp: datetime,
    plate_text: str | None = None,
    plate_confidence: float | None = None,
    vehicle_class: str = "car",
    vehicle_color: str = "white",
    direction: str = "E",
    embedding_id: str | None = None,
) -> SightingContext:
    return SightingContext(
        sighting_id=uuid.uuid4(),
        camera_id=camera_id,
        timestamp=timestamp,
        plate_text=plate_text,
        plate_confidence=plate_confidence,
        vehicle_class=vehicle_class,
        vehicle_color=vehicle_color,
        direction=direction,
        embedding_id=embedding_id,
    )


CAM_1 = uuid.uuid4()
CAM_2 = uuid.uuid4()
T0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def scorer() -> AssociationScorer:
    return AssociationScorer()


@pytest.mark.unit
def test_scorer_exact_plate_match(scorer: AssociationScorer) -> None:
    s1 = _make_sighting(CAM_1, T0, plate_text="AS01AB1234", plate_confidence=0.95)
    s2 = _make_sighting(CAM_2, T0, plate_text="AS01AB1234", plate_confidence=0.95)

    score = scorer.evaluate_plate_signal(s1, s2)
    assert score >= 0.95


@pytest.mark.unit
def test_scorer_one_ocr_character_substitution(scorer: AssociationScorer) -> None:
    # AS01AB1234 vs AS01AB1284 (3 -> 8)
    s1 = _make_sighting(CAM_1, T0, plate_text="AS01AB1234", plate_confidence=0.90)
    s2 = _make_sighting(CAM_2, T0, plate_text="AS01AB1284", plate_confidence=0.90)

    score = scorer.evaluate_plate_signal(s1, s2)
    assert 0.80 <= score <= 0.95


@pytest.mark.unit
def test_scorer_missing_plate_neutral(scorer: AssociationScorer) -> None:
    s1 = _make_sighting(CAM_1, T0, plate_text="AS01AB1234", plate_confidence=0.90)
    s2 = _make_sighting(CAM_2, T0, plate_text=None, plate_confidence=None)

    score = scorer.evaluate_plate_signal(s1, s2)
    assert score == 0.5  # Neutral non-punitive score


@pytest.mark.unit
def test_scorer_temporal_impossible_speed(scorer: AssociationScorer) -> None:
    """Travel time is 2 seconds when minimum expected is 60 seconds (physically impossible)."""
    score = scorer.evaluate_temporal_signal(
        delta_seconds=2.0,
        min_travel_s=60,
        max_travel_s=180,
    )
    assert score == 0.0  # Impossible speed


@pytest.mark.unit
def test_scorer_temporal_optimal_window(scorer: AssociationScorer) -> None:
    """Travel time 90s perfectly matches expected window 60-180s."""
    score = scorer.evaluate_temporal_signal(
        delta_seconds=90.0,
        min_travel_s=60,
        max_travel_s=180,
        avg_travel_s=90,
    )
    assert score == 1.0


@pytest.mark.unit
def test_scorer_direction_opposing_penalty(scorer: AssociationScorer) -> None:
    s1 = _make_sighting(CAM_1, T0, direction="N")
    s2 = _make_sighting(CAM_2, T0, direction="S")

    score = scorer.evaluate_direction_signal(s1, s2)
    assert score == 0.2  # Incompatible opposite directions


@pytest.mark.unit
def test_scorer_hard_gating_class_mismatch(scorer: AssociationScorer) -> None:
    s1 = _make_sighting(CAM_1, T0, vehicle_class="motorcycle", plate_text="KA01AB1234")
    s2 = _make_sighting(CAM_2, T0, vehicle_class="truck", plate_text="KA01AB1234")

    signals = scorer.compute_scores(s1, s2, delta_seconds=60)
    composite = scorer.calculate_composite_score(signals)

    # Even with identical plate text, motorcycle vs truck is hard-capped at <= 0.30
    assert composite <= 0.30
