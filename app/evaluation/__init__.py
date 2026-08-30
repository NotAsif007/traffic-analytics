"""Evaluation and benchmarking subsystem."""

from app.evaluation.alert_eval import AlertEvaluator
from app.evaluation.anpr_eval import ANPREvaluator
from app.evaluation.association_eval import AssociationEvaluator
from app.evaluation.contracts import (
    AlertMetrics,
    ANPRMetrics,
    AssociationMetrics,
    EvaluationReport,
    GroundTruthObservation,
    GroundTruthVehicle,
    TrackingMetrics,
)
from app.evaluation.dataset import generate_synthetic_benchmark
from app.evaluation.runner import BenchmarkRunner
from app.evaluation.tracking_eval import TrackingEvaluator

__all__ = [
    "GroundTruthObservation",
    "GroundTruthVehicle",
    "ANPRMetrics",
    "TrackingMetrics",
    "AssociationMetrics",
    "AlertMetrics",
    "EvaluationReport",
    "ANPREvaluator",
    "TrackingEvaluator",
    "AssociationEvaluator",
    "AlertEvaluator",
    "generate_synthetic_benchmark",
    "BenchmarkRunner",
]
