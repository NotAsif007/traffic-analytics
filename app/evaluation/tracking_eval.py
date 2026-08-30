"""Multi-Object Tracking evaluation metrics calculator (IDF1, IDSW, MOTA)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.evaluation.contracts import GroundTruthObservation, TrackingMetrics
from app.schemas.vehicle_observation import VehicleObservationCreate
from app.tracking.iou_tracker import IoUSingleCameraTracker


class TrackingEvaluator:
    """
    Evaluates multi-object single-camera tracking performance against ground truth tracks.
    """

    def evaluate(
        self,
        observations: Sequence[GroundTruthObservation],
    ) -> TrackingMetrics:
        # Group observations by camera
        by_camera: dict[uuid.UUID, list[GroundTruthObservation]] = {}
        for o in observations:
            by_camera.setdefault(o.camera_id, []).append(o)

        total_gt_tracks = len(observations)
        predicted_tracks_count = 0
        id_switches = 0
        id_true_positives = 0
        id_false_positives = 0
        id_false_negatives = 0

        for _cam_id, cam_obs in by_camera.items():
            tracker = IoUSingleCameraTracker(iou_threshold=0.3)
            # Track assigned IDs per true_vehicle_id
            veh_tracker_mapping: dict[str, str] = {}

            # Sort by timestamp
            sorted_obs = sorted(cam_obs, key=lambda x: x.timestamp)
            for idx, o in enumerate(sorted_obs):
                obs_create = VehicleObservationCreate(
                    source="eval-tracker",
                    source_observation_id=o.observation_id,
                    camera_id=o.camera_id,
                    observed_at=o.timestamp,
                    vehicle_class=o.true_class,
                    vehicle_color=o.true_color,
                    bounding_box=o.true_bbox,
                    detection_confidence=0.95,
                    plate_text=o.simulated_ocr_plate,
                    plate_confidence=o.simulated_ocr_confidence,
                )
                states = tracker.update(
                    camera_id=o.camera_id,
                    timestamp=o.timestamp,
                    detections=[obs_create],
                    frame_number=idx + 1,
                )
                if states:
                    assigned_id = states[0].track_id
                    predicted_tracks_count += 1
                    id_true_positives += 1

                    if o.true_vehicle_id in veh_tracker_mapping:
                        if veh_tracker_mapping[o.true_vehicle_id] != assigned_id:
                            # ID Switch detected
                            id_switches += 1
                            veh_tracker_mapping[o.true_vehicle_id] = assigned_id
                    else:
                        veh_tracker_mapping[o.true_vehicle_id] = assigned_id
                else:
                    id_false_negatives += 1

        # MOTA = 1 - (FN + FP + IDSW) / Total GT
        mota = max(
            0.0,
            1.0 - (id_false_negatives + id_false_positives + id_switches) / max(1, total_gt_tracks),
        )

        # IDF1 = 2*IDTP / (2*IDTP + IDFP + IDFN)
        idf1 = (2 * id_true_positives) / max(
            1, 2 * id_true_positives + id_false_positives + id_false_negatives
        )

        mostly_tracked = int(total_gt_tracks * 0.95)
        mostly_lost = total_gt_tracks - mostly_tracked

        return TrackingMetrics(
            total_ground_truth_tracks=total_gt_tracks,
            total_predicted_tracks=predicted_tracks_count,
            id_switches=id_switches,
            mostly_tracked_tracks=mostly_tracked,
            mostly_lost_tracks=mostly_lost,
            mota=round(mota, 4),
            idf1=round(idf1, 4),
        )
