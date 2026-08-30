"""Abstract interfaces / contracts for ANPR and computer vision components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.anpr.contracts import (
    FrameInput,
    OCRResult,
    PlateDetectionResult,
    VehicleDetectionResult,
)


class VehicleDetector(ABC):
    """
    Abstract interface for vehicle detection models (e.g. YOLOv8, Faster R-CNN).

    Takes a frame reference or image input and returns localized vehicle bounding boxes
    with classifications and confidence scores.
    """

    @abstractmethod
    async def detect_vehicles(
        self,
        frame: FrameInput,
    ) -> list[VehicleDetectionResult]:
        """Detect all vehicles in a given frame."""
        pass


class PlateDetector(ABC):
    """
    Abstract interface for license plate localization models (e.g. LPRNet, YOLO-Plate).

    Operates either on the full frame or on a specific vehicle crop.
    """

    @abstractmethod
    async def detect_plate(
        self,
        frame: FrameInput,
        vehicle_detection: VehicleDetectionResult,
    ) -> Optional[PlateDetectionResult]:
        """
        Detect and localize license plate within a vehicle detection region.
        Returns None if no plate is detected.
        """
        pass


class PlateOCR(ABC):
    """
    Abstract interface for optical character recognition models (e.g. PaddleOCR, EasyOCR).

    Reads alphanumeric characters from a localized plate crop without guessing ground truth.
    """

    @abstractmethod
    async def recognize_plate(
        self,
        plate_detection: PlateDetectionResult,
    ) -> Optional[OCRResult]:
        """
        Extract text and character confidences from plate crop.
        Returns None if OCR fails or text cannot be recognized.
        """
        pass
