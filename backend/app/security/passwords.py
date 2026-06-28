"""Hashing de contraseñas con bcrypt (Fase 7.2).

bcrypt opera sobre como máximo 72 bytes; truncamos explícitamente para evitar el
``ValueError`` que lanzan las versiones modernas de ``bcrypt`` con entradas más largas.
72 bytes de entropía son de sobra para una contraseña.
"""

from __future__ import annotations

import bcrypt

_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash malformado en BD → tratamos como credencial inválida, sin reventar.
        return False
