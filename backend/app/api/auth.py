"""Endpoints de autenticación: ``/api/auth/{register,login,logout,me}`` (Fase 7.2).

Sesión basada en JWT servido en cookie httpOnly (no accesible desde JS → mitiga XSS).
El registro hace auto-login (deja la cookie puesta) para simplificar el flujo del front.

Expone además las dependencies reutilizables:
  - ``get_current_user`` → 401 si no hay sesión válida.
  - ``require_admin``    → 403 si la sesión no es de un admin.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.repositories import SqlUserRepository, UserRepository
from app.db.session import get_db
from app.schemas.auth import Role, UserCreate, UserInDB, UserLogin, UserPublic
from app.security.tokens import create_access_token, decode_access_token
from app.services.auth import (
    EmailTakenError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Dependency override-able en tests."""
    return SqlUserRepository(session)


def _set_auth_cookie(response: Response, user: UserInDB) -> None:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


async def get_current_user(
    request: Request,
    repo: UserRepository = Depends(get_user_repo),
) -> UserInDB:
    """Resuelve la sesión desde la cookie. Lanza 401 si falta o es inválida."""
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token subject") from e
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


async def require_admin(user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return user


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    response: Response,
    repo: UserRepository = Depends(get_user_repo),
) -> UserInDB:
    try:
        user = await register_user(payload, repo=repo)
    except EmailTakenError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from e
    _set_auth_cookie(response, user)
    return user


@router.post("/login", response_model=UserPublic)
async def login(
    payload: UserLogin,
    response: Response,
    repo: UserRepository = Depends(get_user_repo),
) -> UserInDB:
    try:
        user = await authenticate_user(payload, repo=repo)
    except InvalidCredentialsError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from e
    except InactiveUserError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled") from e
    _set_auth_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(key=settings.cookie_name, path="/")


@router.get("/me", response_model=UserPublic)
async def me(user: UserInDB = Depends(get_current_user)) -> UserInDB:
    return user
