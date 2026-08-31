"""Real License Plate Detector Implementation.

Localizes license plate regions within vehicle bounding boxes using edge/contour analysis
and aspect ratio filtering optimized for Indian HSRP (High Security Registration Plate) layouts.
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from app.anpr.contracts import FrameInput, PlateDetectionResult, VehicleDetectionResult
from app.anpr.interfaces import PlateDetector
from app.core.logging import get_logger
from app.schemas.vehicle_observation import BoundingBox

logger = get_logger(__name__)

PLATE_CROP_DIR = Path(
    os.environ.get("PLATE_CROP_DIR", Path(__file__).parent.parent.parent / "data" / "plate_crops")
)


class RealPlateDetector(PlateDetector):
    """
    Real license plate detector and ROI localizer.
    """

    def __init__(self, save_crops: bool = True) -> None:
        self.save_crops = save_crops
        PLATE_CROP_DIR.mkdir(parents=True, exist_ok=True)

    async def detect_plate(
        self,
        frame: FrameInput,
        vehicle_detection: VehicleDetectionResult,
    ) -> PlateDetectionResult | None:
        """
        Detect and crop license plate within the vehicle detection region.
        """
        # Read vehicle image (from crop or full frame)
        if vehicle_detection.crop_path and os.path.exists(vehicle_detection.crop_path):
            veh_img = cv2.imread(vehicle_detection.crop_path)
        elif os.path.exists(frame.frame_path):
            full_img = cv2.imread(frame.frame_path)
            if full_img is None:
                return None
            fh, fw = full_img.shape[:2]
            vx1 = int(vehicle_detection.bbox.x1 * fw)
            vy1 = int(vehicle_detection.bbox.y1 * fh)
            vx2 = int(vehicle_detection.bbox.x2 * fw)
            vy2 = int(vehicle_detection.bbox.y2 * fh)
            veh_img = full_img[vy1:vy2, vx1:vx2]
        else:
            return None

        if veh_img is None or veh_img.size == 0:
            return None

        vh, vw = veh_img.shape[:2]
        if vh < 20 or vw < 20:
            return None

        # Detect candidate plate ROI
        plate_box, conf = self._find_plate_roi(veh_img)
        if plate_box is None:
            # Fallback to lower-central 40% of the vehicle (where Indian plates are mounted)
            px1, py1, px2, py2 = int(vw * 0.25), int(vh * 0.60), int(vw * 0.75), int(vh * 0.90)
            conf = 0.65
        else:
            px1, py1, px2, py2 = plate_box

        # Normalize relative to full frame
        vx1_norm = vehicle_detection.bbox.x1
        vy1_norm = vehicle_detection.bbox.y1
        vw_norm = vehicle_detection.bbox.x2 - vehicle_detection.bbox.x1
        vh_norm = vehicle_detection.bbox.y2 - vehicle_detection.bbox.y1

        norm_px1 = vx1_norm + (px1 / vw) * vw_norm
        norm_py1 = vy1_norm + (py1 / vh) * vh_norm
        norm_px2 = vx1_norm + (px2 / vw) * vw_norm
        norm_py2 = vy1_norm + (py2 / vh) * vh_norm

        plate_crop_path = None
        plate_crop = veh_img[py1:py2, px1:px2]
        if self.save_crops and plate_crop.size > 0:
            crop_filename = f"plate_{frame.camera_id}_{frame.observed_at.strftime('%Y%m%d%H%M%S%f')}.jpg"
            crop_file = PLATE_CROP_DIR / crop_filename
            cv2.imwrite(str(crop_file), plate_crop)
            plate_crop_path = str(crop_file)

        return PlateDetectionResult(
            bbox=BoundingBox(
                x1=round(norm_px1, 4),
                y1=round(norm_py1, 4),
                x2=round(norm_px2, 4),
                y2=round(norm_py2, 4),
            ),
            confidence=round(conf, 4),
            plate_crop_path=plate_crop_path,
            plate_region="IND",
            metadata={
                "localizer": "contour_hsrp_filter",
                "pixel_box": [px1, py1, px2, py2],
            },
        )

    def _find_plate_roi(self, veh_img: np.ndarray) -> tuple[tuple[int, int, int, int] | None, float]:
        """Find rectangular candidate region with aspect ratio 2.0 - 5.5."""
        vh, vw = veh_img.shape[:2]
        gray = cv2.cvtColor(veh_img, cv2.COLOR_BGR2GRAY)

        # Bilateral filter for noise removal while keeping edges sharp
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)
        # Edge detection
        edged = cv2.Canny(blurred, 50, 200)

        contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)

            # Look for 4-corner polygons (rectangles)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = float(w) / max(1, h)
                # Indian HSRP plates typically have aspect ratio 2.5 to 5.2 and lower vehicle placement
                if 2.0 <= aspect_ratio <= 5.8 and w > 40 and h > 12 and y + h > vh * 0.35:
                    return (x, y, x + w, y + h), 0.92

        return None, 0.0
