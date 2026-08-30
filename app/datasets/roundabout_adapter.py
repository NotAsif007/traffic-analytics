"""RoundaboutHD multi-camera vehicle tracking dataset adapter.

Handles multi-camera synchronized drone/pole-mounted high-definition streams
with cross-camera ground truth vehicle IDs for trajectory evaluation.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.datasets.base import BaseDatasetAdapter, DatasetSummary, ParsedDatasetObservation
from app.schemas.vehicle_observation import BoundingBox


class RoundaboutHDDatasetAdapter(BaseDatasetAdapter):
    """Adapter for RoundaboutHD Multi-Camera Trajectory Tracking Dataset."""

    @property
    def dataset_name(self) -> str:
        return "RoundaboutHD Multi-Camera Tracking Dataset"

    @property
    def dataset_code(self) -> str:
        return "roundabouthd"

    def load_from_file_or_dict(self, data: dict[str, Any] | str) -> list[ParsedDatasetObservation]:
        """Parse raw RoundaboutHD multi-camera JSON format."""
        payload = json.loads(data) if isinstance(data, str) else data

        cameras_lookup: dict[str, uuid.UUID] = {}
        for cam in payload.get("cameras", []):
            cid_str = cam.get("id")
            c_name = cam.get("name", "ROUNDABOUT-CAM")
            cid = uuid.UUID(cid_str) if cid_str else uuid.uuid4()
            cameras_lookup[c_name] = cid

        observations: list[ParsedDatasetObservation] = []

        tracks = payload.get("multi_camera_tracks", [])
        for trk in tracks:
            global_veh_id = trk.get("global_vehicle_id", str(uuid.uuid4()))
            v_class = trk.get("vehicle_class", "car")
            v_color = trk.get("vehicle_color", "unknown")
            canonical_plate = trk.get("license_plate")

            for sighting in trk.get("camera_sightings", []):
                cam_name = sighting.get("camera_name", "ROUNDABOUT-CAM-01")
                cam_id = cameras_lookup.get(
                    cam_name, uuid.UUID("11111111-1111-1111-1111-111111111104")
                )

                bbox_coords = sighting.get("bounding_box", [0.2, 0.2, 0.6, 0.6])
                bbox = BoundingBox(
                    x1=min(max(float(bbox_coords[0]), 0.0), 1.0),
                    y1=min(max(float(bbox_coords[1]), 0.0), 1.0),
                    x2=min(max(float(bbox_coords[2]), 0.0), 1.0),
                    y2=min(max(float(bbox_coords[3]), 0.0), 1.0),
                )

                ts_raw = sighting.get("timestamp")
                ts = (
                    datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if ts_raw
                    else datetime.now(timezone.utc)
                )

                obs = ParsedDatasetObservation(
                    dataset_name=self.dataset_code,
                    camera_id=cam_id,
                    camera_name=cam_name,
                    timestamp=ts,
                    vehicle_class=v_class,
                    vehicle_color=v_color,
                    detection_confidence=float(sighting.get("detection_confidence", 0.96)),
                    bounding_box=bbox,
                    plate_text=canonical_plate or sighting.get("plate_text"),
                    plate_confidence=float(sighting.get("plate_confidence", 0.94))
                    if (canonical_plate or sighting.get("plate_text"))
                    else None,
                    track_id=sighting.get("local_track_id"),
                    true_vehicle_id=global_veh_id,
                    metadata={
                        "roundabout_zone": sighting.get("zone", "entry"),
                        "speed_kmh": sighting.get("speed_kmh", 35.0),
                        "heading_deg": sighting.get("heading_deg", 90.0),
                    },
                )
                observations.append(obs)

        return observations

    def get_summary(self, observations: list[ParsedDatasetObservation]) -> DatasetSummary:
        unique_v = {obs.true_vehicle_id for obs in observations if obs.true_vehicle_id}
        classes = sorted({obs.vehicle_class for obs in observations})
        cam_names = {obs.camera_name for obs in observations}

        return DatasetSummary(
            dataset_name=self.dataset_name,
            dataset_code=self.dataset_code,
            description="Multi-camera synchronized roundabout traffic dataset for multi-target multi-camera (MTMC) tracking and cross-camera Re-ID.",
            total_frames_or_sequences=len(cam_names),
            total_observations=len(observations),
            unique_vehicles=len(unique_v),
            supported_classes=classes,
            has_license_plates=any(obs.plate_text is not None for obs in observations),
            has_multi_camera_ids=True,
        )
