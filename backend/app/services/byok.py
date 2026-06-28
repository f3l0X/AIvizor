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
        created_at=stored.created_at,
        updated_at=stored.updated_at,
    )


async def set_api_key(
    user_id: UUID, data: ApiKeyCreate, *, repo: ApiKeyRepository
) -> ApiKeyPublic:
    """Crea o reemplaza la clave BYOK del usuario. Devuelve la vista pública."""
    stored = await repo.upsert(
        user_id=user_id,
        provider=data.provider,
        api_key_encrypted=encrypt_secret(data.api_key),
        model=data.model,
    )
    return _to_public(stored)


async def get_api_key(user_id: UUID, *, repo: ApiKeyRepository) -> ApiKeyPublic | None:
    """Devuelve la vista pública de la clave del usuario, o ``None`` si no tiene."""
    stored = await repo.get(user_id)
    return _to_public(stored) if stored is not None else None


async def delete_api_key(user_id: UUID, *, repo: ApiKeyRepository) -> bool:
    """Borra la clave BYOK del usuario. ``True`` si existía."""
    return await repo.delete(user_id)


async def resolve_provider_for_user(
    user_id: UUID, *, repo: ApiKeyRepository
) -> LLMProvider | None:
    """Construye el ``LLMProvider`` del usuario desde su clave BYOK, o ``None``.

    Lanza ``LLMError`` si hay una clave configurada pero no se puede usar (no se
    descifra, o el provider no se puede construir): preferimos fallar visiblemente a
    gastar silenciosamente la clave del servidor cuando el usuario pidió usar la suya.
    """
    stored = await repo.get(user_id)
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
