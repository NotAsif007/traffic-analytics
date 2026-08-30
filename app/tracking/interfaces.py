"""Abstract single-camera vehicle tracker interface."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from app.schemas.vehicle_observation import VehicleObservationCreate
from app.tracking.contracts import TrackState


class SingleCameraTracker(ABC):
    """
    Abstract interface for single-camera multi-object vehicle trackers
    (e.g. ByteTrack, BoT-SORT, DeepSORT, Sort).

    Maintains temporal continuity across consecutive frames from a single camera.
    Does NOT attempt cross-camera vehicle identification.
    """

    @abstractmethod
    def update(
        self,
        camera_id: uuid.UUID,
        timestamp: datetime,
        detections: list[VehicleObservationCreate],
        frame_number: int | None = None,
    ) -> list[TrackState]:
        """
        Update the tracker with detections from the current frame.

        Parameters
        ----------
        camera_id: uuid.UUID
            The camera producing this frame.
        timestamp: datetime
            Observation timestamp (timezone-aware).
        detections: list[VehicleObservationCreate]
            All vehicle detections / observations in this frame.
        frame_number: Optional[int]
            Video frame number if available.

        Returns
        -------
        list[TrackState]
            Active and updated track states for this camera stream.
        """
        pass

    @abstractmethod
    def get_active_tracks(self, camera_id: uuid.UUID) -> list[TrackState]:
        """Return all currently active tracks for the given camera."""
        pass

    @abstractmethod
    def reset(self, camera_id: uuid.UUID | None = None) -> None:
        """Reset internal tracking state (for a specific camera or all)."""
        pass
