"""Real License Plate Optical Character Recognition (OCR) Engine.

Uses EasyOCR (CRAFT detector + ResNet-CRNN CTC sequence model)
to extract text and per-character confidence metrics from cropped license plates.
"""

from __future__ import annotations

import os

import cv2
import easyocr
import numpy as np

from app.anpr.contracts import OCRResult, PlateDetectionResult
from app.anpr.interfaces import PlateOCR
from app.anpr.model_loader import ModelLoader
from app.core.logging import get_logger

logger = get_logger(__name__)


class RealPlateOCR(PlateOCR):
    """
    Real Optical Character Recognition engine powered by EasyOCR.
    """

    def __init__(self, languages: list[str] | None = None, gpu: bool = False) -> None:
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.model_dir = ModelLoader.get_easyocr_models_dir()
        logger.info("easyocr.initializing", languages=self.languages, gpu=self.gpu)
        self.reader = easyocr.Reader(
            self.languages,
            gpu=self.gpu,
            model_storage_directory=self.model_dir,
            verbose=False,
        )

    async def recognize_plate(
        self,
        plate_detection: PlateDetectionResult,
    ) -> OCRResult | None:
        """
        Run OCR on the localized plate crop image.
        """
        crop_path = plate_detection.plate_crop_path
        if not crop_path or not os.path.exists(crop_path):
            return None

        # Read image
        img = cv2.imread(crop_path)
        if img is None or img.size == 0:
            return None

        # Preprocess plate image for OCR: upscale if small + contrast enhancement
        processed_img = self._preprocess_for_ocr(img)

        # Run EasyOCR
        try:
            results = self.reader.readtext(
                processed_img,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            )
        except Exception as e:
            logger.warning("ocr.inference_failed", error=str(e))
            return None

        if not results:
            return None

        # Combine text segments (ignoring isolated "IND" / "IN" HSRP country tag if multiple segments)
        text_segments: list[str] = []
        confidences: list[float] = []
        has_hsrp_badge = False

        for _bbox, text, conf in results:
            cleaned = "".join(c for c in text.upper() if c.isalnum())
            if not cleaned:
                continue
            if cleaned in ["IND", "IN"] and len(results) > 1:
                has_hsrp_badge = True
                continue
            text_segments.append(cleaned)
            confidences.append(float(conf))

        if not text_segments:
            # If only "IND" was found, return it as raw text
            for _bbox, text, conf in results:
                cleaned = "".join(c for c in text.upper() if c.isalnum())
                if cleaned:
                    text_segments.append(cleaned)
                    confidences.append(float(conf))

        if not text_segments:
            return None

        full_raw_text = "".join(text_segments)
        if full_raw_text.startswith("IND") and len(full_raw_text) > 7:
            full_raw_text = full_raw_text[3:]
            has_hsrp_badge = True

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5

        # Build approximate per-character confidences from segment scores
        char_confidences: list[float] = []
        for text, conf in zip(text_segments, confidences, strict=False):
            char_confidences.extend([round(conf, 4)] * len(text))

        # Ensure length matches exactly
        if len(char_confidences) != len(full_raw_text):
            char_confidences = [round(avg_conf, 4)] * len(full_raw_text)

        return OCRResult(
            raw_text=full_raw_text,
            confidence=round(avg_conf, 4),
            char_confidences=char_confidences,
            model_name="easyocr-v1.7.2",
            metadata={
                "segment_count": len(text_segments),
                "segments": text_segments,
                "is_hsrp_badge": has_hsrp_badge,
            },
        )


    def _preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """Upscale and enhance contrast of plate crop."""
        h, w = img.shape[:2]
        # Target minimum height of 64px for CRAFT text detector
        if h < 64:
            scale = 64.0 / h
            img = cv2.resize(img, (int(w * scale), 64), interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        return enhanced
