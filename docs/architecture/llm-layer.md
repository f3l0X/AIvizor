# Capa de abstracción LLM

> Estado: implementada en Fase 1 (`backend/app/llm/`).
> Decisión: el motor de IA **no se acopla** al código de negocio. Cambiar de proveedor
> = cambiar una variable de entorno.

## Por qué existe

AIvizor es una pieza de portfolio que demuestra criterio de arquitectura. La decisión
documentada en `PLANNING.md` §3 fue mantener el LLM como detalle de infraestructura,
no como dependencia transversal:

- **Servicios (`analyzer`, `trainer`) nunca importan SDKs concretos.** Hablan con la
  interfaz `LLMProvider`.
- **La salida del LLM siempre va validada contra Pydantic** antes de tocar BD o
  cliente. Si el modelo se desvía del esquema (incluido el caso *prompt injection
  exitoso*), la respuesta se rechaza.
- **El proveedor por defecto es `mock`**, no cuesta dinero y deja correr el pipeline
  en CI y en dev local sin claves.

## Diagrama

```
                                      ┌────────────────────────┐
   analyzer.py                ──────▶ │  LLMProvider (Protocol) │
   trainer.py                 ──────▶ │  complete_structured()  │
                                      └────────────┬───────────┘
                                                   │  inyectado por factory()
                                                   │  según env LLM_PROVIDER
                  ┌────────────────────────────────┼────────────────────────────────┐
                  ▼                                ▼                                ▼
        ┌──────────────────┐           ┌─────────────────────┐         ┌─────────────────────┐
        │  MockProvider    │           │   GeminiProvider    │         │   ClaudeProvider    │
        │  (sin red)       │           │   google-genai SDK  │         │   anthropic SDK     │
        │                  │           │   response_schema   │         │   tool_use forzado  │
        └──────────────────┘           └─────────────────────┘         └─────────────────────┘
```

## Contrato (`base.py`)

```python
class LLMProvider(Protocol):
    name: str
    async def complete_structured(
        self, *,
        system: str,                 # instrucción separada del input no confiable
        user: str,                   # contenido (ya envuelto en delimitadores por el caller)
        response_model: type[T],     # clase Pydantic que valida la respuesta
        language: Language,          # ES | EN — se inyecta en el prompt
    ) -> T: ...
```

Cualquier fallo (timeout, JSON malformado, esquema inválido) se normaliza a `LLMError`
con `provider` y `cause`. El handler de FastAPI puede capturar **un solo tipo** y
mapear a 502/503 sin filtrar internals.

## Implementaciones

### `MockProvider` (`mock.py`)

- Determinista: el `risk_score` se deriva del hash SHA-256 del input.
- Soporta `AnalysisResult` y `TrainingSample`. Si pides otro `response_model`, lanza
  `LLMError` — pista clara para añadir un branch al implementar nuevas features.
- **Doble función como contrato vivo**: si añades un campo al esquema y olvidas
  actualizar el mock, los tests rompen.

### `GeminiProvider` (`gemini.py`)

- SDK: `google-genai` (cliente moderno).
- Estrategia: `response_mime_type="application/json"` + `response_schema=ResponseModel`.
  Gemini acepta clases Pydantic 2 directamente y devuelve `response.parsed`.
- Fallback: si `parsed` es `None`, validamos `response.text` con `model_validate_json`.

### `ClaudeProvider` (`claude.py`)

- SDK: `anthropic` (cliente async).
- Estrategia: **tool use forzado**. Declaramos una herramienta `return_result` cuyo
  `input_schema` es el JSON Schema del `response_model`, y forzamos `tool_choice` a
  esa herramienta. Claude está obligado a "llamarla" → su `input` es nuestro JSON.
- Modelo por defecto: `claude-haiku-4-5-20251001` (rápido y barato para el analyzer).

## Factory (`factory.py`)

- `get_llm() -> LLMProvider` decide por `settings.llm_provider`.
- Cacheada con `lru_cache(maxsize=1)`: una sola instancia por proceso, reusa el cliente
  HTTP (keep-alive, rate limit, etc.).
- **Errores tempranos**: si pides `gemini` o `claude` sin API key, falla *al crear*
  el provider, no al primer request.
- `reset_llm_cache()` solo para tests.

## Cómo cambiar de proveedor

```bash
# .env
LLM_PROVIDER=mock     # por defecto, sin coste
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=...
# LLM_PROVIDER=claude
# ANTHROPIC_API_KEY=...
```

Reinicia el backend. Ni un solo import del código de negocio cambia.

## Tests

- `tests/test_schemas.py` — el contrato Pydantic rechaza datos fuera de rango / fuera
  de catálogo.
- `tests/test_llm_mock.py` — `MockProvider` cumple `Protocol`, es determinista, soporta
  los modelos esperados, falla limpio en los no esperados.
- `tests/test_llm_factory.py` — la factory selecciona por env, lanza error temprano
  cuando falta la key.

No tests "reales" contra Gemini/Claude en CI: la capa de abstracción + mock ya cubre
el contrato. Los providers reales se prueban manualmente con `LLM_PROVIDER=...` y un
sanity check en `Fase 2`.

## Trabajo futuro

- **Reintentos con backoff** dentro de cada provider (timeout / 429), envueltos al
  final como `LLMError` solo si todos los reintentos fallan.
- **Métricas** (tokens, latencia, coste) en un decorator común — quizá `BaseProvider`
  abstracto en lugar de `Protocol` cuando esto entre.
- **Streaming** para el Analyzer si la UI lo pide.
