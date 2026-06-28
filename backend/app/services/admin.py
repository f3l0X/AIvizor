"""Lógica de dominio del panel admin (Fase 7.5).

Gestión de usuarios por parte de un administrador: listar, activar/desactivar,
cambiar de rol y borrar cuentas. Como el resto de servicios, solo habla con el
``UserRepository``; no conoce HTTP ni SQLAlchemy. La capa API traduce estas
excepciones a códigos de estado.

Regla de seguridad clave: **un admin no puede modificarse ni borrarse a sí mismo**
desde el panel. Evita el auto-bloqueo (desactivarse o degradarse y quedar sin
ningún admin activo). Para cambiar la propia cuenta debe hacerlo otro admin.
"""

from __future__ import annotations

from uuid import UUID

from app.db.repositories import UserRepository
from app.schemas.auth import UserAdminUpdate, UserInDB


class AdminError(Exception):
    """Base de los errores del panel admin."""


class UserNotFoundError(AdminError):
    """El usuario objetivo no existe."""


class SelfModificationError(AdminError):
    """El admin intenta modificarse/borrarse a sí mismo (prohibido)."""


async def list_users(*, repo: UserRepository) -> list[UserInDB]:
    return await repo.list_all()


async def update_user(
    actor: UserInDB,
    target_id: UUID,
    data: UserAdminUpdate,
    *,
    repo: UserRepository,
) -> UserInDB:
    if target_id == actor.id:
        raise SelfModificationError("Cannot modify your own account")
    updated = await repo.update(target_id, is_active=data.is_active, role=data.role)
    if updated is None:
        raise UserNotFoundError(str(target_id))
    return updated


async def delete_user(
    actor: UserInDB,
    target_id: UUID,
    *,
    repo: UserRepository,
) -> None:
    if target_id == actor.id:
        raise SelfModificationError("Cannot delete your own account")
    if not await repo.delete(target_id):
        raise UserNotFoundError(str(target_id))
