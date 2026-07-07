"""Esquemas de autenticación (Fase 7.2).

Tres niveles de representación de un usuario, deliberadamente separados:

  - ``UserCreate`` / ``UserLogin`` — entrada del cliente (incluye contraseña en claro).
  - ``UserInDB``                  — vista interna del backend (incluye ``password_hash``).
                                    NUNCA se serializa hacia el cliente.
  - ``UserPublic``                — salida segura al cliente (sin contraseña ni hash).

El password_hash jamás cruza la frontera HTTP: los endpoints responden con ``UserPublic``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Role(str, Enum):
    """Rol de la cuenta. ``admin`` accede al panel de gestión; ``user`` es el rol normal."""

    ADMIN = "admin"
    USER = "user"


class UserCreate(BaseModel):
    """Registro público. La contraseña se valida en longitud, nunca en contenido aquí."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(BaseModel):
    """Cambio de contraseña del propio usuario (requiere la actual).

    ``current_password`` solo exige no estar vacía (se verifica contra el hash);
    ``new_password`` pasa además la política de fortaleza en el servicio.
    """

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserInDB(BaseModel):
    """Representación interna con el hash. Uso exclusivo del backend (auth/services)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    password_hash: str
    role: Role
    is_active: bool
    created_at: datetime


class UserPublic(BaseModel):
    """Lo que ve el cliente. Sin ``password`` ni ``password_hash``."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class UserAdminUpdate(BaseModel):
    """Cambios que un admin aplica a OTRA cuenta desde el panel (Fase 7.5).

    Semántica PATCH: solo se modifica el campo que viene; ``None`` = no tocar.
    Permite activar/desactivar (``is_active``) y cambiar de rol (``role``).
    """

    is_active: bool | None = None
    role: Role | None = None
