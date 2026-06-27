"""Esquemas del Módulo B (Entrenador).

El flujo es:
    1. cliente pide siguiente ejemplo → ``TrainingSample`` (con la "verdad" oculta).
    2. cliente responde → ``TrainingAnswer``.
    3. servidor compara y devuelve ``TrainingFeedback`` con los indicadores fallados.

La "verdad" del sample (``true_verdict`` y ``true_indicators``) **nunca** se devuelve al
cliente hasta que el usuario ha respondido — el servicio del trainer la guarda en sesión
o en BD y la oculta en la respuesta inicial (ver Fase 5).
"""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.analysis import Indicator
from app.schemas.common import Difficulty, InputType, Language, Verdict


class TrainingSample(BaseModel):
    """Ejemplo generado por el LLM para que el usuario clasifique."""

    id: UUID
    input_type: InputType
    language: Language
    difficulty: Difficulty
    content: str = Field(min_length=1, max_length=20_000)
    true_verdict: Verdict
    true_indicators: list[Indicator] = Field(default_factory=list, max_length=20)


class TrainingAnswer(BaseModel):
    """Respuesta del usuario a un sample."""

    sample_id: UUID
    user_verdict: Verdict
    marked_indicator_types: list[str] = Field(default_factory=list)


class TrainingFeedback(BaseModel):
    """Devolución educativa tras la respuesta del usuario."""

    sample_id: UUID
    correct: bool
    score: int = Field(ge=0, le=100)
    missed_indicators: list[Indicator] = Field(default_factory=list)
    explanation: str
    next_difficulty: Difficulty
