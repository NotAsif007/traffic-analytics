"""Traceable OCR normalization engine.

Design principles:
- Never silently mutate OCR output.
- Track every transformation step (whitespace stripping, uppercasing, character mapping).
- Keep the raw OCR string and original confidence intact.
- Allow configurable confusion mapping with transformation audit trails.
"""

from __future__ import annotations

import re

from pydantic import Field

from app.schemas.common import AppBaseModel

# ---------------------------------------------------------------------------
# Transformation Audit Record
# ---------------------------------------------------------------------------


class TransformationStep(AppBaseModel):
    """Record of a specific text transformation applied during normalization."""

    rule: str = Field(..., description="Name of the transformation rule applied")
    before: str
    after: str
    details: str | None = None


class NormalizedPlate(AppBaseModel):
    """
    Traceable result of plate text normalization.
    """

    raw_text: str = Field(..., description="Original raw text from OCR")
    normalized_text: str = Field(..., description="Cleaned, standardized plate text")
    raw_confidence: float = Field(..., ge=0.0, le=1.0)
    adjusted_confidence: float = Field(..., ge=0.0, le=1.0)
    transformations: list[TransformationStep] = Field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        """True if any transformation changed the text."""
        return self.raw_text != self.normalized_text


# ---------------------------------------------------------------------------
# Default Character Confusion Pairs
# (Maps ambiguous characters to standard representations when enabled)
# ---------------------------------------------------------------------------

DEFAULT_CONFUSION_MAP: dict[str, str] = {
    # Letters to Digits (common in numeric parts)
    "O": "0",
    "I": "1",
    "Z": "2",
    "B": "8",
    "S": "5",
    "G": "6",
}


# ---------------------------------------------------------------------------
# OCR Normalizer
# ---------------------------------------------------------------------------


class OCRNormalizer:
    """
    Configurable, deterministic normalizer for ANPR plate strings.

    Step-by-step:
    1. Strip leading/trailing and internal delimiters (spaces, hyphens, dots)
    2. Convert to uppercase
    3. (Optional) Apply syntax-based or custom character confusion normalization
    4. Maintain audit log of all modifications with confidence adjustments
    """

    def __init__(
        self,
        strip_separators: bool = True,
        to_uppercase: bool = True,
        enable_confusion_mapping: bool = False,
        confusion_map: dict[str, str] | None = None,
        confusion_penalty: float = 0.05,
    ) -> None:
        self.strip_separators = strip_separators
        self.to_uppercase = to_uppercase
        self.enable_confusion_mapping = enable_confusion_mapping
        self.confusion_map = confusion_map or DEFAULT_CONFUSION_MAP
        self.confusion_penalty = confusion_penalty

    def normalize(
        self,
        raw_text: str,
        confidence: float,
    ) -> NormalizedPlate:
        """
        Normalize a raw OCR plate string into a standard format.

        Returns a NormalizedPlate containing the final text, original text,
        confidence, and an audit trail of all applied transformations.
        """
        current_text = raw_text
        current_confidence = confidence
        steps: list[TransformationStep] = []

        # 1. Strip whitespace & common plate delimiters (hyphens, dots, underscores)
        if self.strip_separators:
            cleaned = re.sub(r"[\s\-\._]+", "", current_text)
            if cleaned != current_text:
                steps.append(
                    TransformationStep(
                        rule="strip_separators",
                        before=current_text,
                        after=cleaned,
                        details="Removed spaces, hyphens, and punctuation delimiters",
                    )
                )
                current_text = cleaned

        # 2. Uppercase normalization
        if self.to_uppercase:
            uppercased = current_text.upper()
            if uppercased != current_text:
                steps.append(
                    TransformationStep(
                        rule="uppercase",
                        before=current_text,
                        after=uppercased,
                        details="Converted characters to uppercase",
                    )
                )
                current_text = uppercased

        # 3. Optional Character Confusion Mapping (traceable with confidence penalty)
        if self.enable_confusion_mapping and self.confusion_map:
            transformed_chars: list[str] = []
            modified_count = 0
            for char in current_text:
                if char in self.confusion_map:
                    replacement = self.confusion_map[char]
                    transformed_chars.append(replacement)
                    modified_count += 1
                else:
                    transformed_chars.append(char)

            mapped_text = "".join(transformed_chars)
            if mapped_text != current_text:
                penalty = min(0.3, modified_count * self.confusion_penalty)
                current_confidence = max(0.0, current_confidence - penalty)
                steps.append(
                    TransformationStep(
                        rule="confusion_mapping",
                        before=current_text,
                        after=mapped_text,
                        details=f"Mapped {modified_count} ambiguous characters; applied penalty -{penalty:.2f}",
                    )
                )
                current_text = mapped_text

        return NormalizedPlate(
            raw_text=raw_text,
            normalized_text=current_text,
            raw_confidence=confidence,
            adjusted_confidence=round(current_confidence, 4),
            transformations=steps,
        )
