"""Tests del contrato: los esquemas Pydantic son la fuente de verdad."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalysisResult,
    Indicator,
    IndicatorType,
    Language,
    Verdict,
)


def test_analysis_result_valid() -> None:
    result = AnalysisResult(
        risk_score=75,
        verdict=Verdict.PHISHING,
        language=Language.ES,
        summary="Phishing claro.",
        indicators=[
            Indicator(
                type=IndicatorType.URGENCY_LANGUAGE,
                evidence="¡Verifica ahora!",
                explanation="La urgencia es una palanca clásica.",
            )
        ],
    )
    assert result.risk_score == 75


def test_risk_score_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalysisResult(
            risk_score=150,
            verdict=Verdict.PHISHING,
            language=Language.ES,
            summary="x",
        )


def test_indicator_type_must_be_in_catalog() -> None:
    with pytest.raises(ValidationError):
        Indicator(
            type="invented_type",  # type: ignore[arg-type]
            evidence="x",
            explanation="y",
        )


def test_summary_required() -> None:
    with pytest.raises(ValidationError):
        AnalysisResult(
            risk_score=10,
            verdict=Verdict.LEGIT,
            language=Language.EN,
        )  # type: ignore[call-arg]
