"""Cifrado simétrico de secretos en reposo (Fase 7.3 — BYOK).

Las API keys de LLM que aporta el usuario son secretos: nunca se guardan en claro
en la BD. Se cifran con **Fernet** (AES-128-CBC + HMAC-SHA256, claves rotables) a
partir de ``settings.byok_encryption_key``.

Frontera de responsabilidades:
  - Este módulo solo cifra/descifra cadenas. No conoce usuarios ni BD.
  - El servicio ``byok`` decide *qué* cifrar y *cuándo*; el repositorio solo
    persiste el texto cifrado.

``decrypt_secret`` traduce cualquier token inválido (clave rotada, dato corrupto)
a ``CryptoError`` en vez de filtrar la excepción del SDK.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class CryptoError(Exception):
    """No se pudo descifrar un secreto (clave incorrecta o dato corrupto)."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """Instancia Fernet cacheada. Falla ruidosamente si la clave no es válida."""
    try:
        return Fernet(settings.byok_encryption_key.encode("utf-8"))
    except (ValueError, TypeError) as e:  # clave mal formada en config
        raise CryptoError(
            "BYOK_ENCRYPTION_KEY no es una clave Fernet válida (urlsafe base64, 32 bytes)."
        ) from e


def encrypt_secret(plaintext: str) -> str:
    """Cifra un secreto y devuelve el token Fernet como str listo para persistir."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Descifra un token Fernet. Lanza ``CryptoError`` si no es válido."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as e:
        raise CryptoError("No se pudo descifrar el secreto.") from e


def reset_fernet_cache() -> None:
    """Solo para tests: recrea la instancia tras cambiar la clave en settings."""
    _fernet.cache_clear()
