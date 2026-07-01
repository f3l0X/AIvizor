"""`ClaudeProvider` — implementación con Anthropic Claude.

Estrategia de salida estructurada:
  - Usamos **tool use forzado**: declaramos una herramienta ``return_result`` cuyo
    ``input_schema`` es el JSON Schema del ``response_model`` Pydantic, y pasamos
    ``tool_choice={"type": "tool", "name": "return_result"}``. Claude está obligado a
    "llamar" a esa herramienta, y nosotros leemos su ``input`` como el JSON final.
  - Esta táctica es la más fiable a día de hoy para forzar JSON con Anthropic: el
    modelo no puede salirse del esquema sin que la API marque error.
  - Como segundo cinturón, validamos el ``input`` con Pydantic — si el modelo aun así
    metiera un campo inválido, lo convertimos en ``LLMError``.

Modelo por defecto: ``claude-haiku-4-5-20251001`` (rápido y barato, suficiente para el
analizador). Se puede subir a Sonnet 4.6 vía env ``CLAUDE_MODEL`` para el entrenador
si se quiere mayor calidad de ejemplos.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMError
from app.schemas.common import Language

T = TypeVar("T", bound=BaseModel)

_TOOL_NAME = "return_result"
_MAX_TOKENS = 4096


class ClaudeProvider:
    """LLMProvider sobre la API de Anthropic."""

    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY vacía", provider=self.name)
        try:
            from anthropic import AsyncAnthropic  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise LLMError(
                "anthropic SDK no está instalado. `pip install anthropic`.",
                provider=self.name,
                cause=e,
            ) from e

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def validate(self) -> None:
        """Ping mínimo (1 token) para confirmar que la clave y el modelo valen."""
        try:
            await self._client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
        except Exception as e:
            raise LLMError(
                f"Claude rechazó la clave o el modelo: {e}",
                provider=self.name,
                cause=e,
            ) from e

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        language: Language,
    ) -> T:
        schema = response_model.model_json_schema()
        tool = {
            "name": _TOOL_NAME,
            "description": f"Return the structured result as {response_model.__name__}.",
            "input_schema": schema,
        }

        try:
            resp = await self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=self._with_language(system, language),
                messages=[{"role": "user", "content": user}],
                tools=[tool],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                temperature=0.2,
            )
        except Exception as e:
            raise LLMError(
                f"Claude falló durante messages.create: {e}",
                provider=self.name,
                cause=e,
            ) from e

        tool_input = self._extract_tool_input(resp)
        if tool_input is None:
            raise LLMError(
                f"Claude no devolvió un bloque tool_use para {_TOOL_NAME}.",
                provider=self.name,
            )

        try:
            return response_model.model_validate(tool_input)
        except ValidationError as e:
            raise LLMError(
                f"Claude devolvió tool_use que no cumple {response_model.__name__}: {e}",
                provider=self.name,
                cause=e,
            ) from e

    @staticmethod
    def _extract_tool_input(resp: Any) -> dict | None:
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == _TOOL_NAME:
                return block.input  # type: ignore[no-any-return]
        return None

    @staticmethod
    def _with_language(system: str, language: Language) -> str:
        suffix = (
            "\n\nResponde siempre en español."
            if language is Language.ES
            else "\n\nAlways respond in English."
        )
        return system + suffix
