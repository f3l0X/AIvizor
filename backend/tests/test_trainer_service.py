"""Tests del servicio del Trainer."""

from __future__ import annotations

import pytest

from app.db.repositories import InMemoryTrainingAttemptRepository
from app.llm.mock import MockProvider
from app.schemas.common import Difficulty, InputType, Language, Verdict
from app.schemas.training import TrainingAnswer, TrainingSample
from app.services.trainer import (
    _next_difficulty,
    _score,
    evaluate_answer,
    generate_sample,
)


async def test_generate_persists_and_returns_sample_with_requested_difficulty(
    mock_provider: MockProvider,
    in_memory_training_repo: InMemoryTrainingAttemptRepository,
) -> None:
    sample = await generate_sample(
        difficulty=Difficulty.L3,
        input_type=InputType.EMAIL,
        language=Language.ES,
        llm=mock_provider,
        repo=in_memory_training_repo,
    )
    assert isinstance(sample, TrainingSample)
    assert sample.difficulty is Difficulty.L3
    assert sample.input_type is InputType.EMAIL
    assert sample.language is Language.ES
    assert sample.id in in_memory_training_repo.samples


async def test_evaluate_returns_404_like_error_for_unknown_sample(
    in_memory_training_repo: InMemoryTrainingAttemptRepository,
) -> None:
    from uuid import uuid4

    answer = TrainingAnswer(
        sample_id=uuid4(),
        user_verdict=Verdict.LEGIT,
        marked_indicator_types=[],
    )
    with pytest.raises(LookupError):
        await evaluate_answer(answer, repo=in_memory_training_repo)


async def test_full_flow_correct_verdict_all_indicators(
    mock_provider: MockProvider,
    in_memory_training_repo: InMemoryTrainingAttemptRepository,
) -> None:
    sample = await generate_sample(
        difficulty=Difficulty.L1,
        input_type=InputType.EMAIL,
        language=Language.ES,
        llm=mock_provider,
        repo=in_memory_training_repo,
    )
    answer = TrainingAnswer(
        sample_id=sample.id,
        user_verdict=sample.true_verdict,
        marked_indicator_types=[i.type.value for i in sample.true_indicators],
    )
    feedback = await evaluate_answer(answer, repo=in_memory_training_repo)

    assert feedback.correct is True
    assert feedback.score == 100
    assert feedback.missed_indicators == []
    assert feedback.next_difficulty is Difficulty.L2


async def test_wrong_verdict_scores_zero(
    mock_provider: MockProvider,
    in_memory_training_repo: InMemoryTrainingAttemptRepository,
) -> None:
    sample = await generate_sample(
        difficulty=Difficulty.L2,
        input_type=InputType.EMAIL,
        language=Language.ES,
        llm=mock_provider,
        repo=in_memory_training_repo,
    )
    wrong_verdict = Verdict.LEGIT if sample.true_verdict is not Verdict.LEGIT else Verdict.PHISHING
    answer = TrainingAnswer(
        sample_id=sample.id,
        user_verdict=wrong_verdict,
        marked_indicator_types=[i.type.value for i in sample.true_indicators],
    )
    feedback = await evaluate_answer(answer, repo=in_memory_training_repo)

    assert feedback.correct is False
    assert feedback.score == 0
    assert feedback.next_difficulty is Difficulty.L1  # L2 - 1


async def test_partial_indicators_score(
    mock_provider: MockProvider,
    in_memory_training_repo: InMemoryTrainingAttemptRepository,
) -> None:
    sample = await generate_sample(
        difficulty=Difficulty.L3,
        input_type=InputType.EMAIL,
        language=Language.ES,
        llm=mock_provider,
        repo=in_memory_training_repo,
    )
    # Marca solo el primer indicador.
    first = sample.true_indicators[0].type.value
    answer = TrainingAnswer(
        sample_id=sample.id,
        user_verdict=sample.true_verdict,
        marked_indicator_types=[first],
    )
    feedback = await evaluate_answer(answer, repo=in_memory_training_repo)

    assert feedback.correct is True
    n_true = len(sample.true_indicators)
    assert feedback.score == 100 // n_true
    assert len(feedback.missed_indicators) == n_true - 1


def test_next_difficulty_caps_at_5() -> None:
    assert _next_difficulty(Difficulty.L5, correct=True) is Difficulty.L5


def test_next_difficulty_floors_at_1() -> None:
    assert _next_difficulty(Difficulty.L1, correct=False) is Difficulty.L1


def test_score_legit_with_no_indicators() -> None:
    from uuid import uuid4

    sample = TrainingSample(
        id=uuid4(),
        input_type=InputType.EMAIL,
        language=Language.ES,
        difficulty=Difficulty.L5,
        content="Hola",
        true_verdict=Verdict.LEGIT,
        true_indicators=[],
    )
    answer = TrainingAnswer(
        sample_id=sample.id,
        user_verdict=Verdict.LEGIT,
        marked_indicator_types=[],
    )
    correct, score, missed = _score(sample, answer)
    assert correct is True
    assert score == 100
    assert missed == []
