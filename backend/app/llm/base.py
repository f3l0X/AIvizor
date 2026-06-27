"""Interfaz `LLMProvider` y errores del dominio LLM.

Esta es la **única superficie** que ven los servicios (`analyzer`, `trainer`). Cambiar
de proveedor (Gemini ↔ Claude ↔ mock) significa cambiar la variable de entorno
``LLM_PROVIDER``: ni un import del SDK concreto se cuela en la lógica de negocio.

Contrato:

- Toda llamada es **asíncrona** (las APIs externas son I/O bound).
- El cliente pasa un ``response_model`` (clase Pydantic) y el provider está obligado a
  devolver una instancia válida. Si el modelo del LLM responde fuera de esquema, el
  provider valida con Pydantic, captura el ``ValidationError`` y lo re-lanza como
  ``LLMError`` con suficiente contexto para depurar.
- Esto también es la **primera línea anti prompt-injection**: si el atacante consigue
  que el LLM "obedezca" su instrucción y se salga del formato, la respuesta se rechaza
  antes de tocar BD o cliente (ver Fase 3).
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from app.schemas.common import Language

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Error de la capa LLM. Cualquier fallo del proveedor (timeout, mal JSON, esquema
    inválido, rate limit) se normaliza a este tipo para que la API exponga un 502/503
    coherente sin filtrar detalles del SDK.
    """

    def __init__(self, message: str, *, provider: str, cause: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause

    def __str__(self) -> str:
        base = f"[{self.provider}] {super().__str__()}"
        if self.cause is not None:
            base += f" (cause: {type(self.cause).__name__}: {self.cause})"
        return base


@runtime_checkable
class LLMProvider(Protocol):
    """Contrato común para Gemini / Claude / Mock.

    Implementaciones:
      - `app.llm.mock.MockProvider`     — sin red, sin coste; usado en tests y dev.
      - `app.llm.gemini.GeminiProvider` — google-genai con response_schema.
      - `app.llm.claude.ClaudeProvider` — anthropic con tool use para forzar JSON.
    """

    name: str

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        language: Language,
    ) -> T:
        """Pide al LLM una respuesta JSON que valide contra ``response_model``.

        Args:
            system:         Instrucciones del sistema. **Nunca** contiene input de
                            usuario sin delimitar (ver Fase 3 anti-injection).
            user:           Contenido a procesar. Para el Analyzer es la cadena
                            sospechosa, envuelta en delimitadores por el caller.
            response_model: Clase Pydantic que define el contrato de salida. El
                            provider se encarga de empujarle al LLM el JSON schema
                            correspondiente y de validar la respuesta.
            language:       ``Language.ES`` o ``Language.EN``. Se inyecta para que la
                            salida (explicaciones, summary) vaya en ese idioma.

        Returns:
            Instancia de ``response_model`` ya validada.

        Raises:
            LLMError: el proveedor falló, respondió JSON inválido, o la respuesta no
                cumple el esquema. La lógica de negocio puede capturar este único tipo.
        """
        ...
