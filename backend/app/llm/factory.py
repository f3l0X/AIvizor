"""Factory de `LLMProvider`. Punto único donde se decide qué implementación inyectar.

Política:
  - La selección depende exclusivamente de ``settings.llm_provider`` (env
    ``LLM_PROVIDER`` ∈ {gemini, claude, mock}).
  - Si pides ``gemini`` o ``claude`` y falta la API key correspondiente, se lanza
    ``LLMError`` *al crear el provider*, no al primer uso: error temprano, ruidoso.
  - Cacheamos la instancia con ``lru_cache`` para que los servicios reusen el mismo
    cliente HTTP a lo largo del proceso (importante para keep-alive y rate limit).

Pendiente Fase 2: FastAPI dependency ``get_llm() -> LLMProvider`` que llame aquí.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.llm.base import LLMError, LLMProvider
from app.llm.claude import ClaudeProvider
from app.llm.gemini import GeminiProvider
from app.llm.mock import MockProvider


@lru_cache(maxsize=1)
def get_llm() -> LLMProvider:
    """Devuelve el provider seleccionado por configuración. Cacheado por proceso."""

    provider = settings.llm_provider

    if provider == "mock":
        return MockProvider()
    if provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
    if provider == "claude":
        return ClaudeProvider(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )

    raise LLMError(
        f"LLM_PROVIDER='{provider}' no soportado. Usa 'mock', 'gemini' o 'claude'.",
        provider=provider,
    )


def reset_llm_cache() -> None:
    """Solo para tests: forzar recreación tras cambiar env vars."""
    get_llm.cache_clear()
