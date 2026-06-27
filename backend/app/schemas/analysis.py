"""Esquemas de entrada/salida del Módulo A (Analizador).

Estos modelos son el **contrato** que el LLM debe respetar. El `LLMProvider` valida
contra ellos y, si la respuesta no encaja, lanza ``LLMError`` en lugar de devolver
datos corruptos (ver `app/llm/base.py`).
"""

from pydantic import BaseModel, Field

from app.schemas.common import IndicatorType, InputType, Language, Verdict


class Indicator(BaseModel):
    """Señal individual detectada por el Analizador.

    - ``type``:        categoría del catálogo cerrado (`IndicatorType`).
    - ``evidence``:    fragmento literal del input que justifica la señal. Sirve para
                       que el frontend lo resalte y para auditabilidad.
    - ``explanation``: por qué ese fragmento es señal de engaño, en lenguaje llano y
                       en el idioma pedido (es/en). Es la parte educativa.
    """

    type: IndicatorType
    evidence: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=1000)


class AnalyzeRequest(BaseModel):
    """Payload del endpoint ``POST /api/analyze``."""

    content: str = Field(min_length=1, max_length=20_000)
    input_type: InputType
    language: Language = Language.ES


class AnalysisResult(BaseModel):
    """Salida del Analizador. Lo que el LLM debe rellenar y lo que ve el cliente.

    ``risk_score`` y ``verdict`` van juntos por diseño: el score es matiz numérico,
    el veredicto es el semáforo. Los indicadores explican el porqué.
    """

    risk_score: int = Field(ge=0, le=100)
    verdict: Verdict
    indicators: list[Indicator] = Field(default_factory=list, max_length=20)
    language: Language
    summary: str = Field(min_length=1, max_length=600)
