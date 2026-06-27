"""Endpoints HTTP del Trainer.

  - ``POST /api/train/next``   → genera y devuelve el siguiente sample (sin la
                                 "verdad"; ver `TrainingSamplePublic`).
  - ``POST /api/train/answer`` → recibe la respuesta del alumno y devuelve
                                 feedback con score + indicadores fallados +
                                 dificultad sugerida para el siguiente.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import SqlTrainingAttemptRepository, TrainingAttemptRepository
from app.db.session import get_db
from app.llm.base import LLMError, LLMProvider
from app.llm.factory import get_llm as _factory_get_llm
from app.schemas.training import (
    TrainingAnswer,
    TrainingFeedback,
    TrainingNextRequest,
    TrainingSamplePublic,
)
from app.services.trainer import evaluate_answer, generate_sample

router = APIRouter(prefix="/api/train", tags=["trainer"])


def get_llm() -> LLMProvider:
    return _factory_get_llm()


def get_training_repo(
    session: AsyncSession = Depends(get_db),
) -> TrainingAttemptRepository:
    return SqlTrainingAttemptRepository(session)


@router.post("/next", response_model=TrainingSamplePublic)
async def next_sample(
    payload: TrainingNextRequest,
    llm: LLMProvider = Depends(get_llm),
    repo: TrainingAttemptRepository = Depends(get_training_repo),
) -> TrainingSamplePublic:
    try:
        sample = await generate_sample(
            difficulty=payload.difficulty,
            input_type=payload.input_type,
            language=payload.language,
            llm=llm,
            repo=repo,
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider failed: {e}",
        ) from e
    return TrainingSamplePublic.from_internal(sample)


@router.post("/answer", response_model=TrainingFeedback)
async def submit_answer(
    answer: TrainingAnswer,
    repo: TrainingAttemptRepository = Depends(get_training_repo),
) -> TrainingFeedback:
    try:
        return await evaluate_answer(answer, repo=repo)
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
