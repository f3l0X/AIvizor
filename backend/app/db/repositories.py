"""Repositorios. Frontera entre el servicio de dominio y la persistencia.

Diseño:
  - Los servicios (``analyzer``, ``trainer``) solo dependen de Protocols. No
    conocen SQLAlchemy.
  - En producción, FastAPI inyecta las implementaciones SQL (las dependencies
    construyen el repo con la `AsyncSession` que viene de ``get_db``).
  - En tests, sobreescribimos esas dependencies por implementaciones en memoria
    que capturan llamadas sin necesitar BD. Tests rápidos + verificación del
    contrato del repositorio.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis, TrainingAttempt, User
from app.schemas.analysis import AnalysisResult
from app.schemas.auth import Role, UserInDB
from app.schemas.common import InputType
from app.schemas.training import TrainingAnswer, TrainingSample


@runtime_checkable
class AnalysisRepository(Protocol):
    """Contrato de persistencia para análisis. Async, sin filtrar SQLAlchemy."""

    async def save(
        self,
        *,
        result: AnalysisResult,
        original_content: str,  # reservado para futuras tablas de evidencia
        input_type: InputType,
    ) -> UUID: ...


class SqlAnalysisRepository:
    """Implementación sobre SQLAlchemy async. Hace commit por llamada."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        *,
        result: AnalysisResult,
        original_content: str,
        input_type: InputType,
    ) -> UUID:
        row = Analysis(
            input_type=input_type.value,
            language=result.language.value,
            risk_score=result.risk_score,
            verdict=result.verdict.value,
            summary=result.summary,
            indicators=[i.model_dump(mode="json") for i in result.indicators],
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.id


class InMemoryAnalysisRepository:
    """Implementación en memoria para tests. Conserva los items guardados."""

    def __init__(self) -> None:
        self.items: list[dict] = []

    async def save(
        self,
        *,
        result: AnalysisResult,
        original_content: str,
        input_type: InputType,
    ) -> UUID:
        new_id = uuid4()
        self.items.append(
            {
                "id": new_id,
                "input_type": input_type.value,
                "result": result.model_dump(mode="json"),
                "original_content": original_content,
            }
        )
        return new_id


# ---------------------------------------------------------------------------
# Trainer (Módulo B)
# ---------------------------------------------------------------------------

@runtime_checkable
class TrainingAttemptRepository(Protocol):
    """Persistencia de samples del Trainer y respuestas del alumno."""

    async def save_sample(self, sample: TrainingSample) -> None: ...

    async def get_sample(self, sample_id: UUID) -> TrainingSample | None: ...

    async def save_answer(
        self,
        *,
        answer: TrainingAnswer,
        correct: bool,
        score: int,
    ) -> None: ...


class SqlTrainingAttemptRepository:
    """Implementación sobre SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_sample(self, sample: TrainingSample) -> None:
        row = TrainingAttempt(
            id=sample.id,
            difficulty=sample.difficulty.value,
            sample=sample.model_dump(mode="json"),
        )
        self._session.add(row)
        await self._session.commit()

    async def get_sample(self, sample_id: UUID) -> TrainingSample | None:
        row = await self._session.get(TrainingAttempt, sample_id)
        if row is None:
            return None
        return TrainingSample.model_validate(row.sample)

    async def save_answer(
        self,
        *,
        answer: TrainingAnswer,
        correct: bool,
        score: int,
    ) -> None:
        row = await self._session.get(TrainingAttempt, answer.sample_id)
        if row is None:
            return
        row.user_answer = answer.model_dump(mode="json")
        row.correct = correct
        row.score = score
        row.answered_at = datetime.now(timezone.utc)
        await self._session.commit()


class InMemoryTrainingAttemptRepository:
    """Implementación en memoria para tests. Indexa samples por id."""

    def __init__(self) -> None:
        self.samples: dict[UUID, TrainingSample] = {}
        self.answers: list[dict] = []

    async def save_sample(self, sample: TrainingSample) -> None:
        self.samples[sample.id] = sample

    async def get_sample(self, sample_id: UUID) -> TrainingSample | None:
        return self.samples.get(sample_id)

    async def save_answer(
        self,
        *,
        answer: TrainingAnswer,
        correct: bool,
        score: int,
    ) -> None:
        self.answers.append(
            {
                "answer": answer.model_dump(mode="json"),
                "correct": correct,
                "score": score,
            }
        )


# ---------------------------------------------------------------------------
# Usuarios (Fase 7.2)
# ---------------------------------------------------------------------------

@runtime_checkable
class UserRepository(Protocol):
    """Persistencia de usuarios. Devuelve ``UserInDB`` (incluye hash) o ``None``.

    El servicio de auth nunca toca SQLAlchemy; opera contra este contrato, lo que
    permite testear registro/login con la implementación en memoria.
    """

    async def create(self, *, email: str, password_hash: str, role: Role) -> UserInDB: ...

    async def get_by_email(self, email: str) -> UserInDB | None: ...

    async def get_by_id(self, user_id: UUID) -> UserInDB | None: ...


class SqlUserRepository:
    """Implementación sobre SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, email: str, password_hash: str, role: Role) -> UserInDB:
        row = User(email=email, password_hash=password_hash, role=role.value)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return UserInDB.model_validate(row)

    async def get_by_email(self, email: str) -> UserInDB | None:
        stmt = select(User).where(User.email == email)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return UserInDB.model_validate(row) if row is not None else None

    async def get_by_id(self, user_id: UUID) -> UserInDB | None:
        row = await self._session.get(User, user_id)
        return UserInDB.model_validate(row) if row is not None else None


class InMemoryUserRepository:
    """Implementación en memoria para tests. Indexa por id y mantiene email único."""

    def __init__(self) -> None:
        self.users: dict[UUID, UserInDB] = {}

    async def create(self, *, email: str, password_hash: str, role: Role) -> UserInDB:
        user = UserInDB(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.users[user.id] = user
        return user

    async def get_by_email(self, email: str) -> UserInDB | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, user_id: UUID) -> UserInDB | None:
        return self.users.get(user_id)


# select se exporta porque algunos tests querrán construir queries; lo dejamos
# aquí para evitar imports adicionales en otros módulos.
__all__ = [
    "AnalysisRepository",
    "InMemoryAnalysisRepository",
    "InMemoryTrainingAttemptRepository",
    "InMemoryUserRepository",
    "SqlAnalysisRepository",
    "SqlTrainingAttemptRepository",
    "SqlUserRepository",
    "TrainingAttemptRepository",
    "UserRepository",
    "select",
]
