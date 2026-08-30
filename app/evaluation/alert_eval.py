"""Alert and anomaly detection evaluation metrics calculator."""

from __future__ import annotations

from collections.abc import Sequence

from app.anpr.matcher import PlateMatcher
from app.evaluation.contracts import AlertMetrics, GroundTruthObservation


class AlertEvaluator:
    """
    Evaluates alert precision, recall, and false positive rates.
    """

    def __init__(self) -> None:
        self.matcher = PlateMatcher()

    def evaluate(
        self,
        observations: Sequence[GroundTruthObservation],
        blacklist_plates: set[str],
    ) -> AlertMetrics:
        tp_alerts = 0
        fp_alerts = 0
        fn_alerts = 0
        tn_samples = 0

        for o in observations:
            is_anomaly_gt = o.is_blacklisted or o.is_speed_anomaly or o.is_route_anomaly

            # Blacklist check simulation
            flagged = False
            if o.simulated_ocr_plate:
                for bp in blacklist_plates:
                    comp = self.matcher.compare(o.simulated_ocr_plate, bp)
                    if comp.similarity_score >= 0.85:
                        flagged = True
                        break

            if o.is_speed_anomaly or o.is_route_anomaly:
                flagged = True

            if is_anomaly_gt and flagged:
                tp_alerts += 1
            elif not is_anomaly_gt and flagged:
                fp_alerts += 1
            elif is_anomaly_gt and not flagged:
                fn_alerts += 1
            else:
                tn_samples += 1

        total_alerts = tp_alerts + fp_alerts
        total_gt_anomalies = tp_alerts + fn_alerts

        precision = tp_alerts / max(1, total_alerts)
        recall = tp_alerts / max(1, total_gt_anomalies)
        f1 = (
            2 * (precision * recall) / max(1e-6, precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        fpr = fp_alerts / max(1, fp_alerts + tn_samples)

        return AlertMetrics(
            total_ground_truth_anomalies=total_gt_anomalies,
            total_alerts_generated=total_alerts,
            true_positive_alerts=tp_alerts,
            false_positive_alerts=fp_alerts,
            false_negative_alerts=fn_alerts,
            true_negative_samples=tn_samples,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            false_positive_rate=round(fpr, 4),
        )
