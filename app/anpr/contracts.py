"""ANPR and AI model integration contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field, model_validator

from app.schemas.common import AppBaseModel
from app.schemas.vehicle_observation import BoundingBox


# ---------------------------------------------------------------------------
# Frame / Input contracts
# ---------------------------------------------------------------------------

class FrameInput(AppBaseModel):
    """
    Input representing a single image or video frame to be processed.

    Carries camera context and metadata without requiring raw binary payload
    in the domain layer.
    """
    camera_id: uuid.UUID
    observed_at: datetime
    frame_path: str = Field(..., description="URI or path to image in storage / local filesystem")
    frame_number: Optional[int] = Field(None, ge=0)
    source: str = Field(default="anpr-pipeline", description="Inference pipeline tag")
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


# ---------------------------------------------------------------------------
# Inference Output Contracts
# ---------------------------------------------------------------------------

class VehicleDetectionResult(AppBaseModel):
    """
    Standardized inference result from a vehicle detector (e.g. YOLO, Faster-RCNN).
    """
    bbox: BoundingBox
    vehicle_class: str = Field(..., examples=["car", "truck", "motorcycle", "bus"])
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    vehicle_color: Optional[str] = Field(None, examples=["white", "black", "silver"])
    crop_path: Optional[str] = Field(None, description="Storage path to the cropped vehicle image")
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class PlateDetectionResult(AppBaseModel):
    """
    Standardized inference result from a license plate detector / localizer.
    """
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0, description="Plate localization confidence")
    plate_crop_path: Optional[str] = Field(None, description="Storage path to the cropped plate image")
    plate_region: Optional[str] = Field(None, description="Predicted country/state code (e.g. KA, MH, IN)")
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class OCRResult(AppBaseModel):
    """
    Standardized result from an optical character recognition engine.

    Never represents OCR as absolute ground truth. Preserves raw text,
    overall confidence, optional per-character confidences, and model details.
    """
    raw_text: str = Field(..., description="Raw text output from OCR model")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall OCR confidence score")
    char_confidences: Optional[list[float]] = Field(
        default=None,
        description="Per-character confidence scores matching raw_text characters",
    )
    model_name: Optional[str] = Field(None, examples=["paddleocr-v4", "crnn-v1"])
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")

    @model_validator(mode="after")
    def validate_char_confidences(self) -> OCRResult:
        if self.char_confidences is not None:
            # Check length matches non-whitespace characters or raw string
            for conf in self.char_confidences:
                if not (0.0 <= conf <= 1.0):
                    raise ValueError(f"Character confidence {conf} out of range [0.0, 1.0]")
        return self


# ---------------------------------------------------------------------------
# Consolidated Inference Candidate
# ---------------------------------------------------------------------------

class ObservationCandidate(AppBaseModel):
    """
    Consolidated detection and recognition candidate for a single vehicle sighting.
    """
    vehicle_detection: VehicleDetectionResult
    plate_detection: Optional[PlateDetectionResult] = None
    ocr_result: Optional[OCRResult] = None
    normalized_plate: Optional[str] = None
    effective_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Propagated confidence combining detection and OCR"
    )
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")
