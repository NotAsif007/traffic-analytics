"""Unit tests for the end-to-end ANPR Pipeline orchestrator with mock models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.anpr.contracts import FrameInput
from app.anpr.mock import MockPlateDetector, MockPlateOCR, MockVehicleDetector
from app.anpr.normalizer import OCRNormalizer
from app.anpr.pipeline import ANPRPipeline


@pytest.fixture
def frame() -> FrameInput:
    return FrameInput(
        camera_id=uuid.uuid4(),
        observed_at=datetime.now(timezone.utc),
        frame_path="s3://frames/2026/08/30/cam-01/f1.jpg",
        frame_number=100,
    )


@pytest.mark.unit
async def test_anpr_pipeline_end_to_end(frame: FrameInput) -> None:
    """ANPRPipeline correctly orchestrates detection -> localization -> OCR -> normalization."""
    v_det = MockVehicleDetector(default_class="car", default_confidence=0.96)
    p_det = MockPlateDetector(default_confidence=0.92, default_region="IN")
    p_ocr = MockPlateOCR(default_text=" as 01-ab 1234 ", default_confidence=0.91)

    pipeline = ANPRPipeline(
        vehicle_detector=v_det,
        plate_detector=p_det,
        plate_ocr=p_ocr,
        normalizer=OCRNormalizer(),
        source_name="test-pipeline",
    )

    results = await pipeline.process_frame(frame)

    assert len(results) == 1
    obs = results[0]
    assert obs.vehicle_class == "car"
    assert obs.detection_confidence == 0.96
    # Verified normalized plate
    assert obs.plate_text == "AS01AB1234"
    assert obs.plate_confidence == 0.91
    assert obs.plate_region == "IN"
    assert obs.camera_id == frame.camera_id
    assert obs.source == "test-pipeline"
    assert obs.frame_number == 100
    assert obs.metadata_ is not None
    assert obs.metadata_["ocr_raw_text"] == " as 01-ab 1234 "


@pytest.mark.unit
async def test_anpr_pipeline_vehicle_without_plate(frame: FrameInput) -> None:
    """When plate is not localized or occluded, vehicle observation is still created."""
    v_det = MockVehicleDetector(default_class="motorcycle", default_confidence=0.88)
    p_det = MockPlateDetector(return_none=True)  # Plate detector fails
    p_ocr = MockPlateOCR()

    pipeline = ANPRPipeline(
        vehicle_detector=v_det,
        plate_detector=p_det,
        plate_ocr=p_ocr,
    )

    results = await pipeline.process_frame(frame)

    assert len(results) == 1
    obs = results[0]
    assert obs.vehicle_class == "motorcycle"
    assert obs.detection_confidence == 0.88
    assert obs.plate_text is None
    assert obs.plate_confidence is None
    assert obs.plate_bbox is None


@pytest.mark.unit
async def test_anpr_pipeline_empty_frame(frame: FrameInput) -> None:
    """When no vehicles are detected, returns empty list."""
    v_det = MockVehicleDetector(return_empty=True)
    p_det = MockPlateDetector()
    p_ocr = MockPlateOCR()

    pipeline = ANPRPipeline(
        vehicle_detector=v_det,
        plate_detector=p_det,
        plate_ocr=p_ocr,
    )

    results = await pipeline.process_frame(frame)
    assert results == []
