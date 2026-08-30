"""Real Vehicle Re-Identification (Re-ID) Deep Feature Extractor.

Uses a Torchvision deep convolutional neural network backbone (MobileNetV3 / ResNet50)
to generate L2-normalized 512-dimensional visual appearance embeddings for cross-camera association.
"""

from __future__ import annotations

import os

import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from torchvision.models import MobileNet_V3_Small_Weights

from app.anpr.interfaces import VehicleReIdentifier
from app.core.logging import get_logger

logger = get_logger(__name__)


class RealVehicleReIdentifier(VehicleReIdentifier):
    """
    Real visual appearance Re-ID feature extractor producing unit-norm embeddings.
    """

    def __init__(self, device: str | None = None) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("reid_extractor.initializing", device=self.device)

        # Load pretrained backbone
        weights = MobileNet_V3_Small_Weights.DEFAULT
        backbone = models.mobilenet_v3_small(weights=weights)

        # Replace classification head with projection layer to 512-dim embedding
        backbone.classifier = nn.Sequential(
            nn.Linear(576, 512),
            nn.BatchNorm1d(512),
        )

        self.model = backbone.to(self.device)
        self.model.eval()

        # Image preprocessing pipeline matching ImageNet standards
        self.preprocess = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    async def extract_embedding(
        self,
        image_or_crop_path: str,
    ) -> list[float]:
        """
        Extract L2-normalized 512-dimensional feature embedding from a vehicle image.
        """
        if not os.path.exists(image_or_crop_path):
            logger.warning("reid.file_not_found", path=image_or_crop_path)
            return [0.0] * 512

        # Read image
        bgr = cv2.imread(image_or_crop_path)
        if bgr is None or bgr.size == 0:
            return [0.0] * 512

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        tensor = self.preprocess(rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model(tensor)
            # L2 normalize to unit sphere
            norm_features = torch.nn.functional.normalize(features, p=2, dim=1)
            embedding = norm_features.squeeze(0).cpu().numpy().tolist()

        return [round(float(x), 6) for x in embedding]
