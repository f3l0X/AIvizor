"""Hashing y política de contraseñas (Fases 7.2 y 7.8).

bcrypt opera sobre como máximo 72 bytes; truncamos explícitamente para evitar el
``ValueError`` que lanzan las versiones modernas de ``bcrypt`` con entradas más largas.
72 bytes de entropía son de sobra para una contraseña.

La política de fortaleza (``validate_password_strength``) vive aquí junto al
hashing: es la otra mitad de "qué es una contraseña aceptable". Las reglas se
leen de ``settings`` en cada llamada, así que son configurables por env y los
tests pueden apagarlas con monkeypatch.
"""

from __future__ import annotations

import bcrypt

from app.config import settings

_MAX_BYTES = 72

# Contraseñas ultra comunes (candidatas nº1 de cualquier diccionario de fuerza
# bruta). Comparación con casefold(): "Password123" también cae. Lista corta a
# propósito — las reglas de composición ya filtran la mayoría; esto caza las que
# las cumplen siendo triviales.
_COMMON_PASSWORDS = frozenset(
    {
        "password", "password1", "password123", "passw0rd", "p@ssw0rd",
        "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop",
        "iloveyou", "sunshine1", "princess1", "welcome1", "admin123",
        "abc12345", "letmein1", "football1", "dragon123", "monkey123",
        "contraseña", "contrasena1", "abcd1234", "aa123456", "qwerty12",
    }
)


def validate_password_strength(password: str) -> list[str]:
    """Devuelve los códigos de requisitos NO cumplidos (vacía = contraseña válida).

    Códigos: ``min_length``, ``uppercase``, ``lowercase``, ``digit``, ``special``,
    ``common``. Cada regla se activa/desactiva vía settings (política equilibrada
    por defecto: 8+ chars, mayúscula, minúscula y número; sin símbolo obligatorio).
    """
    failures: list[str] = []
    if len(password) < settings.password_min_length:
        failures.append("min_length")
    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        failures.append("uppercase")
    if settings.password_require_lowercase and not any(c.islower() for c in password):
        failures.append("lowercase")
    if settings.password_require_digit and not any(c.isdigit() for c in password):
        failures.append("digit")
    if settings.password_require_special and all(c.isalnum() for c in password):
        failures.append("special")
    if settings.password_reject_common and password.casefold() in _COMMON_PASSWORDS:
        failures.append("common")
    return failures


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
