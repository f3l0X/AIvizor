"""Servicio del Analyzer. Une LLM + persistencia.

Punto único donde se decide el flujo del Módulo A:
  1. Construir el prompt (system + wrap del input no confiable).
  2. Llamar al `LLMProvider` con el esquema `AnalysisResult`.
  3. Forzar coherencia idioma del payload ↔ idioma de la respuesta (red de seguridad
     por si el LLM se confunde y devuelve otro `language`).
  4. Persistir vía `AnalysisRepository` (ID inyectado en el resultado de retorno
     solo si lo necesita el caller; el endpoint actualmente devuelve solo el
     `AnalysisResult` validado).

Nada de SDK aquí — todo entra por inyección de dependencias.
"""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.db.repositories import AnalysisRepository
from app.prompts.analyzer import system_prompt, wrap_user_input
from app.schemas.analysis import AnalysisResult, AnalyzeRequest


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
    system = system_prompt(req.language)
    user = wrap_user_input(req.content, req.input_type)

    result = await llm.complete_structured(
        system=system,
        user=user,
        response_model=AnalysisResult,
        language=req.language,
    )

    # Red de seguridad: si el LLM mete otro idioma en `language`, lo sobreescribimos
    # con el que pidió el cliente. El esquema ya garantiza que sea ES o EN; aquí
    # garantizamos coherencia con la petición.
    if result.language is not req.language:
        result = result.model_copy(update={"language": req.language})

    await repo.save(
        result=result,
        original_content=req.content,
        input_type=req.input_type,
    )
    return result
