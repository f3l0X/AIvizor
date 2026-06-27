"""Servicio del Analyzer. Une LLM + persistencia + observabilidad de injection.

Flujo del Módulo A:
  1. **Observar.** Detectar patrones conocidos de prompt injection y registrarlos
     (no se bloquea: el LLM debe verlos como DATO y marcarlos como indicadores).
  2. **Construir el prompt** (system endurecido + wrap del input no confiable).
  3. **Llamar al ``LLMProvider``** con el esquema ``AnalysisResult``.
  4. **Forzar coherencia** del idioma del resultado con el de la petición (red
     de seguridad contra un LLM que ignore esa parte del prompt).
  5. **Persistir** vía ``AnalysisRepository``.

Nada de SDK aquí — todo entra por inyección de dependencias.
"""

from __future__ import annotations

import logging

from app.db.repositories import AnalysisRepository
from app.llm.base import LLMProvider
from app.prompts.analyzer import system_prompt, wrap_user_input
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.security.injection_signals import detect as detect_injection_signals

log = logging.getLogger(__name__)


async def analyze_content(
    req: AnalyzeRequest,
    *,
    llm: LLMProvider,
    repo: AnalysisRepository,
) -> AnalysisResult:
    """Analiza ``req.content`` y persiste el resultado.

    Devuelve siempre un ``AnalysisResult`` ya validado por Pydantic (lo garantiza
    la capa LLM). Si el provider falla, propaga ``LLMError`` para que el handler
    de FastAPI lo mapee a un 502/503 coherente.
    """
    signals = detect_injection_signals(req.content)
    if signals:
        log.info(
            "analyzer.injection_signals_detected",
            extra={
                "input_type": req.input_type.value,
                "language": req.language.value,
                "signal_kinds": [s.kind.value for s in signals],
                "signal_count": len(signals),
            },
        )

    system = system_prompt(req.language)
    user = wrap_user_input(req.content, req.input_type)

    result = await llm.complete_structured(
        system=system,
        user=user,
        response_model=AnalysisResult,
        language=req.language,
    )

    if result.language is not req.language:
        result = result.model_copy(update={"language": req.language})

    await repo.save(
        result=result,
        original_content=req.content,
        input_type=req.input_type,
    )
    return result
