"""Evaluation and benchmarking data contracts, ground-truth schemas, and report models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.schemas.common import AppBaseModel
from app.schemas.vehicle_observation import BoundingBox

# ---------------------------------------------------------------------------
# Ground Truth Definitions
# ---------------------------------------------------------------------------


class GroundTruthObservation(AppBaseModel):
    """Ground truth state of a vehicle observation at a camera."""

    observation_id: str
    camera_id: uuid.UUID
    camera_name: str
    timestamp: datetime
    true_vehicle_id: str
    true_plate: str
    true_class: str
    true_color: str
    true_bbox: BoundingBox
    true_plate_bbox: BoundingBox | None = None
    simulated_ocr_plate: str | None = None  # May contain simulated noise/errors
    simulated_ocr_confidence: float | None = None
    is_blacklisted: bool = False
    is_speed_anomaly: bool = False
    is_route_anomaly: bool = False


class GroundTruthVehicle(AppBaseModel):
    """Ground truth identity and journey of a physical vehicle."""

    vehicle_id: str
    plate: str
    vehicle_class: str
    vehicle_color: str
    is_blacklisted: bool = False
    route_camera_names: list[str] = Field(default_factory=list)
    observations: list[GroundTruthObservation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Evaluation Metrics Schemas
# ---------------------------------------------------------------------------


class ANPRMetrics(AppBaseModel):
    total_ground_truth_plates: int
    total_detected_plates: int
    detection_true_positives: int
    detection_false_positives: int
    detection_false_negatives: int
    detection_precision: float = Field(..., ge=0.0, le=1.0)
    detection_recall: float = Field(..., ge=0.0, le=1.0)
    detection_f1: float = Field(..., ge=0.0, le=1.0)
    exact_plate_matches: int
    exact_plate_accuracy: float = Field(..., ge=0.0, le=1.0)
    normalized_plate_accuracy: float = Field(..., ge=0.0, le=1.0)
    average_character_accuracy: float = Field(..., ge=0.0, le=1.0)
    mean_ocr_confidence: float = Field(..., ge=0.0, le=1.0)


class TrackingMetrics(AppBaseModel):
    total_ground_truth_tracks: int
    total_predicted_tracks: int
    id_switches: int
    mostly_tracked_tracks: int
    mostly_lost_tracks: int
    mota: float
    idf1: float = Field(..., ge=0.0, le=1.0)


class AssociationMetrics(AppBaseModel):
    total_ground_truth_vehicles: int
    total_predicted_identities: int
    correct_associations_tp: int
    false_associations_fp: int
    missed_associations_fn: int
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    trajectory_completeness_rate: float = Field(..., ge=0.0, le=1.0)


class AlertMetrics(AppBaseModel):
    total_ground_truth_anomalies: int
    total_alerts_generated: int
    true_positive_alerts: int
    false_positive_alerts: int
    false_negative_alerts: int
    true_negative_samples: int
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    false_positive_rate: float = Field(..., ge=0.0, le=1.0)


class EvaluationReport(AppBaseModel):
    """
    Comprehensive machine-readable evaluation report across all system layers.
    """

    benchmark_name: str
    evaluation_timestamp: datetime
    dataset_summary: dict[str, Any]
    anpr: ANPRMetrics
    tracking: TrackingMetrics
    association: AssociationMetrics
    alerts: AlertMetrics
    overall_system_score: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(populate_by_name=True)
