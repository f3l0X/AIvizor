"""Servicio del Trainer (Módulo B).

Dos operaciones:
  1. ``generate_sample`` — pide al LLM una muestra de la dificultad/idioma/tipo
     pedidos y la persiste con ``user_answer=null`` para poder evaluarla más
     tarde por su ``id``.
  2. ``evaluate_answer`` — recupera el sample por id, compara con la respuesta
     del usuario, calcula score (0-100), decide indicadores fallados y propone
     la siguiente dificultad.

Decisión sobre dificultad adaptativa:
  - Regla simple v1: acierto → +1 (cap 5); fallo → -1 (floor 1). Sin sesión:
    el cliente lleva su nivel y el servidor solo sugiere el siguiente. Esto
    evita inventar un sistema de sesiones para algo que el cliente puede
    gestionar perfectamente y mantiene el endpoint stateless.

Scoring:
  - 100 si verdict correcto y todos los indicadores marcados.
  - 0 si verdict incorrecto.
  - Si verdict correcto pero faltan indicadores: lineal sobre los marcados
    correctamente.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.db.repositories import TrainingAttemptRepository
from app.llm.base import LLMError, LLMProvider
from app.prompts.trainer import system_prompt as trainer_system_prompt
from app.prompts.trainer import user_prompt as trainer_user_prompt
from app.schemas.common import Difficulty, InputType, Language, Verdict
from app.schemas.training import (
    TrainingAnswer,
    TrainingFeedback,
    TrainingSample,
    TrainingSampleDraft,
)


async def generate_sample(
    *,
    difficulty: Difficulty,
    input_type: InputType,
    language: Language,
    llm: LLMProvider,
    repo: TrainingAttemptRepository,
) -> TrainingSample:
    """Pide al LLM un ejemplo y lo persiste para evaluación futura.

    El LLM solo genera el *draft* (contenido + verdad). El servicio compone el
    ``TrainingSample`` final añadiendo los metadatos que ya conoce
    (``difficulty``/``input_type``/``language``) y un ``id`` propio. Así el LLM
    no decide metadatos fijados por la petición y, de paso, evitamos meter un
    ``IntEnum`` en el schema que Gemini no sabe serializar.
    """
    draft = await llm.complete_structured(
        system=trainer_system_prompt(language),
        user=trainer_user_prompt(
            difficulty=difficulty,
            input_type=input_type,
            language=language,
        ),
        response_model=TrainingSampleDraft,
        language=language,
    )

    sample = TrainingSample(
        id=uuid4(),
        input_type=input_type,
        language=language,
        difficulty=difficulty,
        content=draft.content,
        true_verdict=draft.true_verdict,
        true_indicators=draft.true_indicators,
    )

    await repo.save_sample(sample)
    return sample


async def evaluate_answer(
    answer: TrainingAnswer,
    *,
    repo: TrainingAttemptRepository,
) -> TrainingFeedback:
    """Compara la respuesta del usuario con el sample original y devuelve feedback.

    El idioma del feedback se toma del propio sample (que se generó en ese
    idioma); el cliente no necesita reenviarlo.

    Si el sample no existe (id desconocido), lanza ``LookupError`` para que el
    endpoint mapee a 404.
    """
    sample = await repo.get_sample(answer.sample_id)
    if sample is None:
        raise LookupError(f"sample {answer.sample_id} not found")

    correct, score, missed = _score(sample, answer)
    next_diff = _next_difficulty(sample.difficulty, correct)

    feedback = TrainingFeedback(
        sample_id=sample.id,
        correct=correct,
        score=score,
        missed_indicators=missed,
        true_indicator_types=[ind.type.value for ind in sample.true_indicators],
        explanation=_explain(sample, answer, correct, sample.language),
        next_difficulty=next_diff,
    )

    await repo.save_answer(answer=answer, correct=correct, score=score)
    return feedback


# ---------------------------------------------------------------------------
# helpers de scoring / adaptación
# ---------------------------------------------------------------------------

def _score(sample: TrainingSample, answer: TrainingAnswer) -> tuple[bool, int, list]:
    """Devuelve (verdict_correcto, score 0-100, indicadores que se le escaparon).

    `missed` se calcula siempre como "indicadores verdaderos que el alumno NO
    marcó" — independiente del verdict. Si el alumno se equivocó de verdict
    pero acertó algún indicador, ese indicador NO debe aparecer en `missed`
    (sería contradictorio con el ✓ verde que la UI le pinta).

    Score:
      - verdict incorrecto → 0 (puntúa la decisión final, no los indicadores).
      - verdict correcto sin indicadores reales → 100.
      - verdict correcto con indicadores → 100 * aciertos / total.
    """
    verdict_correct = sample.true_verdict is answer.user_verdict
    marked = set(answer.marked_indicator_types)

    missed = [ind for ind in sample.true_indicators if ind.type.value not in marked]

    if not verdict_correct:
        return False, 0, missed

    true_types = {ind.type.value for ind in sample.true_indicators}
    if not true_types:
        # Sample legítimo bien clasificado y sin indicadores que marcar.
        return True, 100, []

    hits = len(true_types & marked)
    pct = 100 * hits // len(true_types)
    return True, pct, missed


def _next_difficulty(current: Difficulty, correct: bool) -> Difficulty:
    value = current.value + 1 if correct else current.value - 1
    value = max(Difficulty.L1.value, min(Difficulty.L5.value, value))
    return Difficulty(value)


def _explain(
    sample: TrainingSample,
    answer: TrainingAnswer,
    correct: bool,
    language: Language,
) -> str:
    is_es = language is Language.ES

    if not correct:
        if is_es:
            return (
                f"Veredicto incorrecto. Era '{_verdict_label(sample.true_verdict, language)}' "
                f"y marcaste '{_verdict_label(answer.user_verdict, language)}'."
            )
        return (
            f"Wrong verdict. It was '{_verdict_label(sample.true_verdict, language)}' "
            f"and you picked '{_verdict_label(answer.user_verdict, language)}'."
        )

    n_true = len(sample.true_indicators)
    n_hits = len({i.type.value for i in sample.true_indicators} & set(answer.marked_indicator_types))

    if n_true == 0:
        return (
            "¡Bien! Era legítimo y no había indicadores que marcar."
            if is_es
            else "Nice! It was legitimate and there were no indicators to mark."
        )
    if n_hits == n_true:
        return (
            f"¡Perfecto! Acertaste el veredicto y los {n_true} indicadores."
            if is_es
            else f"Perfect! You got the verdict and all {n_true} indicators."
        )
    return (
        f"Veredicto correcto, pero te faltaron {n_true - n_hits} de {n_true} indicadores."
        if is_es
        else f"Verdict correct, but you missed {n_true - n_hits} of {n_true} indicators."
    )


def _verdict_label(v: Verdict, language: Language) -> str:
    es = {"legit": "legítimo", "suspicious": "sospechoso", "phishing": "phishing"}
    en = {"legit": "legit", "suspicious": "suspicious", "phishing": "phishing"}
    return (es if language is Language.ES else en)[v.value]
