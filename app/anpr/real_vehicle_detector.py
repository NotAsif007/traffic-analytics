"""Real YOLOv8 Vehicle Detector Implementation.

Uses Ultralytics YOLOv8 (yolov8n / yolov8s) pretrained on COCO dataset
to detect vehicles (cars, motorcycles, buses, trucks) with bounding boxes,
classes, and confidences.
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from app.anpr.contracts import FrameInput, VehicleDetectionResult
from app.anpr.interfaces import VehicleDetector
from app.anpr.model_loader import ModelLoader
from app.core.logging import get_logger
from app.schemas.vehicle_observation import BoundingBox

logger = get_logger(__name__)

# COCO class IDs for traffic vehicles
COCO_VEHICLE_CLASSES: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# Crop storage directory
CROP_DIR = Path(os.environ.get("CROP_DIR", Path(__file__).parent.parent.parent / "data" / "crops"))


class YOLOv8VehicleDetector(VehicleDetector):
    """
    Real production vehicle detector powered by Ultralytics YOLOv8.
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.35,
        save_crops: bool = True,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.save_crops = save_crops
        self.weights_path = ModelLoader.get_yolo_weights_path(model_name)
        logger.info("yolo_detector.loading", weights=self.weights_path)
        self.model = YOLO(self.weights_path)
        CROP_DIR.mkdir(parents=True, exist_ok=True)

    async def detect_vehicles(
        self,
        frame: FrameInput,
    ) -> list[VehicleDetectionResult]:
        """
        Run YOLOv8 inference on input frame and extract vehicle detections.
        """
        frame_path = frame.frame_path
        if not os.path.exists(frame_path):
            logger.warning("yolo_detector.frame_not_found", path=frame_path)
            return []

        # Read image
        img = cv2.imread(frame_path)
        if img is None:
            logger.error("yolo_detector.image_decode_failed", path=frame_path)
            return []

        h, w = img.shape[:2]

        # Run inference (classes: 2=car, 3=motorcycle, 5=bus, 7=truck)
        results = self.model.predict(
            source=img,
            conf=self.confidence_threshold,
            classes=list(COCO_VEHICLE_CLASSES.keys()),
            verbose=False,
        )

        detections: list[VehicleDetectionResult] = []

        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue

            for idx, box in enumerate(boxes):
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy()

                x1_px, y1_px, x2_px, y2_px = xyxy
                # Normalize coordinates to [0.0, 1.0]
                norm_x1 = max(0.0, min(1.0, float(x1_px / w)))
                norm_y1 = max(0.0, min(1.0, float(y1_px / h)))
                norm_x2 = max(0.0, min(1.0, float(x2_px / w)))
                norm_y2 = max(0.0, min(1.0, float(y2_px / h)))

                vehicle_class = COCO_VEHICLE_CLASSES.get(cls_id, "car")

                # Crop vehicle region
                crop_path = None
                if self.save_crops:
                    ix1, iy1, ix2, iy2 = int(x1_px), int(y1_px), int(x2_px), int(y2_px)
                    crop = img[iy1:iy2, ix1:ix2]
                    if crop.size > 0:
                        crop_filename = f"veh_{frame.camera_id}_{frame.observed_at.strftime('%Y%m%d%H%M%S')}_{idx}.jpg"
                        crop_file = CROP_DIR / crop_filename
                        cv2.imwrite(str(crop_file), crop)
                        crop_path = str(crop_file)

                # Estimate dominant color from vehicle crop
                vehicle_color = self._estimate_dominant_color(img, norm_x1, norm_y1, norm_x2, norm_y2)

                det = VehicleDetectionResult(
                    bbox=BoundingBox(x1=norm_x1, y1=norm_y1, x2=norm_x2, y2=norm_y2),
                    vehicle_class=vehicle_class,
                    confidence=round(conf, 4),
                    vehicle_color=vehicle_color,
                    crop_path=crop_path,
                    metadata={
                        "detector": "yolov8n",
                        "coco_class_id": cls_id,
                        "raw_xyxy": [float(x1_px), float(y1_px), float(x2_px), float(y2_px)],
                    },
                )
                detections.append(det)

        return detections

    def _estimate_dominant_color(
        self,
        img: np.ndarray,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> str:
        """Estimate coarse dominant vehicle color (white, black, red, blue, silver, yellow)."""
        h, w = img.shape[:2]
        ix1, iy1 = int(x1 * w), int(y1 * h)
        ix2, iy2 = int(x2 * w), int(y2 * h)
        crop = img[iy1:iy2, ix1:ix2]
        if crop.size == 0:
            return "white"

        # Convert to HSV
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        h_channel, s_channel, v_channel = cv2.split(hsv)

        mean_v = np.mean(v_channel)
        mean_s = np.mean(s_channel)
        mean_h = np.mean(h_channel)

        if mean_v < 50:
            return "black"
        if mean_s < 35 and mean_v > 180:
            return "white"
        if mean_s < 45:
            return "silver"

        if mean_h < 15 or mean_h > 165:
            return "red"
        elif 20 <= mean_h < 38:
            return "yellow"
        elif 90 <= mean_h < 135:
            return "blue"

        return "white"
