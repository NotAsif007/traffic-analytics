"""Indian License Plate ANPR & OCR Dataset Adapter.

Handles ground truth Indian vehicle registration plates across all states:
- Format standard: 2 letters (State) + 2 digits (RTO) + 1-2 letters (Series) + 4 digits (Unique Number)
- High Security Registration Plates (HSRP) with IND hologram/embossing
- Two-line plates (common on motorcycles, auto-rickshaws, tractors)
- Custom / non-standard fonts and regional variations
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.datasets.base import BaseDatasetAdapter, DatasetSummary, ParsedDatasetObservation
from app.schemas.vehicle_observation import BoundingBox

# Valid Indian State and UT Prefix Codes
INDIAN_STATE_CODES = {
    "AN",
    "AP",
    "AR",
    "AS",
    "BR",
    "CG",
    "CH",
    "DD",
    "DL",
    "DN",
    "GA",
    "GJ",
    "HP",
    "HR",
    "JH",
    "JK",
    "KA",
    "KL",
    "LA",
    "LD",
    "MH",
    "ML",
    "MN",
    "MP",
    "MZ",
    "NL",
    "OD",
    "PB",
    "PY",
    "RJ",
    "SK",
    "TN",
    "TR",
    "TS",
    "UK",
    "UP",
    "WB",
}


class IndianPlateDatasetAdapter(BaseDatasetAdapter):
    """Adapter for Indian License Plate ANPR/OCR Benchmark Dataset."""

    @property
    def dataset_name(self) -> str:
        return "Indian License Plate ANPR/OCR Dataset"

    @property
    def dataset_code(self) -> str:
        return "indian_plate"

    def load_from_file_or_dict(self, data: dict[str, Any] | str) -> list[ParsedDatasetObservation]:
        """Parse raw Indian Plate dataset JSON format."""
        payload = json.loads(data) if isinstance(data, str) else data

        camera_id = (
            uuid.UUID(payload["camera_id"])
            if "camera_id" in payload
            else uuid.UUID("11111111-1111-1111-1111-111111111103")
        )
        camera_name = payload.get("camera_name", "ANPR-CHECKPOINT-CAM")
        observations: list[ParsedDatasetObservation] = []

        samples = payload.get("samples", [])
        for item in samples:
            plate_str = item.get("plate_number")
            state_code = plate_str[:2].upper() if plate_str and len(plate_str) >= 2 else "UNKNOWN"
            is_valid_hsrp = bool(item.get("is_hsrp", True))
            plate_layout = item.get("layout", "single_line")  # single_line | double_line

            v_bbox_coords = item.get("vehicle_bbox", [0.1, 0.1, 0.7, 0.7])
            p_bbox_coords = item.get("plate_bbox", [0.3, 0.45, 0.5, 0.55])

            v_bbox = BoundingBox(
                x1=min(max(float(v_bbox_coords[0]), 0.0), 1.0),
                y1=min(max(float(v_bbox_coords[1]), 0.0), 1.0),
                x2=min(max(float(v_bbox_coords[2]), 0.0), 1.0),
                y2=min(max(float(v_bbox_coords[3]), 0.0), 1.0),
            )

            p_bbox = BoundingBox(
                x1=min(max(float(p_bbox_coords[0]), 0.0), 1.0),
                y1=min(max(float(p_bbox_coords[1]), 0.0), 1.0),
                x2=min(max(float(p_bbox_coords[2]), 0.0), 1.0),
                y2=min(max(float(p_bbox_coords[3]), 0.0), 1.0),
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
                vehicle_class=item.get("vehicle_class", "car"),
                vehicle_color=item.get("vehicle_color", "unknown"),
                detection_confidence=float(item.get("detection_confidence", 0.98)),
                bounding_box=v_bbox,
                plate_text=plate_str,
                plate_confidence=float(item.get("ocr_confidence", 0.96)),
                plate_bounding_box=p_bbox,
                track_id=item.get("track_id"),
                true_vehicle_id=item.get("vehicle_id"),
                metadata={
                    "state_code": state_code,
                    "is_state_valid": state_code in INDIAN_STATE_CODES,
                    "is_hsrp": is_valid_hsrp,
                    "plate_layout": plate_layout,
                    "raw_noisy_ocr": item.get("noisy_ocr_variant"),
                    "image_path": item.get("image_path"),
                },
            )
            observations.append(obs)

        return observations

    def get_summary(self, observations: list[ParsedDatasetObservation]) -> DatasetSummary:
        classes = sorted({obs.vehicle_class for obs in observations})

        return DatasetSummary(
            dataset_name=self.dataset_name,
            dataset_code=self.dataset_code,
            description="Indian ANPR ground truth dataset spanning 36 states/UTs, HSRP and 2-line plate layouts with character-level annotations.",
            total_frames_or_sequences=len(observations),
            total_observations=len(observations),
            unique_vehicles=len(observations),
            supported_classes=classes,
            has_license_plates=True,
            has_multi_camera_ids=False,
        )
