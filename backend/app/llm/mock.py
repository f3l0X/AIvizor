"""`MockProvider` — implementación determinista de `LLMProvider`.

Razón de ser:
  1. **Tests sin coste.** El CI no debe llamar a APIs externas.
  2. **Dev local sin API key.** ``LLM_PROVIDER=mock`` y arrancas.
  3. **Doble función como contrato.** Si añades un campo al esquema y olvidas
     actualizar el mock, los tests fallan: te obliga a mantenerlo coherente.

No intenta "imitar" la inteligencia del LLM; sólo devuelve un objeto válido del
``response_model`` pedido. Los servicios prueban su lógica contra esta salida fija.
"""

from __future__ import annotations

import hashlib
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.llm.base import LLMError
from app.schemas.analysis import AnalysisResult, Indicator
from app.schemas.common import Difficulty, IndicatorType, InputType, Language, Verdict
from app.schemas.training import TrainingSample

T = TypeVar("T", bound=BaseModel)


def _stable_score(seed: str) -> int:
    """Score 0-100 derivado del input. Determinista entre llamadas."""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return h[0] * 100 // 255


def _verdict_for(score: int) -> Verdict:
    if score < 30:
        return Verdict.LEGIT
    if score < 70:
        return Verdict.SUSPICIOUS
    return Verdict.PHISHING


class MockProvider:
    """Cumple el ``LLMProvider`` Protocol sin tocar la red."""

    name = "mock"

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        language: Language,
    ) -> T:
        if response_model is AnalysisResult:
            return self._mock_analysis(user, language)  # type: ignore[return-value]
        if response_model is TrainingSample:
            return self._mock_training_sample(user, language)  # type: ignore[return-value]
        raise LLMError(
            f"MockProvider no soporta el response_model {response_model.__name__}. "
            "Añade un branch en mock.py.",
            provider=self.name,
        )

    @staticmethod
    def _mock_analysis(user: str, language: Language) -> AnalysisResult:
        score = _stable_score(user)
        verdict = _verdict_for(score)

        if language is Language.ES:
            summary = (
                f"Análisis MOCK: riesgo {score}/100 ({verdict.value}). "
                "Sustituye LLM_PROVIDER por gemini o claude para resultados reales."
            )
            evidence = user[:120] if user else "(sin contenido)"
            explanation = (
                "Indicador de ejemplo generado por MockProvider para validar el "
                "pipeline sin gastar API."
            )
        else:
            summary = (
                f"MOCK analysis: risk {score}/100 ({verdict.value}). "
                "Switch LLM_PROVIDER to gemini or claude for real output."
            )
            evidence = user[:120] if user else "(empty)"
            explanation = (
                "Example indicator emitted by MockProvider so the pipeline can run "
                "without consuming API quota."
            )

        return AnalysisResult(
            risk_score=score,
            verdict=verdict,
            language=language,
            summary=summary,
            indicators=[
                Indicator(
                    type=IndicatorType.OTHER,
                    evidence=evidence,
                    explanation=explanation,
                )
            ],
        )

    @staticmethod
    def _mock_training_sample(user: str, language: Language) -> TrainingSample:
        score = _stable_score(user)
        verdict = _verdict_for(score)
        sample_id = UUID(bytes=hashlib.sha256(user.encode("utf-8")).digest()[:16])

        content_es = (
            "Estimado cliente: Por motivos de seguridad debe verificar su cuenta "
            "haciendo clic aquí: http://banco-seguro.example/verify. ¡Acción inmediata!"
        )
        content_en = (
            "Dear customer: For security reasons please verify your account by "
            "clicking here: http://secure-bank.example/verify. Immediate action required!"
        )
        content = content_es if language is Language.ES else content_en

        return TrainingSample(
            id=sample_id,
            input_type=InputType.EMAIL,
            language=language,
            difficulty=Difficulty.L2,
            content=content,
            true_verdict=verdict,
            true_indicators=[
                Indicator(
                    type=IndicatorType.URGENCY_LANGUAGE,
                    evidence="¡Acción inmediata!" if language is Language.ES else "Immediate action required!",
                    explanation=(
                        "El uso de urgencia para forzar a actuar sin pensar es típico de phishing."
                        if language is Language.ES
                        else "Pressuring the reader to act without thinking is a classic phishing tactic."
                    ),
                ),
            ],
        )
