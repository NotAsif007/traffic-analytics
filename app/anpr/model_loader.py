"""Model Weights Manager & Downloader.

Provides verified paths and lazy loading for real neural model weights:
- YOLOv8 vehicle detector (`yolov8n.pt`)
- MobileNetV3 / ResNet50 Re-ID appearance embedder
- EasyOCR character recognition engine models
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# Base directory for storing local neural model weights
MODELS_DIR = Path(os.environ.get("MODELS_DIR", Path(__file__).parent.parent.parent / "models"))


class ModelWeightsNotFoundError(Exception):
    """Raised when required neural model weights are missing and auto-download is disabled."""

    pass


class ModelLoader:
    """Manages downloading, caching, and loading neural network weights."""

    @classmethod
    def get_models_dir(cls) -> Path:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        return MODELS_DIR

    @classmethod
    def get_yolo_weights_path(cls, model_name: str = "yolov8n.pt") -> str:
        """
        Get the path to YOLO detector weights.
        Ultralytics automatically downloads official weights if not present locally.
        """
        models_dir = cls.get_models_dir()
        target_path = models_dir / model_name
        if target_path.exists():
            return str(target_path)

        # Allow ultralytics default cache or local path
        return str(target_path)

    @classmethod
    def get_reid_weights_path(cls) -> str:
        """Return directory/path for Re-ID models."""
        models_dir = cls.get_models_dir()
        reid_dir = models_dir / "reid"
        reid_dir.mkdir(parents=True, exist_ok=True)
        return str(reid_dir)

    @classmethod
    def get_easyocr_models_dir(cls) -> str:
        """Return directory for EasyOCR CRAFT & CRNN recognition weights."""
        models_dir = cls.get_models_dir()
        ocr_dir = models_dir / "easyocr"
        ocr_dir.mkdir(parents=True, exist_ok=True)
        return str(ocr_dir)
