"""Indian Traffic Dataset (ITD) static-camera traffic adapter.

Handles static camera video sequences with flow parameters, vehicle counts,
and Indian road conditions (monsoon rain, night glare, variable density).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.datasets.base import BaseDatasetAdapter, DatasetSummary, ParsedDatasetObservation
from app.schemas.vehicle_observation import BoundingBox

ITD_CLASS_MAP = {
    "car": "car",
    "two_wheeler": "motorcycle",
    "motorcycle": "motorcycle",
    "scooter": "motorcycle",
    "auto": "auto_rickshaw",
    "bus": "bus",
    "lcv": "van",
    "hcv": "truck",
    "truck": "truck",
    "bicycle": "bicycle",
}


class ITDDatasetAdapter(BaseDatasetAdapter):
    """Adapter for Indian Traffic Dataset (ITD) static surveillance video streams."""

    @property
    def dataset_name(self) -> str:
        return "Indian Traffic Dataset (ITD)"

    @property
    def dataset_code(self) -> str:
        return "itd"

    def load_from_file_or_dict(self, data: dict[str, Any] | str) -> list[ParsedDatasetObservation]:
        """Parse raw ITD sequence JSON format."""
        payload = json.loads(data) if isinstance(data, str) else data

        camera_id = (
            uuid.UUID(payload["camera_id"])
            if "camera_id" in payload
            else uuid.UUID("11111111-1111-1111-1111-111111111102")
        )
        camera_name = payload.get("camera_name", "ITD-SURVEILLANCE-CAM")
        observations: list[ParsedDatasetObservation] = []

        sequences = payload.get("sequences", [])
        for seq in sequences:
            weather_condition = seq.get("weather", "clear")
            lighting_condition = seq.get("lighting", "day")

            for item in seq.get("vehicles", []):
                raw_class = str(item.get("class", "car")).lower().strip()
                norm_class = ITD_CLASS_MAP.get(raw_class, "car")
                bbox_coords = item.get("bounding_box", [0.15, 0.15, 0.45, 0.45])

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
                    detection_confidence=float(item.get("detection_confidence", 0.93)),
                    bounding_box=bbox,
                    plate_text=item.get("plate_text"),
                    plate_confidence=float(item.get("plate_confidence", 0.90))
                    if item.get("plate_text")
                    else None,
                    track_id=item.get("track_id"),
                    true_vehicle_id=item.get("vehicle_id"),
                    metadata={
                        "sequence_id": seq.get("sequence_id"),
                        "weather": weather_condition,
                        "lighting": lighting_condition,
                        "estimated_speed_kmh": item.get("speed_kmh"),
                    },
                )
                observations.append(obs)

        return observations

    def get_summary(self, observations: list[ParsedDatasetObservation]) -> DatasetSummary:
        unique_v = {
            obs.true_vehicle_id or obs.track_id
            for obs in observations
            if obs.true_vehicle_id or obs.track_id
        }
        classes = sorted({obs.vehicle_class for obs in observations})
        has_plates = any(obs.plate_text is not None for obs in observations)

        return DatasetSummary(
            dataset_name=self.dataset_name,
            dataset_code=self.dataset_code,
            description="Static camera traffic monitoring dataset under diverse Indian weather, illumination, and congestion levels.",
            total_frames_or_sequences=len(
                {obs.metadata.get("sequence_id") for obs in observations}
            ),
            total_observations=len(observations),
            unique_vehicles=len(unique_v) if unique_v else len(observations),
            supported_classes=classes,
            has_license_plates=has_plates,
            has_multi_camera_ids=False,
        )
