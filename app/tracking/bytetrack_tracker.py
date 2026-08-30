"""Real ByteTrack Multi-Object Vehicle Tracker.

Implements two-stage bipartite matching (high confidence first, low confidence recovery)
with temporal continuity and track state management for single-camera streams.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from app.core.logging import get_logger
from app.schemas.vehicle_observation import VehicleObservationCreate
from app.tracking.contracts import TrackPointData, TrackState, calculate_iou
from app.tracking.interfaces import SingleCameraTracker

logger = get_logger(__name__)


class ByteTrackSingleCameraTracker(SingleCameraTracker):
    """
    ByteTrack single-camera multi-object vehicle tracker.
    """

    def __init__(
        self,
        high_score_threshold: float = 0.50,
        low_score_threshold: float = 0.15,
        match_iou_threshold: float = 0.30,
        second_match_iou_threshold: float = 0.20,
        max_time_lost_frames: int = 30,
    ) -> None:
        self.high_score_threshold = high_score_threshold
        self.low_score_threshold = low_score_threshold
        self.match_iou_threshold = match_iou_threshold
        self.second_match_iou_threshold = second_match_iou_threshold
        self.max_time_lost_frames = max_time_lost_frames

        # Per-camera active tracks: camera_id -> list of TrackState
        self._tracks: dict[uuid.UUID, list[TrackState]] = defaultdict(list)
        self._next_track_number: dict[uuid.UUID, int] = defaultdict(lambda: 1)

    def update(
        self,
        camera_id: uuid.UUID,
        timestamp: datetime,
        detections: list[VehicleObservationCreate],
        frame_number: int | None = None,
    ) -> list[TrackState]:
        """
        Update ByteTrack with detections for the current frame.
        """
        active_tracks = self._tracks[camera_id]

        # Partition detections into high score and low score pools
        high_dets: list[VehicleObservationCreate] = []
        low_dets: list[VehicleObservationCreate] = []

        for det in detections:
            conf = det.detection_confidence
            if conf >= self.high_score_threshold:
                high_dets.append(det)
            elif conf >= self.low_score_threshold:
                low_dets.append(det)

        # Stage 1: Associate high score detections with active tracks
        matched_tracks, unmatched_tracks, unmatched_high_dets = self._associate(
            active_tracks, high_dets, self.match_iou_threshold
        )

        # Update matched tracks from stage 1
        for track, det in matched_tracks:
            self._update_track(track, det, timestamp, frame_number)

        # Stage 2: Associate remaining active tracks with low score detections
        stage2_matched_tracks, remaining_unmatched_tracks, _ = self._associate(
            unmatched_tracks, low_dets, self.second_match_iou_threshold
        )

        for track, det in stage2_matched_tracks:
            self._update_track(track, det, timestamp, frame_number)

        # Mark unmatched tracks as lost/increment time_since_update
        surviving_tracks: list[TrackState] = []
        for track in active_tracks:
            if track in [m[0] for m in matched_tracks] or track in [m[0] for m in stage2_matched_tracks]:
                surviving_tracks.append(track)
            else:
                track.time_since_update += 1
                track.age += 1
                if track.time_since_update < self.max_time_lost_frames:
                    track.status = "lost"
                    surviving_tracks.append(track)
                else:
                    track.status = "terminated"

        # Stage 3: Initialize new tracks from unmatched high-confidence detections
        for det in unmatched_high_dets:
            new_track = self._create_track(camera_id, det, timestamp, frame_number)
            surviving_tracks.append(new_track)

        self._tracks[camera_id] = surviving_tracks
        return [t for t in surviving_tracks if t.status == "active"]

    def get_active_tracks(self, camera_id: uuid.UUID) -> list[TrackState]:
        """Return all active tracks for a camera."""
        return [t for t in self._tracks.get(camera_id, []) if t.status == "active"]

    def reset(self, camera_id: uuid.UUID | None = None) -> None:
        """Reset internal tracking state."""
        if camera_id is not None:
            self._tracks[camera_id].clear()
            self._next_track_number[camera_id] = 1
        else:
            self._tracks.clear()
            self._next_track_number.clear()

    def _associate(
        self,
        tracks: list[TrackState],
        dets: list[VehicleObservationCreate],
        iou_threshold: float,
    ) -> tuple[
        list[tuple[TrackState, VehicleObservationCreate]],
        list[TrackState],
        list[VehicleObservationCreate],
    ]:
        if not tracks or not dets:
            return [], list(tracks), list(dets)

        # Compute IoU matrix
        iou_matrix = [[calculate_iou(t.bbox, d.bounding_box) for d in dets] for t in tracks]

        matched_tracks: list[tuple[TrackState, VehicleObservationCreate]] = []
        unmatched_track_indices = set(range(len(tracks)))
        unmatched_det_indices = set(range(len(dets)))

        # Greedy bipartite matching
        flat_matches: list[tuple[float, int, int]] = []
        for t_idx, row in enumerate(iou_matrix):
            for d_idx, iou_val in enumerate(row):
                if iou_val >= iou_threshold:
                    flat_matches.append((iou_val, t_idx, d_idx))

        flat_matches.sort(key=lambda x: x[0], reverse=True)

        for _, t_idx, d_idx in flat_matches:
            if t_idx in unmatched_track_indices and d_idx in unmatched_det_indices:
                matched_tracks.append((tracks[t_idx], dets[d_idx]))
                unmatched_track_indices.remove(t_idx)
                unmatched_det_indices.remove(d_idx)

        unmatched_tracks = [tracks[i] for i in unmatched_track_indices]
        unmatched_dets = [dets[j] for j in unmatched_det_indices]

        return matched_tracks, unmatched_tracks, unmatched_dets

    def _create_track(
        self,
        camera_id: uuid.UUID,
        det: VehicleObservationCreate,
        timestamp: datetime,
        frame_number: int | None,
    ) -> TrackState:
        t_num = self._next_track_number[camera_id]
        self._next_track_number[camera_id] += 1
        track_id = f"TRK-{str(camera_id)[:8]}-{t_num:04d}"

        point = TrackPointData(
            timestamp=timestamp,
            frame_number=frame_number,
            bbox=det.bounding_box,
            confidence=det.detection_confidence,
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
            bbox=det.bounding_box,
            confidence=det.detection_confidence,
            vehicle_class=det.vehicle_class,
            vehicle_color=det.vehicle_color,
            best_plate_text=det.plate_text,
            best_plate_confidence=det.plate_confidence,
            points=[point],
            metadata={
                "tracker": "ByteTrack",
                "embedding_id": det.embedding_id,
            },
        )

    def _update_track(
        self,
        track: TrackState,
        det: VehicleObservationCreate,
        timestamp: datetime,
        frame_number: int | None,
    ) -> None:
        track.last_seen = timestamp
        track.bbox = det.bounding_box
        track.confidence = det.detection_confidence
        track.hits += 1
        track.age += 1
        track.time_since_update = 0
        track.status = "active"

        if det.vehicle_color and not track.vehicle_color:
            track.vehicle_color = det.vehicle_color

        if det.plate_text:
            det_conf = det.plate_confidence or 0.0
            cur_best_conf = track.best_plate_confidence or 0.0
            if det_conf >= cur_best_conf or not track.best_plate_text:
                track.best_plate_text = det.plate_text
                track.best_plate_confidence = det.plate_confidence

        point = TrackPointData(
            timestamp=timestamp,
            frame_number=frame_number,
            bbox=det.bounding_box,
            confidence=det.detection_confidence,
            plate_text=det.plate_text,
            plate_confidence=det.plate_confidence,
            estimated_speed_kmh=det.estimated_speed_kmh,
        )
        track.points.append(point)
