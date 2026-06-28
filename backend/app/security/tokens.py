"""JWT de acceso (Fase 7.2).

Token firmado HS256 con el secreto de ``settings``. Payload mínimo:
  - ``sub``  → id del usuario (str(UUID)).
  - ``role`` → rol, para autorizar sin golpear la BD en cada check ligero.
  - ``iat`` / ``exp`` → emisión y expiración.

``decode_access_token`` nunca lanza: devuelve ``None`` ante cualquier token inválido,
expirado o manipulado, y el caller traduce eso a 401.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def create_access_token(*, subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
