"""Endpoints de gestión de la API key BYOK del usuario: ``/api/keys`` (Fase 7.3).

Todos requieren sesión (``get_current_user`` → 401 sin login). La clave en claro solo
entra (PUT) y nunca sale: las respuestas devuelven ``ApiKeyPublic`` con la clave
enmascarada.

  - ``GET    /api/keys`` → config BYOK actual o 404 si no hay.
  - ``PUT    /api/keys`` → crea/reemplaza la clave (upsert).
  - ``DELETE /api/keys`` → borra la clave (vuelve al provider del servidor).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.repositories import ApiKeyRepository, SqlApiKeyRepository
from app.db.session import get_db
from app.schemas.auth import UserInDB
from app.schemas.byok import ApiKeyCreate, ApiKeyPublic
from app.services.byok import delete_api_key, get_api_key, set_api_key

router = APIRouter(prefix="/api/keys", tags=["byok"])


def get_api_key_repo(session: AsyncSession = Depends(get_db)) -> ApiKeyRepository:
    """Dependency override-able en tests."""
    return SqlApiKeyRepository(session)


@router.get("", response_model=ApiKeyPublic)
async def read_key(
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> ApiKeyPublic:
    public = await get_api_key(user.id, repo=repo)
    if public is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No API key configured")
    return public


@router.put("", response_model=ApiKeyPublic)
async def put_key(
    payload: ApiKeyCreate,
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> ApiKeyPublic:
    return await set_api_key(user.id, payload, repo=repo)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def remove_key(
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> None:
    await delete_api_key(user.id, repo=repo)
