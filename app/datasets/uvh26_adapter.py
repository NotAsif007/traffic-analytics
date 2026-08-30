"""UVH-26 Indian CCTV vehicle detection dataset adapter.

Handles Indian CCTV streams with dense mixed traffic:
- Auto-rickshaws
- Two-wheelers / Motorcycles
- Cars / Cabs
- Heavy Commercial Vehicles (Trucks / Buses)
- Tractors & Agriculture Vehicles
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.datasets.base import BaseDatasetAdapter, DatasetSummary, ParsedDatasetObservation
from app.schemas.vehicle_observation import BoundingBox

# Mapping from UVH-26 dataset class names to normalized system vehicle classes
UVH26_CLASS_MAP = {
    "auto": "auto_rickshaw",
    "autorickshaw": "auto_rickshaw",
    "auto_rickshaw": "auto_rickshaw",
    "three_wheeler": "auto_rickshaw",
    "bike": "motorcycle",
    "motorcycle": "motorcycle",
    "scooter": "motorcycle",
    "two_wheeler": "motorcycle",
    "car": "car",
    "sedan": "car",
    "hatchback": "car",
    "suv": "car",
    "bus": "bus",
    "minibus": "bus",
    "truck": "truck",
    "lorry": "truck",
    "commercial_truck": "truck",
    "tractor": "truck",
    "van": "van",
    "tempo": "van",
}


class UVH26DatasetAdapter(BaseDatasetAdapter):
    """Adapter for UVH-26 Indian CCTV Vehicle Detection Dataset."""

    @property
    def dataset_name(self) -> str:
        return "UVH-26 Indian CCTV Vehicle Dataset"

    @property
    def dataset_code(self) -> str:
        return "uvh26"

    def load_from_file_or_dict(self, data: dict[str, Any] | str) -> list[ParsedDatasetObservation]:
        """Parse raw UVH-26 annotations format."""
        payload = json.loads(data) if isinstance(data, str) else data

        camera_id = (
            uuid.UUID(payload["camera_id"])
            if "camera_id" in payload
            else uuid.UUID("11111111-1111-1111-1111-111111111101")
        )
        camera_name = payload.get("camera_name", "UVH26-CAM-01")
        observations: list[ParsedDatasetObservation] = []

        frames = payload.get("frames", [])
        for frame in frames:
            timestamp_str = frame.get("timestamp")
            if timestamp_str:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                ts = datetime.now(timezone.utc)

            for det in frame.get("detections", []):
                raw_class = str(det.get("class", "car")).lower().strip()
                norm_class = UVH26_CLASS_MAP.get(raw_class, "car")
                bbox_raw = det.get("bbox", [0.1, 0.1, 0.5, 0.5])

                # Ensure normalized [0.0, 1.0] bbox
                bbox = BoundingBox(
                    x1=min(max(float(bbox_raw[0]), 0.0), 1.0),
                    y1=min(max(float(bbox_raw[1]), 0.0), 1.0),
                    x2=min(max(float(bbox_raw[2]), 0.0), 1.0),
                    y2=min(max(float(bbox_raw[3]), 0.0), 1.0),
                )

                obs = ParsedDatasetObservation(
                    dataset_name=self.dataset_code,
                    camera_id=camera_id,
                    camera_name=camera_name,
                    timestamp=ts,
                    vehicle_class=norm_class,
                    vehicle_color=det.get("color", "unknown"),
                    detection_confidence=float(det.get("confidence", 0.94)),
                    bounding_box=bbox,
                    plate_text=det.get("license_plate"),
                    plate_confidence=float(det.get("plate_confidence", 0.92))
                    if det.get("license_plate")
                    else None,
                    track_id=det.get("track_id"),
                    true_vehicle_id=det.get("vehicle_id"),
                    metadata={
                        "frame_id": frame.get("frame_id"),
                        "raw_class": raw_class,
                        "occlusion_level": det.get("occlusion", "none"),
                    },
                )
                observations.append(obs)

        return observations

    def get_summary(self, observations: list[ParsedDatasetObservation]) -> DatasetSummary:
        unique_v = {
            obs.true_vehicle_id or obs.track_id or f"v_{idx}"
            for idx, obs in enumerate(observations)
        }
        classes = sorted({obs.vehicle_class for obs in observations})
        has_plates = any(obs.plate_text is not None for obs in observations)

        return DatasetSummary(
            dataset_name=self.dataset_name,
            dataset_code=self.dataset_code,
            description="Indian Urban CCTV vehicle detection benchmark with high density auto-rickshaws, bikes, and commercial traffic.",
            total_frames_or_sequences=len({obs.metadata.get("frame_id") for obs in observations}),
            total_observations=len(observations),
            unique_vehicles=len(unique_v),
            supported_classes=classes,
            has_license_plates=has_plates,
            has_multi_camera_ids=False,
        )
