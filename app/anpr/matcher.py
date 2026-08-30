"""Plate comparison and similarity metrics for trajectory association preparation.

Provides pure comparison algorithms without prematurely mutating or creating
cross-camera vehicle identities.
"""

from __future__ import annotations

from pydantic import Field

from app.anpr.normalizer import OCRNormalizer
from app.schemas.common import AppBaseModel

# ---------------------------------------------------------------------------
# Similarity Results
# ---------------------------------------------------------------------------


class PlateMatchResult(AppBaseModel):
    """
    Detailed outcome of comparing two license plate strings.
    """

    plate_a: str
    plate_b: str
    is_exact_match: bool
    is_normalized_match: bool
    is_partial_match: bool
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Overall similarity score in [0.0, 1.0]"
    )
    edit_distance: int = Field(..., ge=0, description="Levenshtein distance")
    match_type: str = Field(
        ..., description="exact | normalized | high_similarity | partial | mismatch"
    )
    details: str | None = None


# ---------------------------------------------------------------------------
# Comparison Functions
# ---------------------------------------------------------------------------


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the minimum edit distance between two strings."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0, v1 = v1, v0

    return v0[len(s2)]


def levenshtein_similarity(s1: str, s2: str) -> float:
    """
    Normalized Levenshtein similarity score in [0.0, 1.0].
    1.0 = identical; 0.0 = completely dissimilar.
    """
    if s1 == s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return round(max(0.0, 1.0 - (dist / max_len)), 4)


def is_partial_match(s1: str, s2: str, min_overlap: int = 4) -> bool:
    """
    Check if one plate is a contiguous substring/prefix/suffix of the other
    with at least min_overlap characters.
    """
    if len(s1) < min_overlap or len(s2) < min_overlap:
        return False
    return (s1 in s2) or (s2 in s1)


def propagate_observation_confidence(
    detection_confidence: float | None,
    plate_confidence: float | None,
    ocr_quality_weight: float = 0.7,
) -> float:
    """
    Calculate an effective observation confidence score combining
    vehicle detector confidence and plate OCR confidence.

    Formula:
    If both exist: (detection_conf * (1 - w)) + (plate_conf * w)
    If only detection exists: detection_conf * 0.8 (penalty for missing plate)
    If only plate exists: plate_conf * 0.9
    If neither: 0.0
    """
    det_conf = detection_confidence if detection_confidence is not None else None
    plt_conf = plate_confidence if plate_confidence is not None else None

    if det_conf is not None and plt_conf is not None:
        effective = (det_conf * (1.0 - ocr_quality_weight)) + (plt_conf * ocr_quality_weight)
        return round(min(1.0, max(0.0, effective)), 4)
    elif det_conf is not None:
        return round(det_conf * 0.8, 4)
    elif plt_conf is not None:
        return round(plt_conf * 0.9, 4)
    return 0.0


# ---------------------------------------------------------------------------
# High-Level Plate Matcher
# ---------------------------------------------------------------------------


class PlateMatcher:
    """
    Evaluator for comparing license plate strings across observations.
    """

    def __init__(
        self,
        normalizer: OCRNormalizer | None = None,
        high_similarity_threshold: float = 0.85,
        min_partial_overlap: int = 5,
    ) -> None:
        self.normalizer = normalizer or OCRNormalizer()
        self.high_similarity_threshold = high_similarity_threshold
        self.min_partial_overlap = min_partial_overlap

    def compare(
        self,
        plate_a: str,
        plate_b: str,
    ) -> PlateMatchResult:
        """
        Perform a comprehensive comparison between two license plate strings.
        """
        # 1. Exact raw match
        if plate_a == plate_b:
            return PlateMatchResult(
                plate_a=plate_a,
                plate_b=plate_b,
                is_exact_match=True,
                is_normalized_match=True,
                is_partial_match=True,
                similarity_score=1.0,
                edit_distance=0,
                match_type="exact",
                details="Exact raw string match",
            )

        # 2. Normalized match
        norm_a = self.normalizer.normalize(plate_a, confidence=1.0).normalized_text
        norm_b = self.normalizer.normalize(plate_b, confidence=1.0).normalized_text

        if norm_a == norm_b:
            return PlateMatchResult(
                plate_a=plate_a,
                plate_b=plate_b,
                is_exact_match=False,
                is_normalized_match=True,
                is_partial_match=True,
                similarity_score=1.0,
                edit_distance=0,
                match_type="normalized",
                details="Identical after separator and case normalization",
            )

        # 3. String similarity on normalized strings
        dist = levenshtein_distance(norm_a, norm_b)
        sim = levenshtein_similarity(norm_a, norm_b)
        partial = is_partial_match(norm_a, norm_b, min_overlap=self.min_partial_overlap)

        if sim >= self.high_similarity_threshold:
            match_type = "high_similarity"
            details = f"High similarity (score={sim:.2f}, distance={dist})"
        elif partial:
            match_type = "partial"
            details = f"Partial substring match (score={sim:.2f})"
        else:
            match_type = "mismatch"
            details = f"Plate mismatch (score={sim:.2f}, distance={dist})"

        return PlateMatchResult(
            plate_a=plate_a,
            plate_b=plate_b,
            is_exact_match=False,
            is_normalized_match=False,
            is_partial_match=partial,
            similarity_score=sim,
            edit_distance=dist,
            match_type=match_type,
            details=details,
        )
