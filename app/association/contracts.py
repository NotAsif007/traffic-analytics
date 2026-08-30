"""Association engine data contracts, scoring configurations, and explainability schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import AppBaseModel


class ScoringWeights(AppBaseModel):
    """
    Configurable signal weights for cross-camera association scoring.

    Weights are automatically normalized to sum to 1.0 during scoring.
    """

    plate_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    appearance_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    temporal_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    route_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    direction_weight: float = Field(default=0.08, ge=0.0, le=1.0)
    class_weight: float = Field(default=0.05, ge=0.0, le=1.0)
    color_weight: float = Field(default=0.02, ge=0.0, le=1.0)


class ScoringThresholds(AppBaseModel):
    """Thresholds determining association status decisions."""

    acceptance_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    review_threshold: float = Field(default=0.55, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> ScoringThresholds:
        if self.review_threshold > self.acceptance_threshold:
            raise ValueError("review_threshold must be <= acceptance_threshold")
        return self


class MatchSignalScores(AppBaseModel):
    """
    Detailed breakdown of individual signal scores for full explainability.
    All scores in range [0.0, 1.0].
    """

    plate_similarity: float = Field(..., ge=0.0, le=1.0)
    appearance_similarity: float = Field(..., ge=0.0, le=1.0)
    temporal_feasibility: float = Field(..., ge=0.0, le=1.0)
    route_feasibility: float = Field(..., ge=0.0, le=1.0)
    direction_match: float = Field(..., ge=0.0, le=1.0)
    class_match: float = Field(..., ge=0.0, le=1.0)
    color_match: float = Field(..., ge=0.0, le=1.0)


class AssociationDecision(AppBaseModel):
    """
    Final decision and explainability payload for an association candidate.
    """

    match_score: float = Field(..., ge=0.0, le=1.0)
    status: str = Field(..., description="candidate | accepted | rejected | needs_review")
    signals: MatchSignalScores
    reasoning: str = Field(..., description="Human-readable justification for government auditing")
    is_accepted: bool


class SightingContext(AppBaseModel):
    """
    Unified representation of a camera sighting (from observation or track).
    """

    sighting_id: uuid.UUID
    is_track: bool = False
    camera_id: uuid.UUID
    timestamp: datetime
    plate_text: str | None = None
    plate_confidence: float | None = None
    vehicle_class: str | None = None
    vehicle_color: str | None = None
    direction: str | None = None
    speed_kmh: float | None = None
    embedding_id: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
