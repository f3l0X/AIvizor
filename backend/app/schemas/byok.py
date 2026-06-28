"""Esquemas de BYOK — *Bring Your Own Key* (Fase 7.3).

Niveles de representación de la API key de un usuario, separados igual que en auth:

  - ``ApiKeyCreate``  — entrada del cliente (incluye la clave en claro).
  - ``StoredApiKey``  — vista interna del backend (incluye el texto **cifrado**).
                        Nunca se serializa hacia el cliente.
  - ``ApiKeyPublic``  — salida segura: provider, model, timestamps y una *máscara*
                        de la clave (solo los últimos 4 caracteres). Jamás la clave.

El provider para BYOK se restringe a ``gemini``/``claude``: el ``mock`` no necesita
clave y no tiene sentido como "tu propia" credencial.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ByokProvider = Literal["gemini", "claude"]


def mask_key(plaintext: str) -> str:
    """Devuelve una máscara segura para mostrar: ``••••abcd`` (últimos 4 chars)."""
    tail = plaintext[-4:] if len(plaintext) >= 4 else ""
    return f"••••{tail}"


class ApiKeyCreate(BaseModel):
    """Alta/reemplazo de la clave BYOK. ``model`` opcional (default del provider)."""

    provider: ByokProvider
    api_key: str = Field(min_length=8, max_length=400)
    model: str | None = Field(default=None, max_length=64)


class StoredApiKey(BaseModel):
    """Representación interna con el texto cifrado. Uso exclusivo del backend."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    provider: ByokProvider
    api_key_encrypted: str
    model: str | None
    created_at: datetime
    updated_at: datetime


class ApiKeyPublic(BaseModel):
    """Lo que ve el cliente: nunca la clave en claro, solo su máscara."""

    provider: ByokProvider
    model: str | None
    masked_key: str
    created_at: datetime
    updated_at: datetime
