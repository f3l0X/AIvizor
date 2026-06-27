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


class TrainingSampleDraft(BaseModel):
    """Lo que el LLM **genera**: solo el contenido y su verdad.

    NO incluye ``difficulty``/``input_type``/``language``: esos los conoce el
    caller (el servicio del trainer los pidió) y los rellena él al componer el
    ``TrainingSample`` final. Esto tiene dos ventajas:

    1. **Compatibilidad de schema.** ``Difficulty`` es un ``IntEnum`` y el
       generador de ``response_schema`` de Gemini (google-genai) no acepta enums
       de enteros — exige strings. Sacando ``difficulty`` del esquema que ve el
       LLM, evitamos el fallo de validación del schema.
    2. **Corrección.** El LLM no debe decidir metadatos que ya están fijados por
       la petición; antes los sobreescribíamos igualmente, ahora ni se piden.
    """

    content: str = Field(min_length=1, max_length=20_000)
    true_verdict: Verdict
    true_indicators: list[Indicator] = Field(default_factory=list, max_length=20)


class TrainingSample(BaseModel):
    """Ejemplo completo (draft + metadatos del caller) que se persiste y evalúa."""

    id: UUID
    input_type: InputType
    language: Language
    difficulty: Difficulty
    content: str = Field(min_length=1, max_length=20_000)
    true_verdict: Verdict
    true_indicators: list[Indicator] = Field(default_factory=list, max_length=20)


class TrainingSamplePublic(BaseModel):
    """Vista del sample que recibe el cliente: SIN la verdad (verdict/indicators).

    Si devolviésemos `TrainingSample` directamente, el cliente vería la respuesta
    correcta antes de contestar. Mantenemos la "verdad" server-side e indexada
    por ``id``; el cliente sólo manda ``sample_id`` + su respuesta.
    """

    id: UUID
    input_type: InputType
    language: Language
    difficulty: Difficulty
    content: str

    @classmethod
    def from_internal(cls, s: "TrainingSample") -> "TrainingSamplePublic":
        return cls(
            id=s.id,
            input_type=s.input_type,
            language=s.language,
            difficulty=s.difficulty,
            content=s.content,
        )


class TrainingNextRequest(BaseModel):
    """Payload del endpoint ``POST /api/train/next``."""

    difficulty: Difficulty = Difficulty.L1
    input_type: InputType = InputType.EMAIL
    language: Language = Language.ES


class TrainingAnswer(BaseModel):
    """Respuesta del usuario a un sample."""

    sample_id: UUID
    user_verdict: Verdict
    marked_indicator_types: list[str] = Field(default_factory=list)


class TrainingFeedback(BaseModel):
    """Devolución educativa tras la respuesta del usuario.

    - ``missed_indicators``: indicadores verdaderos que el alumno NO marcó
      (con su explicación, para que el frontend los muestre como "te faltó").
    - ``true_indicator_types``: tipos verdaderos completos (los que faltaron
      + los que el alumno acertó). El frontend lo usa para distinguir aciertos
      (✓ verde) de falsos positivos (✗ rojo); sin esta lista el cliente solo
      sabría qué le faltó pero no qué marcó correctamente.
    """

    sample_id: UUID
    correct: bool
    score: int = Field(ge=0, le=100)
    missed_indicators: list[Indicator] = Field(default_factory=list)
    true_indicator_types: list[str] = Field(default_factory=list)
    explanation: str
    next_difficulty: Difficulty
