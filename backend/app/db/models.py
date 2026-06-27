"""Modelos SQLAlchemy 2.0 (style mapped_column).

Tablas de v1:
  - ``analyses``           — cada análisis del Módulo A (PLANNING.md §5).
  - ``training_attempts``  — intentos del Módulo B (se añade en Fase 5).

`indicators` se guarda como JSON (en Postgres se mapea a JSONB) para flexibilidad de
esquema sin migrar a cada cambio del catálogo de `IndicatorType`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    input_type: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(8))
    risk_score: Mapped[int] = mapped_column(Integer)
    verdict: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str] = mapped_column(String(1000))
    indicators: Mapped[list[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Analysis id={self.id} verdict={self.verdict} score={self.risk_score}>"
