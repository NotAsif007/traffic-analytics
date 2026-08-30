"""Cross-camera association and trajectory accuracy evaluator."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.association.contracts import SightingContext
from app.association.engine import AssociationEngine
from app.evaluation.contracts import AssociationMetrics, GroundTruthVehicle


class AssociationEvaluator:
    """
    Evaluates multi-camera association engine precision, recall, and trajectory completeness.
    """

    def __init__(self) -> None:
        self.engine = AssociationEngine()

    def evaluate(
        self,
        gt_vehicles: Sequence[GroundTruthVehicle],
    ) -> AssociationMetrics:
        total_gt_vehicles = len(gt_vehicles)

        correct_associations_tp = 0
        false_associations_fp = 0
        missed_associations_fn = 0
        complete_trajectories = 0

        # Run pairwise progressive evaluation along each vehicle's route
        for veh in gt_vehicles:
            obs_list = veh.observations
            if len(obs_list) < 2:
                complete_trajectories += 1
                continue

            veh_fully_connected = True
            for i in range(1, len(obs_list)):
                o_prev = obs_list[i - 1]
                o_curr = obs_list[i]

                s_prev = SightingContext(
                    sighting_id=uuid.uuid4(),
                    camera_id=o_prev.camera_id,
                    timestamp=o_prev.timestamp,
                    plate_text=o_prev.simulated_ocr_plate,
                    plate_confidence=o_prev.simulated_ocr_confidence,
                    vehicle_class=o_prev.true_class,
                    vehicle_color=o_prev.true_color,
                )
                s_curr = SightingContext(
                    sighting_id=uuid.uuid4(),
                    camera_id=o_curr.camera_id,
                    timestamp=o_curr.timestamp,
                    plate_text=o_curr.simulated_ocr_plate,
                    plate_confidence=o_curr.simulated_ocr_confidence,
                    vehicle_class=o_curr.true_class,
                    vehicle_color=o_curr.true_color,
                )

                decision = self.engine.evaluate_pair(s_prev, s_curr)
                if decision.is_accepted or decision.status == "needs_review":
                    correct_associations_tp += 1
                else:
                    missed_associations_fn += 1
                    veh_fully_connected = False

            if veh_fully_connected:
                complete_trajectories += 1

        # Evaluate negative cross-vehicle pairs (different vehicles should NOT be associated)
        for i in range(len(gt_vehicles) - 1):
            v1 = gt_vehicles[i]
            v2 = gt_vehicles[i + 1]

            s1 = SightingContext(
                sighting_id=uuid.uuid4(),
                camera_id=v1.observations[0].camera_id,
                timestamp=v1.observations[0].timestamp,
                plate_text=v1.observations[0].simulated_ocr_plate,
                plate_confidence=v1.observations[0].simulated_ocr_confidence,
                vehicle_class=v1.vehicle_class,
                vehicle_color=v1.vehicle_color,
            )
            s2 = SightingContext(
                sighting_id=uuid.uuid4(),
                camera_id=v2.observations[0].camera_id,
                timestamp=v2.observations[0].timestamp,
                plate_text=v2.observations[0].simulated_ocr_plate,
                plate_confidence=v2.observations[0].simulated_ocr_confidence,
                vehicle_class=v2.vehicle_class,
                vehicle_color=v2.vehicle_color,
            )
            decision = self.engine.evaluate_pair(s1, s2)
            if decision.is_accepted:
                false_associations_fp += 1

        precision = correct_associations_tp / max(
            1, correct_associations_tp + false_associations_fp
        )
        recall = correct_associations_tp / max(1, correct_associations_tp + missed_associations_fn)
        f1 = (
            2 * (precision * recall) / max(1e-6, precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        traj_rate = complete_trajectories / max(1, total_gt_vehicles)

        return AssociationMetrics(
            total_ground_truth_vehicles=total_gt_vehicles,
            total_predicted_identities=total_gt_vehicles + missed_associations_fn,
            correct_associations_tp=correct_associations_tp,
            false_associations_fp=false_associations_fp,
            missed_associations_fn=missed_associations_fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            trajectory_completeness_rate=round(traj_rate, 4),
        )
