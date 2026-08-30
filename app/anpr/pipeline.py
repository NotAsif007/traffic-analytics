"""ANPR Pipeline Orchestrator.

Sequences:
Frame -> Vehicle Detection -> Plate Detection -> Plate OCR -> Normalization -> VehicleObservationCreate.
"""

from __future__ import annotations

import uuid
from typing import Optional

from app.anpr.contracts import (
    FrameInput,
    ObservationCandidate,
)
from app.anpr.interfaces import PlateDetector, PlateOCR, VehicleDetector
from app.anpr.matcher import propagate_observation_confidence
from app.anpr.normalizer import OCRNormalizer
from app.core.logging import get_logger
from app.schemas.vehicle_observation import VehicleObservationCreate

logger = get_logger(__name__)


class ANPRPipeline:
    """
    End-to-end inference pipeline service.

    Orchestrates the pluggable AI components without coupling to any specific
    computer vision or OCR library.
    """

    def __init__(
        self,
        vehicle_detector: VehicleDetector,
        plate_detector: PlateDetector,
        plate_ocr: PlateOCR,
        normalizer: Optional[OCRNormalizer] = None,
        source_name: str = "anpr-pipeline-v1",
    ) -> None:
        self.vehicle_detector = vehicle_detector
        self.plate_detector = plate_detector
        self.plate_ocr = plate_ocr
        self.normalizer = normalizer or OCRNormalizer()
        self.source_name = source_name

    async def process_frame(
        self,
        frame: FrameInput,
    ) -> list[VehicleObservationCreate]:
        """
        Process a single frame through the complete ANPR pipeline.

        Returns a list of standardized `VehicleObservationCreate` records
        ready for direct ingestion into the backend domain layer.
        """
        # Step 1: Detect vehicles
        vehicle_detections = await self.vehicle_detector.detect_vehicles(frame)
        if not vehicle_detections:
            logger.debug("anpr.no_vehicles_detected", camera_id=str(frame.camera_id))
            return []

        observations: list[VehicleObservationCreate] = []

        for idx, v_det in enumerate(vehicle_detections):
            # Step 2: Detect license plate within vehicle ROI
            plate_det = await self.plate_detector.detect_plate(frame, v_det)

            # Step 3: Run OCR on plate if localized
            ocr_res = None
            normalized_plate = None
            if plate_det is not None:
                ocr_res = await self.plate_ocr.recognize_plate(plate_det)
                if ocr_res is not None and ocr_res.raw_text:
                    norm_result = self.normalizer.normalize(
                        raw_text=ocr_res.raw_text,
                        confidence=ocr_res.confidence,
                    )
                    normalized_plate = norm_result.normalized_text

            # Step 4: Calculate combined confidence
            eff_confidence = propagate_observation_confidence(
                detection_confidence=v_det.confidence,
                plate_confidence=ocr_res.confidence if ocr_res else None,
            )

            # Step 5: Build unique source observation ID
            obs_tag = (
                f"{frame.camera_id}_{frame.observed_at.strftime('%Y%m%d%H%M%S%f')}_{idx}"
            )

            # Step 6: Construct normalized domain payload
            obs_payload = VehicleObservationCreate(
                source=self.source_name,
                source_observation_id=obs_tag,
                camera_id=frame.camera_id,
                observed_at=frame.observed_at,
                frame_number=frame.frame_number,
                vehicle_class=v_det.vehicle_class,
                vehicle_color=v_det.vehicle_color,
                bounding_box=v_det.bbox,
                detection_confidence=v_det.confidence,
                plate_text=normalized_plate if normalized_plate else (ocr_res.raw_text if ocr_res else None),
                plate_confidence=ocr_res.confidence if ocr_res else None,
                plate_bbox=plate_det.bbox if plate_det else None,
                plate_region=plate_det.plate_region if plate_det else None,
                frame_path=frame.frame_path,
                crop_path=v_det.crop_path,
                plate_crop_path=plate_det.plate_crop_path if plate_det else None,
                metadata={
                    "effective_confidence": eff_confidence,
                    "pipeline_source": self.source_name,
                    "ocr_raw_text": ocr_res.raw_text if ocr_res else None,
                    "ocr_model": ocr_res.model_name if ocr_res else None,
                },
            )
            observations.append(obs_payload)

        logger.info(
            "anpr.frame_processed",
            camera_id=str(frame.camera_id),
            vehicles_found=len(observations),
        )
        return observations
