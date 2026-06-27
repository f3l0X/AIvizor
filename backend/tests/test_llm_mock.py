"""Tests del `MockProvider`. Verifican que cumple el contrato `LLMProvider`."""

from __future__ import annotations

import pytest

from app.llm.base import LLMError, LLMProvider
from app.llm.mock import MockProvider
from app.schemas import AnalysisResult, Language, TrainingSample, Verdict


class _Unsupported:
    pass


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


def test_mock_implements_protocol(provider: MockProvider) -> None:
    assert isinstance(provider, LLMProvider)
    assert provider.name == "mock"


async def test_mock_returns_valid_analysis(provider: MockProvider) -> None:
    result = await provider.complete_structured(
        system="ignored",
        user="Hola, este es un correo de prueba muy sospechoso.",
        response_model=AnalysisResult,
        language=Language.ES,
    )
    assert isinstance(result, AnalysisResult)
    assert 0 <= result.risk_score <= 100
    assert result.verdict in Verdict
    assert result.language is Language.ES
    assert len(result.indicators) >= 1


async def test_mock_is_deterministic(provider: MockProvider) -> None:
    payload = "Same input twice should produce same output"
    a = await provider.complete_structured(
        system="x", user=payload, response_model=AnalysisResult, language=Language.EN
    )
    b = await provider.complete_structured(
        system="x", user=payload, response_model=AnalysisResult, language=Language.EN
    )
    assert a.risk_score == b.risk_score
    assert a.verdict == b.verdict


async def test_mock_supports_training_sample(provider: MockProvider) -> None:
    sample = await provider.complete_structured(
        system="x",
        user="train me",
        response_model=TrainingSample,
        language=Language.ES,
    )
    assert isinstance(sample, TrainingSample)
    assert sample.language is Language.ES
    assert sample.true_verdict in Verdict


async def test_mock_rejects_unknown_model(provider: MockProvider) -> None:
    with pytest.raises(LLMError) as exc:
        await provider.complete_structured(
            system="x",
            user="y",
            response_model=_Unsupported,  # type: ignore[type-var]
            language=Language.ES,
        )
    assert exc.value.provider == "mock"
