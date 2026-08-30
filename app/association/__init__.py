"""Cross-camera vehicle association package."""

from app.association.contracts import (
    AssociationDecision,
    MatchSignalScores,
    ScoringThresholds,
    ScoringWeights,
    SightingContext,
)
from app.association.engine import AssociationEngine
from app.association.gating import CandidateGating
from app.association.scorer import AssociationScorer

__all__ = [
    "AssociationDecision",
    "MatchSignalScores",
    "ScoringThresholds",
    "ScoringWeights",
    "SightingContext",
    "AssociationScorer",
    "CandidateGating",
    "AssociationEngine",
]
