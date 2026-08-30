"""Built-in spatial IoU-based single-camera multi-vehicle tracker."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from app.schemas.vehicle_observation import VehicleObservationCreate
from app.tracking.contracts import TrackPointData, TrackState, calculate_iou
from app.tracking.interfaces import SingleCameraTracker


class IoUSingleCameraTracker(SingleCameraTracker):
    """
    Spatial IoU tracker for continuous vehicle tracking across consecutive video frames.

    Features:
    - Greedy / Hungarian-style IoU bipartite association.
    - Automatic track lifecycle: Active -> Lost -> Terminated.
    - Aggregates best license plate read across all track points.
    - Handles multiple simultaneous vehicles.
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_lost_frames: int = 5,
        min_hits: int = 1,
    ) -> None:
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.min_hits = min_hits
        # State: camera_id -> list of TrackState
        self._tracks: dict[uuid.UUID, list[TrackState]] = {}
        self._next_track_number: int = 1

    def _generate_track_id(self, camera_id: uuid.UUID) -> str:
        tid = f"TRK-{str(camera_id)[:8]}-{self._next_track_number:04d}"
        self._next_track_number += 1
        return tid

    def update(
        self,
        camera_id: uuid.UUID,
        timestamp: datetime,
        detections: list[VehicleObservationCreate],
        frame_number: Optional[int] = None,
    ) -> list[TrackState]:
        if camera_id not in self._tracks:
            self._tracks[camera_id] = []

        active_tracks = [t for t in self._tracks[camera_id] if t.status in ("active", "lost")]

        # Match existing active tracks to new detections via IoU
        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()

        if active_tracks and detections:
            # Build IoU matrix
            iou_matrix: list[list[float]] = []
            for t in active_tracks:
                row = []
                for d in detections:
                    if d.bounding_box and t.bbox:
                        row.append(calculate_iou(t.bbox, d.bounding_box))
                    else:
                        row.append(0.0)
                iou_matrix.append(row)

            # Greedy matching sorted by highest IoU
            pairs: list[tuple[float, int, int]] = []
            for t_idx in range(len(active_tracks)):
                for d_idx in range(len(detections)):
                    score = iou_matrix[t_idx][d_idx]
                    if score >= self.iou_threshold:
                        pairs.append((score, t_idx, d_idx))

            pairs.sort(key=lambda x: x[0], reverse=True)

            for score, t_idx, d_idx in pairs:
                if t_idx not in matched_tracks and d_idx not in matched_detections:
                    matched_tracks.add(t_idx)
                    matched_detections.add(d_idx)
                    self._update_track(active_tracks[t_idx], detections[d_idx], timestamp, frame_number)

        # Handle unmatched active tracks (increment lost frames or terminate)
        for t_idx, track in enumerate(active_tracks):
            if t_idx not in matched_tracks:
                track.time_since_update += 1
                track.age += 1
                if track.time_since_update > self.max_lost_frames:
                    track.status = "terminated"
                else:
                    track.status = "lost"

        # Create new tracks for unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_detections and det.bounding_box is not None:
                new_track = self._create_track(camera_id, det, timestamp, frame_number)
                self._tracks[camera_id].append(new_track)

        return self.get_active_tracks(camera_id)

    def _create_track(
        self,
        camera_id: uuid.UUID,
        det: VehicleObservationCreate,
        timestamp: datetime,
        frame_number: Optional[int],
    ) -> TrackState:
        track_id = self._generate_track_id(camera_id)
        point = TrackPointData(
            timestamp=timestamp,
            frame_number=frame_number,
            bbox=det.bounding_box,  # type: ignore[arg-type]
            confidence=det.detection_confidence or 1.0,
            plate_text=det.plate_text,
            plate_confidence=det.plate_confidence,
            estimated_speed_kmh=det.estimated_speed_kmh,
        )

        return TrackState(
            track_id=track_id,
            camera_id=camera_id,
            start_time=timestamp,
            last_seen=timestamp,
            status="active",
            hits=1,
            age=1,
            time_since_update=0,
            bbox=det.bounding_box,  # type: ignore[arg-type]
            confidence=det.detection_confidence or 1.0,
            vehicle_class=det.vehicle_class,
            vehicle_color=det.vehicle_color,
            best_plate_text=det.plate_text,
            best_plate_confidence=det.plate_confidence,
            points=[point],
        )

    def _update_track(
        self,
        track: TrackState,
        det: VehicleObservationCreate,
        timestamp: datetime,
        frame_number: Optional[int],
    ) -> None:
        track.hits += 1
        track.age += 1
        track.time_since_update = 0
        track.status = "active"
        track.last_seen = timestamp
        if det.bounding_box:
            track.bbox = det.bounding_box

        # Update running average confidence
        track.confidence = round(
            ((track.confidence * (track.hits - 1)) + (det.detection_confidence or 1.0)) / track.hits,
            4,
        )

        # Update classification if not set
        if not track.vehicle_class and det.vehicle_class:
            track.vehicle_class = det.vehicle_class
        if not track.vehicle_color and det.vehicle_color:
            track.vehicle_color = det.vehicle_color

        # Update best plate reading if higher confidence
        if det.plate_text and (det.plate_confidence or 0.0) > (track.best_plate_confidence or 0.0):
            track.best_plate_text = det.plate_text
            track.best_plate_confidence = det.plate_confidence

        point = TrackPointData(
            timestamp=timestamp,
            frame_number=frame_number,
            bbox=det.bounding_box or track.bbox,
            confidence=det.detection_confidence or 1.0,
            plate_text=det.plate_text,
            plate_confidence=det.plate_confidence,
            estimated_speed_kmh=det.estimated_speed_kmh,
        )
        track.points.append(point)

    def get_active_tracks(self, camera_id: uuid.UUID) -> list[TrackState]:
        if camera_id not in self._tracks:
            return []
        return [t for t in self._tracks[camera_id] if t.status in ("active", "lost")]

    def reset(self, camera_id: Optional[uuid.UUID] = None) -> None:
        if camera_id is not None:
            self._tracks.pop(camera_id, None)
        else:
            self._tracks.clear()
            self._next_track_number = 1
