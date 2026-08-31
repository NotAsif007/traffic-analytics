"""Base abstract interface and contracts for real-world dataset adapters."""

from __future__ import annotations

import abc
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.vehicle_observation import BoundingBox, VehicleObservationCreate


class ParsedDatasetObservation(BaseModel):
    """Normalized observation parsed from a real dataset."""

    dataset_name: str
    camera_id: uuid.UUID
    camera_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vehicle_class: str
    vehicle_color: str | None = "unknown"
    detection_confidence: float = 0.95
    bounding_box: BoundingBox
    plate_text: str | None = None
    plate_confidence: float | None = None
    plate_bounding_box: BoundingBox | None = None
    track_id: str | None = None
    true_vehicle_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_observation_create(self) -> VehicleObservationCreate:
        """Convert into API observation creation schema."""
        obs_uid = self.true_vehicle_id or self.track_id or str(uuid.uuid4())[:8]
        ts_ms = int(self.timestamp.timestamp() * 1000)
        has_plate = bool(self.plate_text and self.plate_text.strip())
        return VehicleObservationCreate(
            source=f"dataset:{self.dataset_name}",
            source_observation_id=f"{self.dataset_name}-{obs_uid}-{ts_ms}",
            camera_id=self.camera_id,
            observed_at=self.timestamp,
            vehicle_class=self.vehicle_class,
            vehicle_color=self.vehicle_color,
            detection_confidence=self.detection_confidence,
            bounding_box=self.bounding_box,
            plate_text=self.plate_text if has_plate else None,
            plate_confidence=self.plate_confidence if has_plate else None,
            plate_bbox=self.plate_bounding_box if has_plate else None,
            track_id=self.track_id,
        )


class DatasetSummary(BaseModel):
    """Metadata summary of a loaded real-world dataset."""

    dataset_name: str
    dataset_code: str
    description: str
    total_frames_or_sequences: int
    total_observations: int
    unique_vehicles: int
    supported_classes: list[str]
    has_license_plates: bool
    has_multi_camera_ids: bool


class BaseDatasetAdapter(abc.ABC):
    """Abstract Base Class for external traffic dataset adapters."""

    @property
    @abc.abstractmethod
    def dataset_name(self) -> str:
        """Human-readable dataset name."""
        ...

    @property
    @abc.abstractmethod
    def dataset_code(self) -> str:
        """Unique short identifier."""
        ...

    @abc.abstractmethod
    def load_from_file_or_dict(self, data: dict[str, Any] | str) -> list[ParsedDatasetObservation]:
        """Parse raw dataset content into normalized observations."""
        ...

    @abc.abstractmethod
    def get_summary(self, observations: list[ParsedDatasetObservation]) -> DatasetSummary:
        """Generate statistical summary of parsed dataset observations."""
        ...
