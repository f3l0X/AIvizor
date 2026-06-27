"""Tests del servicio `analyze_content` con MockProvider + InMemoryRepository."""

from __future__ import annotations

import pytest

from app.db.repositories import InMemoryAnalysisRepository
from app.llm.base import LLMError, LLMProvider
from app.llm.mock import MockProvider
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.schemas.common import InputType, Language, Verdict
from app.services.analyzer import analyze_content


async def test_analyze_returns_validated_result(
    mock_provider: MockProvider,
    in_memory_repo: InMemoryAnalysisRepository,
) -> None:
    req = AnalyzeRequest(
        content="¡Verifica tu cuenta ya o se bloqueará!",
        input_type=InputType.EMAIL,
        language=Language.ES,
    )
    result = await analyze_content(req, llm=mock_provider, repo=in_memory_repo)

    assert isinstance(result, AnalysisResult)
    assert result.language is Language.ES
    assert result.verdict in Verdict


async def test_analyze_persists_via_repository(
    mock_provider: MockProvider,
    in_memory_repo: InMemoryAnalysisRepository,
) -> None:
    req = AnalyzeRequest(
        content="Suspicious URL https://bnak-of-america.example",
        input_type=InputType.URL,
        language=Language.EN,
    )
    await analyze_content(req, llm=mock_provider, repo=in_memory_repo)

    assert len(in_memory_repo.items) == 1
    item = in_memory_repo.items[0]
    assert item["input_type"] == "url"
    assert item["result"]["language"] == "en"


async def test_language_mismatch_is_normalized(
    in_memory_repo: InMemoryAnalysisRepository,
) -> None:
    """Si el LLM jura que respondió en otro idioma, ganamos nosotros."""

    class WrongLanguageProvider:
        name = "wrong"

        async def complete_structured(self, *, system, user, response_model, language):
            mock = MockProvider()
            r = await mock.complete_structured(
                system=system, user=user, response_model=response_model, language=Language.EN
            )
            return r.model_copy(update={"language": Language.EN})

    req = AnalyzeRequest(
        content="Cualquier cosa",
        input_type=InputType.SMS,
        language=Language.ES,
    )
    result = await analyze_content(req, llm=WrongLanguageProvider(), repo=in_memory_repo)  # type: ignore[arg-type]
    assert result.language is Language.ES


async def test_llm_error_propagates(
    in_memory_repo: InMemoryAnalysisRepository,
) -> None:
    class FailingProvider:
        name = "failing"

        async def complete_structured(self, **_kw) -> object:
            raise LLMError("simulated failure", provider="failing")

    req = AnalyzeRequest(content="x", input_type=InputType.EMAIL, language=Language.ES)
    with pytest.raises(LLMError):
        await analyze_content(req, llm=FailingProvider(), repo=in_memory_repo)  # type: ignore[arg-type]
    assert in_memory_repo.items == []


async def test_provider_implements_protocol() -> None:
    assert isinstance(MockProvider(), LLMProvider)
