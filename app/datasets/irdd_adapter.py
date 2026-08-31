"""Indian Road Driving Dataset (IRDD / IDD) adapter.

Handles unstructured Indian driving scenarios:
- Extreme occlusion and vehicle density
- Heterogeneous class distributions (rickshaws, bikes, handcarts, tempos)
- Non-lane driving, pedestrian-vehicle co-occurrence
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.datasets.base import BaseDatasetAdapter, DatasetSummary, ParsedDatasetObservation
from app.schemas.vehicle_observation import BoundingBox

IRDD_CLASS_MAP = {
    "car": "car",
    "motorcycle": "motorcycle",
    "rider": "motorcycle",
    "autorickshaw": "auto_rickshaw",
    "auto": "auto_rickshaw",
    "bus": "bus",
    "truck": "truck",
    "tempo": "van",
    "tractor": "truck",
    "bicycle": "bicycle",
    "vehicle fallback": "car",
}


class IRDDDatasetAdapter(BaseDatasetAdapter):
    """Adapter for Indian Road Driving Dataset (IRDD / IDD)."""

    @property
    def dataset_name(self) -> str:
        return "Indian Road Driving Dataset (IRDD/IDD)"

    @property
    def dataset_code(self) -> str:
        return "irdd"

    def load_from_file_or_dict(self, data: dict[str, Any] | str) -> list[ParsedDatasetObservation]:
        """Parse raw IRDD scene JSON format."""
        payload = json.loads(data) if isinstance(data, str) else data

        camera_id = (
            uuid.UUID(payload["camera_id"])
            if "camera_id" in payload
            else uuid.UUID("11111111-1111-1111-1111-111111111105")
        )
        camera_name = payload.get("camera_name", "IRDD-DASH-CAM-01")
        observations: list[ParsedDatasetObservation] = []

        scenes = payload.get("scenes", [])
        for scene in scenes:
            road_type = scene.get("road_type", "urban_arterial")
            traffic_density = scene.get("density", "high")

            for item in scene.get("objects", []):
                raw_class = str(item.get("category", "car")).lower().strip()
                norm_class = IRDD_CLASS_MAP.get(raw_class, "car")
                bbox_coords = item.get("box", [0.1, 0.2, 0.4, 0.6])

                bbox = BoundingBox(
                    x1=min(max(float(bbox_coords[0]), 0.0), 1.0),
                    y1=min(max(float(bbox_coords[1]), 0.0), 1.0),
                    x2=min(max(float(bbox_coords[2]), 0.0), 1.0),
                    y2=min(max(float(bbox_coords[3]), 0.0), 1.0),
                )

                ts_raw = item.get("timestamp")
                ts = (
                    datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if ts_raw
                    else datetime.now(timezone.utc)
                )

                obs = ParsedDatasetObservation(
                    dataset_name=self.dataset_code,
                    camera_id=camera_id,
                    camera_name=camera_name,
                    timestamp=ts,
                    vehicle_class=norm_class,
                    vehicle_color=item.get("color", "unknown"),
                    detection_confidence=float(item.get("confidence", 0.91)),
                    bounding_box=bbox,
                    plate_text=item.get("license_plate"),
                    plate_confidence=float(item.get("plate_confidence", 0.88))
                    if item.get("license_plate")
                    else None,
                    track_id=item.get("track_id"),
                    true_vehicle_id=item.get("vehicle_id"),
                    metadata={
                        "road_type": road_type,
                        "density": traffic_density,
                        "occlusion_ratio": item.get("occlusion_ratio", 0.2),
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

        return DatasetSummary(
            dataset_name=self.dataset_name,
            dataset_code=self.dataset_code,
            description="Indian Road Driving Dataset benchmark for robust perception under heavy occlusion, unconstrained lane behaviour, and unstructured traffic.",
            total_frames_or_sequences=len(observations),
            total_observations=len(observations),
            unique_vehicles=len(unique_v),
            supported_classes=classes,
            has_license_plates=any(obs.plate_text is not None for obs in observations),
            has_multi_camera_ids=False,
        )
