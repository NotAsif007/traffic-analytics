"""Unit tests for Evaluation & Benchmarking subsystem."""

from __future__ import annotations

import pytest

from app.evaluation.alert_eval import AlertEvaluator
from app.evaluation.anpr_eval import ANPREvaluator
from app.evaluation.association_eval import AssociationEvaluator
from app.evaluation.dataset import generate_synthetic_benchmark
from app.evaluation.runner import BenchmarkRunner
from app.evaluation.tracking_eval import TrackingEvaluator


@pytest.mark.unit
def test_synthetic_benchmark_dataset_generation() -> None:
    """Benchmark dataset generates expected entities and ground-truth structures."""
    ds = generate_synthetic_benchmark()

    assert len(ds.cameras) == 8
    assert len(ds.vehicles) == 35
    assert len(ds.all_observations) >= 100
    assert len(ds.blacklist_plates) == 3
    assert ds.total_anomalies >= 5

    # Check vehicle 1 is blacklisted
    v1 = ds.vehicles[0]
    assert v1.is_blacklisted is True
    assert v1.plate in ds.blacklist_plates


@pytest.mark.unit
def test_anpr_evaluator_metrics() -> None:
    """ANPREvaluator produces valid precision, recall, and character accuracy numbers."""
    ds = generate_synthetic_benchmark()
    evaluator = ANPREvaluator()
    metrics = evaluator.evaluate(ds.all_observations)

    assert metrics.total_ground_truth_plates == len(ds.all_observations)
    assert 0.0 <= metrics.detection_precision <= 1.0
    assert 0.0 <= metrics.detection_recall <= 1.0
    assert 0.0 <= metrics.detection_f1 <= 1.0
    assert 0.0 <= metrics.exact_plate_accuracy <= 1.0
    assert 0.0 <= metrics.average_character_accuracy <= 1.0
    assert metrics.detection_recall > 0.90  # Benchmark has 4 unreadable plates out of 128


@pytest.mark.unit
def test_tracking_evaluator_metrics() -> None:
    """TrackingEvaluator computes MOTA and IDF1."""
    ds = generate_synthetic_benchmark()
    evaluator = TrackingEvaluator()
    metrics = evaluator.evaluate(ds.all_observations)

    assert metrics.total_ground_truth_tracks == len(ds.all_observations)
    assert 0.0 <= metrics.idf1 <= 1.0
    assert 0.0 <= metrics.mota <= 1.0
    assert metrics.id_switches >= 0


@pytest.mark.unit
def test_association_evaluator_metrics() -> None:
    """AssociationEvaluator computes precision, recall, and trajectory completeness rate."""
    ds = generate_synthetic_benchmark()
    evaluator = AssociationEvaluator()
    metrics = evaluator.evaluate(ds.vehicles)

    assert metrics.total_ground_truth_vehicles == 35
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1_score <= 1.0
    assert 0.0 <= metrics.trajectory_completeness_rate <= 1.0


@pytest.mark.unit
def test_alert_evaluator_metrics() -> None:
    """AlertEvaluator computes alert precision, recall, and false positive rate."""
    ds = generate_synthetic_benchmark()
    evaluator = AlertEvaluator()
    metrics = evaluator.evaluate(ds.all_observations, ds.blacklist_plates)

    assert metrics.total_ground_truth_anomalies > 0
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1_score <= 1.0
    assert 0.0 <= metrics.false_positive_rate <= 1.0


@pytest.mark.unit
def test_benchmark_runner_full_report() -> None:
    """BenchmarkRunner produces a complete machine-readable EvaluationReport."""
    runner = BenchmarkRunner()
    report = runner.run_benchmark()

    assert report.benchmark_name == "PS26127-City-Benchmark-v1"
    assert report.dataset_summary["total_cameras"] == 8
    assert report.dataset_summary["total_vehicles"] == 35
    assert 0.0 <= report.overall_system_score <= 1.0
    assert report.anpr.detection_f1 > 0.90
    assert report.tracking.idf1 > 0.90
    assert report.association.f1_score > 0.90
    assert report.alerts.f1_score > 0.90
