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

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Usuario de la plataforma (Fase 7.2).

    - ``password_hash`` guarda un hash bcrypt; la contraseña en claro nunca toca
      la BD ni sale al cliente.
    - ``role`` es ``admin`` o ``user`` (ver ``app.schemas.auth.Role``); se guarda
      como string para no acoplar la columna al enum.
    - ``is_active`` permite deshabilitar cuentas sin borrarlas (futuro panel admin).
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(16), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email} role={self.role}>"


class UserApiKey(Base):
    """API key de LLM aportada por el usuario (BYOK, Fase 7.3; multi-clave en 7.6).

    - ``api_key_encrypted`` guarda el token Fernet (cifrado en reposo); la clave en
      claro nunca toca la BD ni sale al cliente.
    - ``provider`` es ``gemini`` o ``claude`` (el mock no admite BYOK).
    - ``model`` es opcional: si está vacío, se usa el modelo por defecto del provider.
    - Un usuario puede tener **una clave por proveedor** (único ``(user_id, provider)``).
      ``is_active`` marca cuál se usa; la capa de aplicación garantiza ≤1 activa por
      usuario. Reemplazar la clave de un proveedor es un upsert sobre su fila.
    """

    __tablename__ = "user_api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_api_keys_user_provider"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(16))
    api_key_encrypted: Mapped[str] = mapped_column(String(512))
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserApiKey user_id={self.user_id} provider={self.provider} active={self.is_active}>"


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


class TrainingAttempt(Base):
    """Un sample del Trainer + (opcionalmente) la respuesta del alumno.

    Se inserta con ``user_answer=None`` al pedir ``/api/train/next``. La fila se
    actualiza con la respuesta y el scoring al llegar ``/api/train/answer``.
    Mantener todo en una sola tabla simplifica la consulta y refleja el flujo
    real (un sample tiene como máximo un intento).
    """

    __tablename__ = "training_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    difficulty: Mapped[int] = mapped_column(Integer)
    sample: Mapped[dict] = mapped_column(JSON)  # TrainingSample completo
    user_answer: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correct: Mapped[bool | None] = mapped_column(nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TrainingAttempt id={self.id} diff={self.difficulty} score={self.score}>"
