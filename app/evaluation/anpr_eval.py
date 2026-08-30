"""ANPR layer evaluation and benchmarking metrics calculator."""

from __future__ import annotations

from typing import Sequence

from app.anpr.matcher import levenshtein_distance
from app.anpr.normalizer import OCRNormalizer
from app.evaluation.contracts import ANPRMetrics, GroundTruthObservation


class ANPREvaluator:
    """
    Evaluates license plate detection and OCR recognition performance against ground truth.
    """

    def __init__(self) -> None:
        self.normalizer = OCRNormalizer()

    def evaluate(
        self,
        observations: Sequence[GroundTruthObservation],
    ) -> ANPRMetrics:
        total_gt = len(observations)
        detected_count = sum(1 for o in observations if o.simulated_ocr_plate is not None)
        tp_det = detected_count  # Detected true plates
        fp_det = 0
        fn_det = total_gt - detected_count  # Unreadable / missed plates

        precision_det = tp_det / max(1, tp_det + fp_det)
        recall_det = tp_det / max(1, total_gt)
        f1_det = (
            2 * (precision_det * recall_det) / max(1e-6, precision_det + recall_det)
            if (precision_det + recall_det) > 0
            else 0.0
        )

        exact_matches = 0
        normalized_matches = 0
        char_accuracies: list[float] = []
        confidences: list[float] = []

        for o in observations:
            gt_text = o.true_plate
            pred_text = o.simulated_ocr_plate

            if pred_text is not None:
                conf = o.simulated_ocr_confidence or 0.90
                confidences.append(conf)

                if pred_text == gt_text:
                    exact_matches += 1

                # Check normalized
                norm_gt = self.normalizer.normalize(gt_text, 1.0).normalized_text
                norm_pred = self.normalizer.normalize(pred_text, conf).normalized_text
                if norm_gt == norm_pred:
                    normalized_matches += 1

                # Character accuracy = 1 - (edit_dist / max_len)
                dist = levenshtein_distance(gt_text, pred_text)
                char_acc = max(0.0, 1.0 - (dist / max(len(gt_text), len(pred_text), 1)))
                char_accuracies.append(char_acc)
            else:
                char_accuracies.append(0.0)

        exact_acc = exact_matches / max(1, total_gt)
        norm_acc = normalized_matches / max(1, total_gt)
        avg_char_acc = sum(char_accuracies) / max(1, len(char_accuracies))
        mean_conf = sum(confidences) / max(1, len(confidences)) if confidences else 0.0

        return ANPRMetrics(
            total_ground_truth_plates=total_gt,
            total_detected_plates=detected_count,
            detection_true_positives=tp_det,
            detection_false_positives=fp_det,
            detection_false_negatives=fn_det,
            detection_precision=round(precision_det, 4),
            detection_recall=round(recall_det, 4),
            detection_f1=round(f1_det, 4),
            exact_plate_matches=exact_matches,
            exact_plate_accuracy=round(exact_acc, 4),
            normalized_plate_accuracy=round(norm_acc, 4),
            average_character_accuracy=round(avg_char_acc, 4),
            mean_ocr_confidence=round(mean_conf, 4),
        )
