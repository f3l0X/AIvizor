"""Engine SQLAlchemy 2.0 async + session factory + ``Base`` declarativo.

- Engine **lazy**: se crea la primera vez que alguien lo pide (a través de
  ``get_db``). Tests que sobreescriben la dependency con repos en memoria nunca lo
  tocan, así que no necesitan tener ``psycopg`` instalado.
- ``get_db`` es la dependency de FastAPI: abre una `AsyncSession`, la cede al
  endpoint y la cierra al salir del bloque.
- ``Base`` es la clase declarativa de la que heredan los modelos.

DATABASE_URL espera el driver async ``psycopg`` (no ``psycopg2``); ver `.env.example`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base declarativa común. Todos los modelos heredan de aquí."""


@lru_cache(maxsize=1)
def _engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        _engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: una sesión por request."""
    async with _session_factory()() as session:
        yield session
