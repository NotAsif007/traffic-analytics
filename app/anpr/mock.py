"""Mock implementations of ANPR components strictly for automated testing and local development."""

from __future__ import annotations

from typing import Optional

from app.anpr.contracts import (
    FrameInput,
    OCRResult,
    PlateDetectionResult,
    VehicleDetectionResult,
)
from app.anpr.interfaces import PlateDetector, PlateOCR, VehicleDetector
from app.schemas.vehicle_observation import BoundingBox


class MockVehicleDetector(VehicleDetector):
    """
    Simulates vehicle detection without running a neural network.
    """

    def __init__(
        self,
        default_class: str = "car",
        default_confidence: float = 0.95,
        default_color: str = "white",
        default_bbox: Optional[BoundingBox] = None,
        return_empty: bool = False,
    ) -> None:
        self.default_class = default_class
        self.default_confidence = default_confidence
        self.default_color = default_color
        self.default_bbox = default_bbox or BoundingBox(x1=0.1, y1=0.1, x2=0.8, y2=0.8)
        self.return_empty = return_empty

    async def detect_vehicles(
        self,
        frame: FrameInput,
    ) -> list[VehicleDetectionResult]:
        if self.return_empty:
            return []

        return [
            VehicleDetectionResult(
                bbox=self.default_bbox,
                vehicle_class=self.default_class,
                confidence=self.default_confidence,
                vehicle_color=self.default_color,
                crop_path=f"storage/crops/{frame.camera_id}_v1.jpg",
                metadata={"detector": "mock-yolo-v8"},
            )
        ]


class MockPlateDetector(PlateDetector):
    """
    Simulates license plate detection/localization.
    """

    def __init__(
        self,
        default_confidence: float = 0.92,
        default_bbox: Optional[BoundingBox] = None,
        default_region: str = "IN",
        return_none: bool = False,
    ) -> None:
        self.default_confidence = default_confidence
        self.default_bbox = default_bbox or BoundingBox(x1=0.3, y1=0.6, x2=0.6, y2=0.75)
        self.default_region = default_region
        self.return_none = return_none

    async def detect_plate(
        self,
        frame: FrameInput,
        vehicle_detection: VehicleDetectionResult,
    ) -> Optional[PlateDetectionResult]:
        if self.return_none:
            return None

        return PlateDetectionResult(
            bbox=self.default_bbox,
            confidence=self.default_confidence,
            plate_crop_path=f"storage/plates/{frame.camera_id}_p1.jpg",
            plate_region=self.default_region,
            metadata={"detector": "mock-plate-localizer"},
        )


class MockPlateOCR(PlateOCR):
    """
    Simulates character recognition on a plate crop.
    """

    def __init__(
        self,
        default_text: str = "AS01AB1234",
        default_confidence: float = 0.94,
        char_confidences: Optional[list[float]] = None,
        return_none: bool = False,
    ) -> None:
        self.default_text = default_text
        self.default_confidence = default_confidence
        self.char_confidences = char_confidences or [0.95] * len(default_text)
        self.return_none = return_none

    async def recognize_plate(
        self,
        plate_detection: PlateDetectionResult,
    ) -> Optional[OCRResult]:
        if self.return_none:
            return None

        return OCRResult(
            raw_text=self.default_text,
            confidence=self.default_confidence,
            char_confidences=self.char_confidences,
            model_name="mock-paddleocr",
            metadata={"inference_time_ms": 12.5},
        )
