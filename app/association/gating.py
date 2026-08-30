"""Candidate generation and spatio-temporal gating for association."""

from __future__ import annotations

import uuid
from datetime import timedelta

from app.association.contracts import SightingContext


class CandidateGating:
    """
    Filters and prunes candidate pairs before performing full multi-signal scoring.
    Prevents O(N^2) pairwise comparisons.
    """

    def __init__(
        self,
        max_time_window_minutes: int = 60,
        min_time_delta_seconds: float = 0.0,
    ) -> None:
        self.max_time_window = timedelta(minutes=max_time_window_minutes)
        self.min_time_delta_seconds = min_time_delta_seconds

    def is_plausible_candidate(
        self,
        source: SightingContext,
        target: SightingContext,
        connected_camera_ids: set[uuid.UUID] | None = None,
    ) -> bool:
        """
        Check if target sighting is a plausible candidate given the source sighting.
        """
        # Time delta must be forward in time
        delta = (target.timestamp - source.timestamp).total_seconds()
        if delta < self.min_time_delta_seconds:
            return False

        if target.timestamp - source.timestamp > self.max_time_window:
            return False

        # Class mismatch hard filter (e.g. bicycle cannot match truck)
        if source.vehicle_class and target.vehicle_class:
            c1 = source.vehicle_class.lower()
            c2 = target.vehicle_class.lower()
            if (c1 in {"motorcycle", "bicycle"} and c2 in {"truck", "bus", "heavy_vehicle"}) or (
                c2 in {"motorcycle", "bicycle"} and c1 in {"truck", "bus", "heavy_vehicle"}
            ):
                return False

        # If camera topology filter is supplied: target camera should be reachable
        if connected_camera_ids is not None and (
            target.camera_id not in connected_camera_ids and target.camera_id != source.camera_id
        ):
            # If plate text is identical, allow candidate even if indirect topology
            return bool(
                source.plate_text and target.plate_text and source.plate_text == target.plate_text
            )

        return True
