"""Unit tests for plate matching and similarity algorithms."""

from __future__ import annotations

import pytest

from app.anpr.matcher import (
    PlateMatcher,
    is_partial_match,
    levenshtein_distance,
    levenshtein_similarity,
    propagate_observation_confidence,
)

# ---------------------------------------------------------------------------
# Algorithm unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_levenshtein_distance() -> None:
    assert levenshtein_distance("AS01AB1234", "AS01AB1234") == 0
    assert levenshtein_distance("AS01AB1234", "AS01AB1284") == 1  # 3 -> 8
    assert levenshtein_distance("AS01AB1234", "AS01AB123") == 1  # missing '4'
    assert levenshtein_distance("AS01AB1234", "MH12CD5678") == 10


@pytest.mark.unit
def test_levenshtein_similarity() -> None:
    assert levenshtein_similarity("AS01AB1234", "AS01AB1234") == 1.0
    # 1 edit over 10 chars = 0.9 similarity
    sim_sub = levenshtein_similarity("AS01AB1234", "AS01AB1284")
    assert sim_sub == 0.9

    # 1 deletion over 10 chars = 0.9 similarity
    sim_trunc = levenshtein_similarity("AS01AB1234", "AS01AB123")
    assert sim_trunc == 0.9


@pytest.mark.unit
def test_partial_match_logic() -> None:
    assert is_partial_match("AS01AB1234", "AS01AB123", min_overlap=5) is True
    assert is_partial_match("KA01", "KA01AB1234", min_overlap=4) is True
    assert is_partial_match("KA01", "MH12", min_overlap=4) is False
    assert is_partial_match("KA", "KA01AB1234", min_overlap=4) is False  # below min_overlap


# ---------------------------------------------------------------------------
# Realistic Plate Matcher Test Cases
# ---------------------------------------------------------------------------


@pytest.fixture
def matcher() -> PlateMatcher:
    return PlateMatcher()


@pytest.mark.unit
def test_exact_match(matcher: PlateMatcher) -> None:
    """AS01AB1234 vs AS01AB1234 -> exact match."""
    res = matcher.compare("AS01AB1234", "AS01AB1234")
    assert res.is_exact_match is True
    assert res.is_normalized_match is True
    assert res.similarity_score == 1.0
    assert res.match_type == "exact"
    assert res.edit_distance == 0


@pytest.mark.unit
def test_normalized_match(matcher: PlateMatcher) -> None:
    """AS 01-AB.1234 vs as01ab1234 -> normalized match."""
    res = matcher.compare("AS 01-AB.1234", "as01ab1234")
    assert res.is_exact_match is False
    assert res.is_normalized_match is True
    assert res.similarity_score == 1.0
    assert res.match_type == "normalized"
    assert res.edit_distance == 0


@pytest.mark.unit
def test_single_character_substitution(matcher: PlateMatcher) -> None:
    """AS01AB1234 vs AS01AB1284 -> high similarity (score=0.90, dist=1)."""
    res = matcher.compare("AS01AB1234", "AS01AB1284")
    assert res.is_exact_match is False
    assert res.is_normalized_match is False
    assert res.similarity_score == 0.90
    assert res.edit_distance == 1
    assert res.match_type == "high_similarity"


@pytest.mark.unit
def test_truncated_plate_match(matcher: PlateMatcher) -> None:
    """AS01AB1234 vs AS01AB123 -> high similarity & partial match."""
    res = matcher.compare("AS01AB1234", "AS01AB123")
    assert res.is_exact_match is False
    assert res.is_partial_match is True
    assert res.similarity_score == 0.90
    assert res.edit_distance == 1
    assert res.match_type == "high_similarity"


@pytest.mark.unit
def test_complete_mismatch(matcher: PlateMatcher) -> None:
    """AS01AB1234 vs MH02ZZ9999 -> mismatch."""
    res = matcher.compare("AS01AB1234", "MH02ZZ9999")
    assert res.is_exact_match is False
    assert res.is_normalized_match is False
    assert res.is_partial_match is False
    assert res.similarity_score < 0.50
    assert res.match_type == "mismatch"


# ---------------------------------------------------------------------------
# Confidence Propagation Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_propagate_observation_confidence_both_signals() -> None:
    # (0.90 * 0.3) + (0.95 * 0.7) = 0.27 + 0.665 = 0.935
    eff = propagate_observation_confidence(detection_confidence=0.90, plate_confidence=0.95)
    assert eff == 0.935


@pytest.mark.unit
def test_propagate_observation_confidence_missing_plate() -> None:
    # 0.90 * 0.8 = 0.72
    eff = propagate_observation_confidence(detection_confidence=0.90, plate_confidence=None)
    assert eff == 0.72


@pytest.mark.unit
def test_propagate_observation_confidence_zero_signals() -> None:
    eff = propagate_observation_confidence(detection_confidence=None, plate_confidence=None)
    assert eff == 0.0
