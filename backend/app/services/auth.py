"""Lógica de dominio de autenticación (Fase 7.2).

Solo habla con el ``UserRepository`` y las utilidades de ``security``; no conoce HTTP
ni SQLAlchemy. La capa API traduce estas excepciones a códigos de estado.
"""

from __future__ import annotations

from app.config import settings
from app.db.repositories import UserRepository
from app.schemas.auth import Role, UserCreate, UserInDB, UserLogin
from app.security.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)


class AuthError(Exception):
    """Base de los errores de auth de dominio."""


class EmailTakenError(AuthError):
    """El email ya está registrado."""


class WeakPasswordError(AuthError):
    """La contraseña no cumple la política (Fase 7.8). ``failures`` trae los códigos."""

    def __init__(self, failures: list[str]) -> None:
        super().__init__(", ".join(failures))
        self.failures = failures


class InvalidCredentialsError(AuthError):
    """Email inexistente o contraseña incorrecta. Mensaje deliberadamente genérico."""


class InactiveUserError(AuthError):
    """La cuenta existe pero está deshabilitada."""


async def register_user(
    data: UserCreate,
    *,
    repo: UserRepository,
    role: Role = Role.USER,
) -> UserInDB:
    # Política de contraseñas (solo registro público; el admin sembrado por env
    # entra por ensure_admin y queda exento a propósito — ver auth.md).
    failures = validate_password_strength(data.password)
    if failures:
        raise WeakPasswordError(failures)
    if await repo.get_by_email(data.email) is not None:
        raise EmailTakenError(data.email)
    return await repo.create(
        email=data.email,
        password_hash=hash_password(data.password),
        role=role,
    )


async def authenticate_user(data: UserLogin, *, repo: UserRepository) -> UserInDB:
    user = await repo.get_by_email(data.email)
    # Verificamos siempre para no filtrar por timing si el email existe o no.
    valid = user is not None and verify_password(data.password, user.password_hash)
    if not valid:
        raise InvalidCredentialsError(data.email)
    if not user.is_active:  # type: ignore[union-attr]  (user no es None aquí)
        raise InactiveUserError(data.email)
    return user  # type: ignore[return-value]


async def ensure_admin(repo: UserRepository) -> bool:
    """Siembra el admin inicial a partir de ``settings`` si no existe ya.

    Idempotente y silenciosa si ``ADMIN_EMAIL``/``ADMIN_PASSWORD`` no están definidos.
    Devuelve ``True`` solo si creó la cuenta.
    """

    if not (settings.admin_email and settings.admin_password):
        return False
    if await repo.get_by_email(settings.admin_email) is not None:
        return False
    await repo.create(
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
        role=Role.ADMIN,
    )
    return True
