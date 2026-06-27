"""`GeminiProvider` — implementación con Google Gemini (google-genai SDK).

Estrategia de salida estructurada:
  - Se pasa ``response_mime_type='application/json'`` y ``response_schema=<Pydantic>``
    a la API. Gemini ya acepta clases Pydantic 2 directamente y devuelve el JSON
    parseado en ``response.parsed``.
  - Si el SDK no consigue parsearlo (rara vez), caemos a ``response.text`` y validamos
    a mano con ``model_validate_json``.
  - Cualquier excepción del SDK se traduce a ``LLMError`` para mantener la frontera
    de la capa LLM cerrada.

El SDK es opcional en tiempo de import: si el módulo se carga y google-genai no está
instalado, no fallamos hasta que alguien intente construir el provider. Esto evita que
el `mock` se rompa en entornos minimalistas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMError
from app.schemas.common import Language

if TYPE_CHECKING:  # pragma: no cover
    pass

T = TypeVar("T", bound=BaseModel)


class GeminiProvider:
    """LLMProvider sobre la API de Google Gemini."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        if not api_key:
            raise LLMError("GEMINI_API_KEY vacía", provider=self.name)
        try:
            from google import genai  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise LLMError(
                "google-genai no está instalado. `pip install google-genai`.",
                provider=self.name,
                cause=e,
            ) from e

        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        language: Language,
    ) -> T:
        try:
            from google.genai import types  # type: ignore

            config = types.GenerateContentConfig(
                system_instruction=self._with_language(system, language),
                response_mime_type="application/json",
                response_schema=response_model,
                temperature=0.2,
            )

            resp = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user,
                config=config,
            )
        except Exception as e:  # SDK puede lanzar varios tipos; los normalizamos.
            raise LLMError(
                f"Gemini falló durante generate_content: {e}",
                provider=self.name,
                cause=e,
            ) from e

        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, response_model):
            return parsed

        # Fallback: validar el texto crudo.
        text = getattr(resp, "text", None) or ""
        if not text:
            raise LLMError(
                "Gemini devolvió respuesta vacía.",
                provider=self.name,
            )

        try:
            return response_model.model_validate_json(text)
        except ValidationError as e:
            raise LLMError(
                f"Gemini devolvió JSON que no cumple {response_model.__name__}: {e}",
                provider=self.name,
                cause=e,
            ) from e

    @staticmethod
    def _with_language(system: str, language: Language) -> str:
        suffix = (
            "\n\nResponde siempre en español."
            if language is Language.ES
            else "\n\nAlways respond in English."
        )
        return system + suffix
