"""Repositorios. Frontera entre el servicio de dominio y la persistencia.

Diseño:
  - El servicio `analyzer.analyze_content` solo depende del Protocol
    ``AnalysisRepository``. No conoce SQLAlchemy.
  - En producción, FastAPI inyecta una ``SqlAnalysisRepository`` (la dependency
    ``get_analysis_repo`` toma la `AsyncSession` de ``get_db``).
  - En tests, sobreescribimos esa dependency por una ``InMemoryAnalysisRepository``
    que captura llamadas sin necesitar BD. Esto mantiene los tests del endpoint
    rápidos y deterministas, y verifica el contrato del repositorio.

Esta indirección también allana el camino para Fase 5 (`training_attempts`) y para
hipotéticos cambios de persistencia (caché, append-only log, etc.).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Analysis
from app.schemas.analysis import AnalysisResult
from app.schemas.common import InputType


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
