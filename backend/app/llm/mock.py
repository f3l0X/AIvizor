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


def _infer_difficulty_from_prompt(text: str) -> Difficulty:
    """El servicio del Trainer mete 'dificultad N' / 'difficulty N' en el user prompt."""
    lower = text.lower()
    for level in (5, 4, 3, 2, 1):
        if f"dificultad {level}" in lower or f"difficulty {level}" in lower:
            return Difficulty(level)
    return Difficulty.L2


def _infer_input_type_from_prompt(text: str) -> InputType:
    for kind in (InputType.URL, InputType.SMS, InputType.EMAIL):
        if f"`{kind.value}`" in text:
            return kind
    return InputType.EMAIL


def _sample_l1(sid: UUID, lang: Language, itype: InputType) -> TrainingSample:
    if lang is Language.ES:
        content = (
            "De: soporte@bbva-seguridad-online.ru\n"
            "Asunto: ¡URGENTE!!! Su cuenta sera cerrada en 24h\n\n"
            "Estimado cliente verifike sus datos AHORA en este link "
            "http://bbva-verificacion.ru/login o su cuenta sera CERRADA."
        )
        indicators = [
            Indicator(
                type=IndicatorType.LOOKALIKE_DOMAIN,
                evidence="bbva-seguridad-online.ru",
                explanation="Dominio falso con TLD `.ru` haciéndose pasar por BBVA.",
            ),
            Indicator(
                type=IndicatorType.URGENCY_LANGUAGE,
                evidence="¡URGENTE!!! Su cuenta sera cerrada en 24h",
                explanation="Urgencia exagerada y amenaza de cierre, típico patrón de phishing.",
            ),
            Indicator(
                type=IndicatorType.BRAND_OR_GRAMMAR_ERROR,
                evidence="verifike",
                explanation="Falta ortográfica obvia en un correo supuestamente bancario.",
            ),
        ]
    else:
        content = (
            "From: support@chase-security-online.ru\n"
            "Subject: URGENT!!! Your account will be CLOSED in 24h\n\n"
            "Dear customer pleese verfy your data NOW at "
            "http://chase-verify.ru/login or your account will be CLOSED."
        )
        indicators = [
            Indicator(
                type=IndicatorType.LOOKALIKE_DOMAIN,
                evidence="chase-security-online.ru",
                explanation="Fake domain with `.ru` TLD impersonating Chase.",
            ),
            Indicator(
                type=IndicatorType.URGENCY_LANGUAGE,
                evidence="URGENT!!! Your account will be CLOSED in 24h",
                explanation="Excessive urgency and closure threat, classic phishing pattern.",
            ),
            Indicator(
                type=IndicatorType.BRAND_OR_GRAMMAR_ERROR,
                evidence="pleese verfy",
                explanation="Obvious typos in a supposedly bank-sent email.",
            ),
        ]
    return TrainingSample(
        id=sid,
        input_type=itype,
        language=lang,
        difficulty=Difficulty.L1,
        content=content,
        true_verdict=Verdict.PHISHING,
        true_indicators=indicators,
    )


def _sample_l3(sid: UUID, lang: Language, itype: InputType) -> TrainingSample:
    if lang is Language.ES:
        content = (
            "De: notificaciones@correos-postal.com\n"
            "Asunto: Paquete pendiente de entrega\n\n"
            "Hola, tenemos un paquete a su nombre que no se ha podido entregar. "
            "Para reprogramar, abone los 1.99€ de gestión en "
            "https://correos-postal.com/pagar"
        )
        indicators = [
            Indicator(
                type=IndicatorType.LOOKALIKE_DOMAIN,
                evidence="correos-postal.com",
                explanation="No es el dominio oficial de Correos (sería correos.es).",
            ),
            Indicator(
                type=IndicatorType.PAYMENT_REQUEST,
                evidence="abone los 1.99€ de gestión",
                explanation="Pedir un micro-pago para 'desbloquear' un envío es señal típica de fraude.",
            ),
        ]
    else:
        content = (
            "From: notifications@usps-postal.com\n"
            "Subject: Package pending delivery\n\n"
            "Hi, we have a package for you that we could not deliver. "
            "To reschedule, pay the $1.99 handling fee at "
            "https://usps-postal.com/pay"
        )
        indicators = [
            Indicator(
                type=IndicatorType.LOOKALIKE_DOMAIN,
                evidence="usps-postal.com",
                explanation="Not the official USPS domain (usps.com).",
            ),
            Indicator(
                type=IndicatorType.PAYMENT_REQUEST,
                evidence="pay the $1.99 handling fee",
                explanation="Requesting a small payment to 'unlock' a delivery is a classic fraud signal.",
            ),
        ]
    return TrainingSample(
        id=sid,
        input_type=itype,
        language=lang,
        difficulty=Difficulty.L3,
        content=content,
        true_verdict=Verdict.PHISHING,
        true_indicators=indicators,
    )


def _sample_l5_legit(sid: UUID, lang: Language, itype: InputType) -> TrainingSample:
    """Nivel 5: ejemplo LEGÍTIMO. Aprender a no marcar todo como phishing."""
    if lang is Language.ES:
        content = (
            "De: facturacion@stripe.com\n"
            "Asunto: Tu factura mensual de Stripe (junio 2026)\n\n"
            "Hola, adjuntamos la factura del mes. Puedes consultarla y descargarla "
            "desde tu panel en https://dashboard.stripe.com/invoices. "
            "Si tienes dudas, responde a este correo o escribe a support@stripe.com."
        )
    else:
        content = (
            "From: billing@stripe.com\n"
            "Subject: Your monthly Stripe invoice (June 2026)\n\n"
            "Hi, please find this month's invoice attached. You can view and "
            "download it from your dashboard at https://dashboard.stripe.com/invoices. "
            "If you have questions, reply to this email or write to support@stripe.com."
        )
    return TrainingSample(
        id=sid,
        input_type=itype,
        language=lang,
        difficulty=Difficulty.L5,
        content=content,
        true_verdict=Verdict.LEGIT,
        true_indicators=[],
    )


# Niveles intermedios reusan los anteriores con etiqueta distinta para que la
# UI vea progresión. En una iteración futura cada nivel tendrá un sample propio.
def _sample_l2(sid: UUID, lang: Language, itype: InputType) -> TrainingSample:
    s = _sample_l1(sid, lang, itype)
    return s.model_copy(update={"difficulty": Difficulty.L2})


def _sample_l4(sid: UUID, lang: Language, itype: InputType) -> TrainingSample:
    s = _sample_l3(sid, lang, itype)
    return s.model_copy(update={"difficulty": Difficulty.L4})


_SAMPLE_FACTORIES = {
    Difficulty.L1: _sample_l1,
    Difficulty.L2: _sample_l2,
    Difficulty.L3: _sample_l3,
    Difficulty.L4: _sample_l4,
    Difficulty.L5: _sample_l5_legit,
}


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
        # Determinista: el id se deriva del input + timestamp truncado para que
        # llamadas en bucle no colisionen pero sigan siendo reproducibles dentro
        # de la misma "ráfaga" de tests.
        sample_id = UUID(bytes=hashlib.sha256(user.encode("utf-8")).digest()[:16])

        # Inferimos la dificultad del propio prompt del usuario (lo monta el
        # servicio del trainer y siempre contiene "dificultad N" / "difficulty N").
        difficulty = _infer_difficulty_from_prompt(user)
        input_type = _infer_input_type_from_prompt(user)

        return _SAMPLE_FACTORIES[difficulty](sample_id, language, input_type)
