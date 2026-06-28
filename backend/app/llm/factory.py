"""Factory de `LLMProvider`. Punto único donde se decide qué implementación inyectar.

Dos caminos, una sola construcción (`build_provider`):
  - **Default por entorno** (`get_llm`): el provider se elige con ``settings.llm_provider``
    (env ``LLM_PROVIDER`` ∈ {gemini, claude, mock}) usando las claves del servidor.
    Cacheado por proceso con ``lru_cache`` para reusar el cliente HTTP.
  - **BYOK** (`build_provider_cached`, Fase 7.3): un usuario aporta su propia clave; se
    construye un provider con ella. Se cachea por (provider, clave, modelo) para reusar
    el cliente entre requests del mismo usuario sin recrearlo en cada llamada.

Si pides ``gemini``/``claude`` sin clave, se lanza ``LLMError`` *al construir*, no al
primer uso: error temprano y ruidoso.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.llm.base import LLMError, LLMProvider
from app.llm.claude import ClaudeProvider
from app.llm.gemini import GeminiProvider
from app.llm.mock import MockProvider


def build_provider(
    provider: str, *, api_key: str = "", model: str | None = None
) -> LLMProvider:
    """Construye un provider concreto a partir de sus parámetros.

    ``model=None`` cae al modelo por defecto del provider (de ``settings``). El ``mock``
    ignora ``api_key``/``model``.
    """

    if provider == "mock":
        return MockProvider()
    if provider == "gemini":
        return GeminiProvider(api_key=api_key, model=model or settings.gemini_model)
    if provider == "claude":
        return ClaudeProvider(api_key=api_key, model=model or settings.claude_model)

    raise LLMError(
        f"LLM_PROVIDER='{provider}' no soportado. Usa 'mock', 'gemini' o 'claude'.",
        provider=provider,
    )


@lru_cache(maxsize=32)
def build_provider_cached(
    provider: str, api_key: str, model: str | None
) -> LLMProvider:
    """Variante cacheada para BYOK: reusa el cliente HTTP por (provider, clave, modelo).

    La clave ya viaja en claro en memoria en este punto (descifrada por el servicio),
    así que cachearla aquí no añade exposición. Argumentos posicionales para que
    ``lru_cache`` los use como parte de la clave.
    """
    return build_provider(provider, api_key=api_key, model=model)


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    """Provider por defecto del servidor, según configuración. Cacheado por proceso."""

    provider = settings.llm_provider
    if provider == "mock":
        return build_provider("mock")
    if provider == "gemini":
        return build_provider("gemini", api_key=settings.gemini_api_key)
    if provider == "claude":
        return build_provider("claude", api_key=settings.anthropic_api_key)

    raise LLMError(
        f"LLM_PROVIDER='{provider}' no soportado. Usa 'mock', 'gemini' o 'claude'.",
        provider=provider,
    )


def reset_llm_cache() -> None:
    """Solo para tests: forzar recreación tras cambiar env vars."""
    get_llm.cache_clear()
    build_provider_cached.cache_clear()
