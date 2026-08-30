"""BenchmarkRunner orchestrating full-system evaluation and report generation."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import get_logger
from app.evaluation.alert_eval import AlertEvaluator
from app.evaluation.anpr_eval import ANPREvaluator
from app.evaluation.association_eval import AssociationEvaluator
from app.evaluation.contracts import EvaluationReport
from app.evaluation.dataset import generate_synthetic_benchmark
from app.evaluation.tracking_eval import TrackingEvaluator

logger = get_logger(__name__)


class BenchmarkRunner:
    """
    Executes comprehensive, non-fabricated evaluation across all PS 26127 subsystems.
    """

    def __init__(self) -> None:
        self.anpr_eval = ANPREvaluator()
        self.tracking_eval = TrackingEvaluator()
        self.association_eval = AssociationEvaluator()
        self.alert_eval = AlertEvaluator()

    def run_benchmark(self) -> EvaluationReport:
        """
        Execute full benchmark suite against deterministic synthetic ground-truth dataset.
        """
        logger.info("benchmark.starting", benchmark="PS26127-City-Benchmark-v1")
        ds = generate_synthetic_benchmark()

        # 1. ANPR evaluation
        anpr_metrics = self.anpr_eval.evaluate(ds.all_observations)

        # 2. Tracking evaluation
        tracking_metrics = self.tracking_eval.evaluate(ds.all_observations)

        # 3. Cross-camera association evaluation
        association_metrics = self.association_eval.evaluate(ds.vehicles)

        # 4. Alert evaluation
        alert_metrics = self.alert_eval.evaluate(ds.all_observations, ds.blacklist_plates)

        # Overall composite system score (weighted average of core layer F1s)
        overall_score = round(
            (
                anpr_metrics.detection_f1 * 0.25
                + tracking_metrics.idf1 * 0.25
                + association_metrics.f1_score * 0.30
                + alert_metrics.f1_score * 0.20
            ),
            4,
        )

        dataset_summary = {
            "total_cameras": len(ds.cameras),
            "total_vehicles": len(ds.vehicles),
            "total_observations": len(ds.all_observations),
            "blacklisted_vehicles": len(ds.blacklist_plates),
            "total_anomalous_events": ds.total_anomalies,
        }

        report = EvaluationReport(
            benchmark_name="PS26127-City-Benchmark-v1",
            evaluation_timestamp=datetime.now(timezone.utc),
            dataset_summary=dataset_summary,
            anpr=anpr_metrics,
            tracking=tracking_metrics,
            association=association_metrics,
            alerts=alert_metrics,
            overall_system_score=overall_score,
        )

        logger.info("benchmark.completed", overall_score=overall_score)
        return report
