"""Endpoints del panel admin: ``/api/admin`` (Fase 7.5).

Todos exigen sesión de administrador (``require_admin`` → 401 sin login, 403 si
no es admin). Operan sobre la tabla de usuarios existente; no añaden esquema nuevo.

  - ``GET    /api/admin/users``            → lista de usuarios.
  - ``PATCH  /api/admin/users/{user_id}``  → activa/desactiva o cambia el rol.
  - ``DELETE /api/admin/users/{user_id}``  → borra la cuenta (cascada a su clave BYOK).

Un admin no puede tocar su propia cuenta desde aquí (400): ver ``services.admin``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_user_repo, require_admin
from app.db.repositories import UserRepository
from app.schemas.auth import UserAdminUpdate, UserInDB, UserPublic
from app.services.admin import (
    SelfModificationError,
    UserNotFoundError,
    delete_user,
    list_users,
    update_user,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
async def list_users_endpoint(
    _admin: UserInDB = Depends(require_admin),
    repo: UserRepository = Depends(get_user_repo),
) -> list[UserInDB]:
    return await list_users(repo=repo)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user_endpoint(
    user_id: UUID,
    payload: UserAdminUpdate,
    admin: UserInDB = Depends(require_admin),
    repo: UserRepository = Depends(get_user_repo),
) -> UserInDB:
    try:
        return await update_user(admin, user_id, payload, repo=repo)
    except SelfModificationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except UserNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found") from e


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: UUID,
    admin: UserInDB = Depends(require_admin),
    repo: UserRepository = Depends(get_user_repo),
) -> None:
    try:
        await delete_user(admin, user_id, repo=repo)
    except SelfModificationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    except UserNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found") from e
