"""Tests del contrato: los esquemas Pydantic son la fuente de verdad."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalysisResult,
    Indicator,
    IndicatorType,
    Language,
    Verdict,
)
from app.schemas.analysis import AnalyzeRequest
from app.schemas.common import InputType
from app.schemas.training import TrainingAnswer


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


# --- Endurecimiento de entrada (Fase 7.7) -----------------------------------


def test_analyze_content_strips_null_bytes() -> None:
    req = AnalyzeRequest(content="hola\x00mundo", input_type=InputType.EMAIL)
    assert req.content == "holamundo"


def test_analyze_content_only_null_bytes_rejected() -> None:
    # Tras limpiar queda vacío → min_length=1 lo rechaza.
    with pytest.raises(ValidationError):
        AnalyzeRequest(content="\x00\x00", input_type=InputType.EMAIL)


def test_training_answer_marked_types_list_capped() -> None:
    with pytest.raises(ValidationError):
        TrainingAnswer(
            sample_id=uuid4(),
            user_verdict=Verdict.PHISHING,
            marked_indicator_types=[f"type_{i}" for i in range(21)],  # > 20
        )


def test_training_answer_marked_type_item_capped() -> None:
    with pytest.raises(ValidationError):
        TrainingAnswer(
            sample_id=uuid4(),
            user_verdict=Verdict.PHISHING,
            marked_indicator_types=["x" * 51],  # item > 50 chars
        )


def test_training_answer_valid_marked_types_ok() -> None:
    answer = TrainingAnswer(
        sample_id=uuid4(),
        user_verdict=Verdict.LEGIT,
        marked_indicator_types=["urgency_language", "credential_request"],
    )
    assert len(answer.marked_indicator_types) == 2
