"""Lógica de dominio de BYOK — *Bring Your Own Key* (Fase 7.3).

Orquesta el ``ApiKeyRepository`` y la capa de ``crypto``; no conoce HTTP ni
SQLAlchemy. Responsabilidades:

  - Guardar/leer/borrar la clave BYOK de un usuario, cifrándola en reposo.
  - Exponer al cliente solo una vista segura (``ApiKeyPublic`` con la clave enmascarada).
  - Resolver el ``LLMProvider`` de un usuario a partir de su clave descifrada, para que
    Analyzer/Trainer usen *su* cuenta de LLM en vez de la del servidor.

Si un usuario no tiene clave BYOK, ``resolve_provider_for_user`` devuelve ``None`` y el
caller cae al provider por defecto del servidor (uso anónimo / demo sigue funcionando).
"""

from __future__ import annotations

from uuid import UUID

from app.db.repositories import ApiKeyRepository
from app.llm.base import LLMError, LLMProvider
from app.llm.factory import build_provider_cached
from app.schemas.byok import ApiKeyCreate, ApiKeyPublic, StoredApiKey, mask_key
from app.security.crypto import CryptoError, decrypt_secret, encrypt_secret


class NoApiKeyError(Exception):
    """Se intentó activar un proveedor del que el usuario no tiene clave."""


def _to_public(stored: StoredApiKey) -> ApiKeyPublic:
    """Convierte la vista interna en la pública, enmascarando la clave descifrada."""
    try:
        plaintext = decrypt_secret(stored.api_key_encrypted)
        masked = mask_key(plaintext)
    except CryptoError:
        # Clave rotada o dato corrupto: no reventamos el GET, mostramos máscara vacía.
        masked = "••••"
    return ApiKeyPublic(
        provider=stored.provider,
        model=stored.model,
        masked_key=masked,
        is_active=stored.is_active,
        created_at=stored.created_at,
        updated_at=stored.updated_at,
    )


async def set_api_key(
    user_id: UUID, data: ApiKeyCreate, *, repo: ApiKeyRepository
) -> ApiKeyPublic:
    """Crea o reemplaza la clave del proveedor. La primera del usuario queda activa."""
    await repo.upsert(
        user_id=user_id,
        provider=data.provider,
        api_key_encrypted=encrypt_secret(data.api_key),
        model=data.model,
    )
    # Re-leemos para reflejar el is_active definitivo (lo decide el repo en el alta).
    stored = await repo.get(user_id, data.provider)
    assert stored is not None  # acabamos de guardarla
    return _to_public(stored)


async def list_api_keys(user_id: UUID, *, repo: ApiKeyRepository) -> list[ApiKeyPublic]:
    """Vista pública de todas las claves del usuario (enmascaradas)."""
    return [_to_public(s) for s in await repo.list_for_user(user_id)]


async def set_active_provider(
    user_id: UUID, provider: str, *, repo: ApiKeyRepository
) -> ApiKeyPublic:
    """Marca activo el proveedor indicado. Lanza ``NoApiKeyError`` si no hay clave suya."""
    stored = await repo.set_active(user_id, provider)
    if stored is None:
        raise NoApiKeyError(provider)
    return _to_public(stored)


async def delete_api_key(user_id: UUID, provider: str, *, repo: ApiKeyRepository) -> bool:
    """Borra la clave de un proveedor. Si era la activa y queda otra, la activa."""
    existing = await repo.get(user_id, provider)
    was_active = existing is not None and existing.is_active
    deleted = await repo.delete(user_id, provider)
    if deleted and was_active:
        remaining = await repo.list_for_user(user_id)
        if remaining:
            await repo.set_active(user_id, remaining[0].provider)
    return deleted


async def resolve_provider_for_user(
    user_id: UUID, *, repo: ApiKeyRepository
) -> LLMProvider | None:
    """Construye el ``LLMProvider`` del usuario desde su clave BYOK **activa**, o ``None``.

    Lanza ``LLMError`` si hay una clave activa pero no se puede usar (no se descifra,
    o el provider no se puede construir): preferimos fallar visiblemente a gastar
    silenciosamente la clave del servidor cuando el usuario pidió usar la suya.
    """
    stored = await repo.get_active(user_id)
    if stored is None:
        return None
    try:
        api_key = decrypt_secret(stored.api_key_encrypted)
    except CryptoError as e:
        raise LLMError(
            "No se pudo descifrar tu API key (¿clave de cifrado rotada?). "
            "Vuelve a guardarla.",
            provider=stored.provider,
            cause=e,
        ) from e
    return build_provider_cached(stored.provider, api_key, stored.model)
