"""Tracking state contracts and data structures for single-camera tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from app.schemas.common import AppBaseModel
from app.schemas.vehicle_observation import BoundingBox


class TrackPointData(AppBaseModel):
    """Data representation of a single track point state."""
    timestamp: datetime
    frame_number: Optional[int] = None
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0)
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    estimated_speed_kmh: Optional[float] = None
    observation_id: Optional[uuid.UUID] = None


class TrackState(AppBaseModel):
    """
    Current live state of an active or completed single-camera track.
    """
    track_id: str = Field(..., description="Local tracker ID within this camera stream")
    camera_id: uuid.UUID
    start_time: datetime
    last_seen: datetime
    status: str = Field(default="active", description="active | lost | completed | terminated")
    hits: int = Field(default=1, description="Number of successful detection associations")
    age: int = Field(default=1, description="Total frame age of track")
    time_since_update: int = Field(default=0, description="Frames since last detection")
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0)
    vehicle_class: Optional[str] = None
    vehicle_color: Optional[str] = None
    best_plate_text: Optional[str] = None
    best_plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    points: list[TrackPointData] = Field(default_factory=list)
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


def calculate_iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes."""
    x_left = max(box_a.x1, box_b.x1)
    y_top = max(box_a.y1, box_b.y1)
    x_right = min(box_a.x2, box_b.x2)
    y_bottom = min(box_a.y2, box_b.y2)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    area_a = (box_a.x2 - box_a.x1) * (box_a.y2 - box_a.y1)
    area_b = (box_b.x2 - box_b.x1) * (box_b.y2 - box_b.y1)

    union_area = area_a + area_b - intersection_area
    if union_area <= 0:
        return 0.0

    return round(intersection_area / union_area, 4)
