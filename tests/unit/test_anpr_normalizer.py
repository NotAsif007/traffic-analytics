"""Unit tests for traceable OCR plate text normalization."""

from __future__ import annotations

import pytest

from app.anpr.normalizer import OCRNormalizer


@pytest.mark.unit
def test_normalizer_strips_separators_and_spaces() -> None:
    norm = OCRNormalizer(strip_separators=True, to_uppercase=False)
    res = norm.normalize(" AS-01 AB.1234 ", confidence=0.95)

    assert res.normalized_text == "AS01AB1234"
    assert res.was_modified is True
    assert len(res.transformations) == 1
    assert res.transformations[0].rule == "strip_separators"
    assert res.raw_confidence == 0.95
    assert res.adjusted_confidence == 0.95


@pytest.mark.unit
def test_normalizer_converts_to_uppercase() -> None:
    norm = OCRNormalizer(strip_separators=False, to_uppercase=True)
    res = norm.normalize("as01ab1234", confidence=0.90)

    assert res.normalized_text == "AS01AB1234"
    assert res.was_modified is True
    assert len(res.transformations) == 1
    assert res.transformations[0].rule == "uppercase"


@pytest.mark.unit
def test_normalizer_audit_trail_both_steps() -> None:
    norm = OCRNormalizer(strip_separators=True, to_uppercase=True)
    res = norm.normalize("ka-01 cd 9999", confidence=0.92)

    assert res.normalized_text == "KA01CD9999"
    assert len(res.transformations) == 2
    rules = [t.rule for t in res.transformations]
    assert rules == ["strip_separators", "uppercase"]


@pytest.mark.unit
def test_normalizer_clean_string_no_modifications() -> None:
    norm = OCRNormalizer(strip_separators=True, to_uppercase=True)
    res = norm.normalize("DL01XY1234", confidence=0.98)

    assert res.normalized_text == "DL01XY1234"
    assert res.was_modified is False
    assert len(res.transformations) == 0


@pytest.mark.unit
def test_normalizer_configurable_confusion_mapping() -> None:
    norm = OCRNormalizer(
        strip_separators=True,
        to_uppercase=True,
        enable_confusion_mapping=True,
        confusion_map={"O": "0", "I": "1"},
        confusion_penalty=0.05,
    )
    # 'ASO1AB1234' with letter O instead of 0
    res = norm.normalize("ASO1AB1234", confidence=0.90)

    assert res.normalized_text == "AS01AB1234"
    assert res.was_modified is True
    assert res.adjusted_confidence == 0.85  # 0.90 - 0.05 penalty
    assert any(t.rule == "confusion_mapping" for t in res.transformations)
