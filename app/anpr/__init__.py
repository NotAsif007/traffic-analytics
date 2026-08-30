"""ANPR and AI model integration package."""

from app.anpr.contracts import (
    FrameInput,
    ObservationCandidate,
    OCRResult,
    PlateDetectionResult,
    VehicleDetectionResult,
)
from app.anpr.interfaces import PlateDetector, PlateOCR, VehicleDetector
from app.anpr.matcher import (
    PlateMatcher,
    PlateMatchResult,
    is_partial_match,
    levenshtein_distance,
    levenshtein_similarity,
    propagate_observation_confidence,
)
from app.anpr.mock import MockPlateDetector, MockPlateOCR, MockVehicleDetector
from app.anpr.normalizer import NormalizedPlate, OCRNormalizer, TransformationStep
from app.anpr.pipeline import ANPRPipeline

__all__ = [
    "FrameInput",
    "VehicleDetectionResult",
    "PlateDetectionResult",
    "OCRResult",
    "ObservationCandidate",
    "VehicleDetector",
    "PlateDetector",
    "PlateOCR",
    "OCRNormalizer",
    "NormalizedPlate",
    "TransformationStep",
    "PlateMatcher",
    "PlateMatchResult",
    "levenshtein_distance",
    "levenshtein_similarity",
    "is_partial_match",
    "propagate_observation_confidence",
    "ANPRPipeline",
    "MockVehicleDetector",
    "MockPlateDetector",
    "MockPlateOCR",
]
