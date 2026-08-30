"""Multi-signal scoring functions for cross-camera vehicle association."""

from __future__ import annotations

import math

from app.anpr.matcher import PlateMatcher
from app.association.contracts import MatchSignalScores, ScoringWeights, SightingContext


class AssociationScorer:
    """
    Evaluates association signals between two vehicle sightings across cameras.
    """

    def __init__(
        self,
        plate_matcher: PlateMatcher | None = None,
        weights: ScoringWeights | None = None,
    ) -> None:
        self.plate_matcher = plate_matcher or PlateMatcher()
        self.weights = weights or ScoringWeights()

    def evaluate_plate_signal(
        self,
        src: SightingContext,
        tgt: SightingContext,
    ) -> float:
        """
        Evaluate plate similarity score in [0.0, 1.0].
        If one or both plates are missing/unreadable, returns a non-zero neutral fallback (0.5).
        """
        if not src.plate_text or not tgt.plate_text:
            # Unreadable / missing plate is not a hard rejection, just neutral
            return 0.5

        comp = self.plate_matcher.compare(src.plate_text, tgt.plate_text)
        raw_sim = comp.similarity_score

        # Weight by OCR confidence if available
        src_conf = src.plate_confidence if src.plate_confidence is not None else 0.8
        tgt_conf = tgt.plate_confidence if tgt.plate_confidence is not None else 0.8
        avg_conf = (src_conf + tgt_conf) / 2.0

        # High confidence OCR elevates similarity; low confidence OCR softens penalties
        if raw_sim >= 0.85:
            # e.g. AS01AB1234 vs AS01AB1284 -> 0.90 * 0.95
            return round(raw_sim * (0.8 + 0.2 * avg_conf), 4)
        else:
            return round(raw_sim, 4)

    def evaluate_appearance_signal(
        self,
        src: SightingContext,
        tgt: SightingContext,
    ) -> float:
        """Evaluate visual appearance and re-ID embedding compatibility."""
        if src.embedding_id and tgt.embedding_id and src.embedding_id == tgt.embedding_id:
            return 1.0

        # Fallback to color and class compatibility
        color_score = self.evaluate_color_signal(src, tgt)
        class_score = self.evaluate_class_signal(src, tgt)
        return round((color_score * 0.5) + (class_score * 0.5), 4)

    def evaluate_temporal_signal(
        self,
        delta_seconds: float,
        min_travel_s: int | None = None,
        max_travel_s: int | None = None,
        avg_travel_s: int | None = None,
    ) -> float:
        """
        Evaluate temporal plausibility of movement from source to target camera.
        """
        if delta_seconds < 0:
            # Time travel is physically impossible
            return 0.0

        if min_travel_s is not None and max_travel_s is not None:
            if delta_seconds < min_travel_s:
                # Vehicle appeared impossibly fast (exceeded physical speed limit)
                # Severe exponential penalty
                ratio = delta_seconds / max(1, min_travel_s)
                return round(max(0.0, ratio**3), 4)

            if min_travel_s <= delta_seconds <= max_travel_s:
                # Perfectly plausible window
                target_avg = avg_travel_s or ((min_travel_s + max_travel_s) / 2.0)
                deviation = abs(delta_seconds - target_avg)
                window_size = max_travel_s - min_travel_s
                if window_size > 0:
                    score = 1.0 - 0.2 * (deviation / window_size)
                    return round(min(1.0, max(0.8, score)), 4)
                return 1.0

            # delta_seconds > max_travel_s: gradual decay
            excess = delta_seconds - max_travel_s
            decay = math.exp(-excess / 300.0)  # 5-minute half-life decay
            return round(max(0.1, 0.8 * decay), 4)

        # No road connection bounds: assume general speed limit ~80km/h
        # 10s to 30min is generally plausible for urban sightings
        if 5 <= delta_seconds <= 1800:
            return 0.8
        elif delta_seconds < 5:
            return 0.1
        else:
            return 0.4

    def evaluate_route_signal(
        self,
        has_direct_connection: bool,
        is_same_camera: bool = False,
    ) -> float:
        """Evaluate topological route feasibility."""
        if is_same_camera:
            return 1.0
        if has_direct_connection:
            return 1.0
        # Multi-hop / indirect path
        return 0.75

    def evaluate_direction_signal(
        self,
        src: SightingContext,
        tgt: SightingContext,
    ) -> float:
        """Evaluate direction heading compatibility."""
        if not src.direction or not tgt.direction:
            return 0.8  # Neutral when direction not reported

        if src.direction.upper() == tgt.direction.upper():
            return 1.0

        # Incompatible opposing directions (e.g. N vs S on a linear corridor)
        opposing = {("N", "S"), ("S", "N"), ("E", "W"), ("W", "E")}
        if (src.direction.upper(), tgt.direction.upper()) in opposing:
            return 0.2

        return 0.6

    def evaluate_class_signal(
        self,
        src: SightingContext,
        tgt: SightingContext,
    ) -> float:
        """Evaluate vehicle classification compatibility."""
        if not src.vehicle_class or not tgt.vehicle_class:
            return 0.7  # Neutral

        c1 = src.vehicle_class.lower()
        c2 = tgt.vehicle_class.lower()

        if c1 == c2:
            return 1.0

        # Sub-type compatibilities
        similar_groups = [
            {"car", "van", "suv"},
            {"truck", "heavy_vehicle"},
            {"motorcycle", "scooter", "bicycle"},
        ]
        for group in similar_groups:
            if c1 in group and c2 in group:
                return 0.7

        return 0.0

    def evaluate_color_signal(
        self,
        src: SightingContext,
        tgt: SightingContext,
    ) -> float:
        """Evaluate vehicle color compatibility."""
        if not src.vehicle_color or not tgt.vehicle_color:
            return 0.7  # Neutral

        if src.vehicle_color.lower() == tgt.vehicle_color.lower():
            return 1.0
        return 0.1

    def compute_scores(
        self,
        src: SightingContext,
        tgt: SightingContext,
        delta_seconds: float,
        has_direct_connection: bool = False,
        min_travel_s: int | None = None,
        max_travel_s: int | None = None,
        avg_travel_s: int | None = None,
    ) -> MatchSignalScores:
        """Compute all signal scores between two sightings."""
        is_same_cam = src.camera_id == tgt.camera_id

        return MatchSignalScores(
            plate_similarity=self.evaluate_plate_signal(src, tgt),
            appearance_similarity=self.evaluate_appearance_signal(src, tgt),
            temporal_feasibility=self.evaluate_temporal_signal(
                delta_seconds, min_travel_s, max_travel_s, avg_travel_s
            ),
            route_feasibility=self.evaluate_route_signal(has_direct_connection, is_same_cam),
            direction_match=self.evaluate_direction_signal(src, tgt),
            class_match=self.evaluate_class_signal(src, tgt),
            color_match=self.evaluate_color_signal(src, tgt),
        )

    def calculate_composite_score(
        self,
        signals: MatchSignalScores,
        weights: ScoringWeights | None = None,
    ) -> float:
        """
        Calculate weighted composite match score in [0.0, 1.0].
        """
        w = weights or self.weights

        total_weight = (
            w.plate_weight
            + w.appearance_weight
            + w.temporal_weight
            + w.route_weight
            + w.direction_weight
            + w.class_weight
            + w.color_weight
        )
        if total_weight <= 0:
            return 0.0

        raw_score = (
            signals.plate_similarity * w.plate_weight
            + signals.appearance_similarity * w.appearance_weight
            + signals.temporal_feasibility * w.temporal_weight
            + signals.route_feasibility * w.route_weight
            + signals.direction_match * w.direction_weight
            + signals.class_match * w.class_weight
            + signals.color_match * w.color_weight
        ) / total_weight

        # Hard gating: if temporal feasibility is 0.0 (impossible speed), cap score
        if signals.temporal_feasibility == 0.0:
            raw_score = min(raw_score, 0.20)

        # Hard gating: if class match is 0.0 (e.g. motorcycle vs truck), cap score
        if signals.class_match == 0.0:
            raw_score = min(raw_score, 0.30)

        return round(min(1.0, max(0.0, raw_score)), 4)
