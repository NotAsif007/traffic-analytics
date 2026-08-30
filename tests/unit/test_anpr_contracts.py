"""Unit tests for ANPR contracts and data models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.anpr.contracts import (
    FrameInput,
    OCRResult,
    PlateDetectionResult,
    VehicleDetectionResult,
)
from app.schemas.vehicle_observation import BoundingBox


@pytest.mark.unit
def test_frame_input_creation() -> None:
    frame = FrameInput(
        camera_id=uuid.uuid4(),
        observed_at=datetime.now(timezone.utc),
        frame_path="s3://bucket/frame.jpg",
        frame_number=10,
    )
    assert frame.frame_number == 10
    assert frame.source == "anpr-pipeline"


@pytest.mark.unit
def test_vehicle_detection_result_confidence_bounds() -> None:
    bbox = BoundingBox(x1=0.1, y1=0.1, x2=0.8, y2=0.8)
    res = VehicleDetectionResult(
        bbox=bbox,
        vehicle_class="car",
        confidence=0.95,
    )
    assert res.confidence == 0.95

    with pytest.raises(ValidationError):
        VehicleDetectionResult(
            bbox=bbox,
            vehicle_class="car",
            confidence=1.5,
        )


@pytest.mark.unit
def test_plate_detection_result_creation() -> None:
    bbox = BoundingBox(x1=0.2, y1=0.5, x2=0.5, y2=0.7)
    res = PlateDetectionResult(
        bbox=bbox,
        confidence=0.89,
        plate_region="IN",
    )
    assert res.plate_region == "IN"
    assert res.confidence == 0.89


@pytest.mark.unit
def test_ocr_result_char_confidences_validation() -> None:
    res = OCRResult(
        raw_text="AS01AB1234",
        confidence=0.92,
        char_confidences=[0.9, 0.95, 0.92, 0.88, 0.95, 0.91, 0.94, 0.93, 0.89, 0.92],
    )
    assert len(res.char_confidences) == 10

    with pytest.raises(ValidationError):
        OCRResult(
            raw_text="AS01",
            confidence=0.92,
            char_confidences=[0.9, 1.2, 0.9, 0.9],  # 1.2 is out of range
        )
