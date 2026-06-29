"""Endpoints de gestión de las API keys BYOK del usuario: ``/api/keys`` (Fase 7.3 / 7.6).

Todos requieren sesión (``get_current_user`` → 401 sin login). La clave en claro solo
entra (PUT) y nunca sale: las respuestas devuelven ``ApiKeyPublic`` con la clave
enmascarada.

Un usuario puede guardar una clave **por proveedor** (gemini/claude) y elegir cuál
está **activa** (la que usan Analyzer/Trainer):

  - ``GET    /api/keys``            → lista de claves (vacía si no hay).
  - ``PUT    /api/keys``            → crea/reemplaza la clave de un proveedor (upsert).
  - ``PUT    /api/keys/active``     → marca activa la clave de un proveedor. 404 si no existe.
  - ``DELETE /api/keys/{provider}`` → borra la clave de ese proveedor (204).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.repositories import ApiKeyRepository, SqlApiKeyRepository
from app.db.session import get_db
from app.schemas.auth import UserInDB
from app.schemas.byok import (
    ActiveProviderRequest,
    ApiKeyCreate,
    ApiKeyPublic,
    ByokProvider,
)
from app.services.byok import (
    NoApiKeyError,
    delete_api_key,
    list_api_keys,
    set_active_provider,
    set_api_key,
)

router = APIRouter(prefix="/api/keys", tags=["byok"])


def get_api_key_repo(session: AsyncSession = Depends(get_db)) -> ApiKeyRepository:
    """Dependency override-able en tests."""
    return SqlApiKeyRepository(session)


@router.get("", response_model=list[ApiKeyPublic])
async def list_keys(
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> list[ApiKeyPublic]:
    return await list_api_keys(user.id, repo=repo)


@router.put("", response_model=ApiKeyPublic)
async def put_key(
    payload: ApiKeyCreate,
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> ApiKeyPublic:
    return await set_api_key(user.id, payload, repo=repo)


@router.put("/active", response_model=ApiKeyPublic)
async def activate_key(
    payload: ActiveProviderRequest,
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> ApiKeyPublic:
    try:
        return await set_active_provider(user.id, payload.provider, repo=repo)
    except NoApiKeyError as e:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No API key for that provider"
        ) from e


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_key(
    provider: ByokProvider,
    user: UserInDB = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> None:
    await delete_api_key(user.id, provider, repo=repo)
