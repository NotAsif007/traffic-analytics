"""Cross-camera vehicle association engine with explainable multi-signal reasoning."""

from __future__ import annotations

from app.association.contracts import (
    AssociationDecision,
    MatchSignalScores,
    ScoringThresholds,
    ScoringWeights,
    SightingContext,
)
from app.association.gating import CandidateGating
from app.association.scorer import AssociationScorer
from app.models.camera_connection import CameraConnection


class AssociationEngine:
    """
    Core intelligence engine for determining whether observations/tracks across
    cameras belong to the same physical vehicle identity.
    """

    def __init__(
        self,
        scorer: AssociationScorer | None = None,
        gating: CandidateGating | None = None,
        thresholds: ScoringThresholds | None = None,
        weights: ScoringWeights | None = None,
    ) -> None:
        self.scorer = scorer or AssociationScorer(weights=weights)
        self.gating = gating or CandidateGating()
        self.thresholds = thresholds or ScoringThresholds()
        self.weights = weights or ScoringWeights()

    def evaluate_pair(
        self,
        source: SightingContext,
        target: SightingContext,
        connection: CameraConnection | None = None,
    ) -> AssociationDecision:
        """
        Evaluate candidate association between a prior sighting and a new sighting.

        Returns an explainable AssociationDecision.
        """
        delta_seconds = (target.timestamp - source.timestamp).total_seconds()

        min_travel_s = connection.min_travel_time_s if connection else None
        max_travel_s = connection.max_travel_time_s if connection else None
        avg_travel_s = connection.avg_travel_time_s if connection else None
        has_direct_conn = connection is not None

        # 1. Compute multi-signal scores
        signals = self.scorer.compute_scores(
            src=source,
            tgt=target,
            delta_seconds=delta_seconds,
            has_direct_connection=has_direct_conn,
            min_travel_s=min_travel_s,
            max_travel_s=max_travel_s,
            avg_travel_s=avg_travel_s,
        )

        # 2. Compute composite score
        score = self.scorer.calculate_composite_score(signals, self.weights)

        # 3. Determine status
        if score >= self.thresholds.acceptance_threshold:
            status = "accepted"
            is_accepted = True
        elif score >= self.thresholds.review_threshold:
            status = "needs_review"
            is_accepted = False
        else:
            status = "rejected"
            is_accepted = False

        # 4. Generate structured reasoning for government/auditor explainability
        reasoning = self._build_reasoning(
            source=source,
            target=target,
            signals=signals,
            score=score,
            status=status,
            delta_seconds=delta_seconds,
            connection=connection,
        )

        return AssociationDecision(
            match_score=score,
            status=status,
            signals=signals,
            reasoning=reasoning,
            is_accepted=is_accepted,
        )

    def _build_reasoning(
        self,
        source: SightingContext,
        target: SightingContext,
        signals: MatchSignalScores,
        score: float,
        status: str,
        delta_seconds: float,
        connection: CameraConnection | None,
    ) -> str:
        """Construct human-readable explainability narrative."""
        parts: list[str] = []

        # Overall verdict
        parts.append(f"Association decision: {status.upper()} (composite score: {score:.2f}).")

        # Plate signal analysis
        if source.plate_text and target.plate_text:
            if source.plate_text == target.plate_text:
                parts.append(f"Exact license plate match '{source.plate_text}' (similarity: 1.00).")
            else:
                parts.append(
                    f"Plate reading '{source.plate_text}' ~ '{target.plate_text}' "
                    f"(plate similarity: {signals.plate_similarity:.2f})."
                )
        elif source.plate_text or target.plate_text:
            present_plate = source.plate_text or target.plate_text
            parts.append(
                f"Single readable plate reading '{present_plate}' with one unreadable observation "
                f"(neutral plate weight: {signals.plate_similarity:.2f})."
            )
        else:
            parts.append(
                "License plates unreadable on both sightings; association relies on temporal/appearance signals."
            )

        # Temporal & route analysis
        time_str = f"{delta_seconds:.0f}s"
        if connection:
            parts.append(
                f"Traveled {time_str} over connected road segment "
                f"(expected: {connection.min_travel_time_s}-{connection.max_travel_time_s}s, "
                f"temporal score: {signals.temporal_feasibility:.2f})."
            )
        else:
            parts.append(
                f"Elapsed time: {time_str} between camera sightings "
                f"(temporal feasibility: {signals.temporal_feasibility:.2f}, route: {signals.route_feasibility:.2f})."
            )

        # Vehicle attributes
        if source.vehicle_class and target.vehicle_class:
            if source.vehicle_class == target.vehicle_class:
                parts.append(f"Vehicle class matched ('{source.vehicle_class}').")
            else:
                parts.append(
                    f"Vehicle class variation: '{source.vehicle_class}' vs '{target.vehicle_class}'."
                )

        if (
            source.vehicle_color
            and target.vehicle_color
            and source.vehicle_color == target.vehicle_color
        ):
            parts.append(f"Color matched ('{source.vehicle_color}').")

        return " ".join(parts)
