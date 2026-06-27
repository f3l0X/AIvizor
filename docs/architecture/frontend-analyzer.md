# Frontend — Analyzer (Fase 4)

> Estado: implementado.
> Stack: Next.js 14 (App Router) + TypeScript + Tailwind + next-intl.
> Ubicación: `frontend/app/[locale]/analyze/page.tsx` + `frontend/components/*`.

## Flujo de pantallas

```
   /<locale>/analyze
        │
        ▼
   ┌────────────────────────────┐
   │ <AnalyzeForm>              │ ← textarea + selectores + submit
   └────────────┬───────────────┘
                │ onSubmit
                ▼
   POST /api/analyze (lib/api.ts)
                │
       ┌────────┴─────────┐
       ▼                  ▼
   200 OK             4xx / 5xx
       │                  │
       ▼                  ▼
   ┌─────────────┐  ┌─────────────┐
   │ <AnalysisResultView/> │  │ banner de error │
   │  ├ <RiskMeter/>       │  │ (mantiene input)│
   │  ├ summary            │  └─────────────────┘
   │  └ [<IndicatorCard/>] │
   └───────────────────────┘
```

## Estado de la página

`AnalyzePage` (cliente) mantiene un único discriminated union:

```ts
type Status =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; result: AnalysisResult }
  | { kind: 'error'; message: string };
```

Pros: render trivial, sin estados imposibles ("loading + error simultáneo"), y
TypeScript fuerza a tratar cada caso. Pattern usado deliberadamente como ejemplo
para LinkedIn ("modelar el estado con union types").

## Componentes

### `<RiskMeter score verdict />`

- Barra horizontal coloreada según verdict (verde / ámbar / rojo).
- Puntero negro en la posición exacta del score (accesibilidad: la barra sirve
  aunque el daltonismo afecte al color).
- Score numérico grande y badge con el verdict traducido.
- `role="progressbar"` con `aria-valuenow/min/max`.

### `<IndicatorCard indicator />`

- Icono emoji por `IndicatorType` (rápido, ligero, sin sprites; cambiable a SVGs
  en Fase 6 si se quiere pulir).
- **Evidencia en monospace** dentro de un bloque `<pre>`: deliberado, queremos
  que el usuario vea que es el texto LITERAL del input, no una paráfrasis.
- Explicación educativa debajo.

### `<AnalyzeForm defaultLanguage onSubmit isLoading />`

- Controla su propio input (textarea + selectores).
- Limita a 20 000 chars con contador visible (alineado con el `max_length` del
  backend).
- Botón deshabilitado si el contenido está vacío o si hay un request en vuelo.
- No persiste estado al desmontar: la página es la dueña del flujo.

### `<AnalysisResultView result />`

- Composición sin estado: `RiskMeter` + summary + lista de indicadores.
- `aria-live="polite"` para que lectores de pantalla anuncien el resultado.
- Mensaje específico cuando la lista de indicadores está vacía (no es un bug,
  es un veredicto LEGIT plausible).

## Cliente API (`lib/api.ts`)

- `analyze(req)` → `Promise<AnalysisResult>`.
- Errores normalizados a `ApiError` con `status` y `detail`.
- `isClientError` / `isServerError` exponen la distinción 4xx / 5xx para que la
  UI decida si reintentar automáticamente o pedir corrección al usuario.

`NEXT_PUBLIC_API_URL` viene del `.env`. En dev por defecto:
`http://localhost:8000`. En docker-compose, lo provee `services.frontend.env_file`.

## Tipos (`lib/types.ts`)

Espejo manual de los esquemas Pydantic del backend
(`backend/app/schemas/{common,analysis}.py`). Si añades un `IndicatorType` allí,
**añádelo también aquí** — TypeScript no lo deriva automáticamente. Para la v1
mantener la sincronización manual es asumible; en una iteración futura se puede
generar con `datamodel-codegen` desde el JSON Schema expuesto por FastAPI.

## Internacionalización

- next-intl con prefijo `[locale]` en la URL (`/es/analyze`, `/en/analyze`).
- Cadenas en `frontend/messages/{es,en}.json`.
- Plural con sintaxis ICU para el contador de indicadores
  (`{count, plural, =0 {...} one {...} other {...}}`).
- El idioma del análisis se inicializa con el `locale` de la URL pero el usuario
  puede sobreescribirlo desde el formulario sin cambiar la URL.

## Accesibilidad (mínimos de v1)

- Labels asociados a inputs (`htmlFor` / `id`).
- `role="progressbar"` en el meter.
- `aria-live="polite"` en el bloque de resultado.
- Contraste suficiente en modo claro y oscuro (Tailwind `slate-*` + colores de
  verdict).
- Foco visible (Tailwind `focus:ring-*` por defecto).

Pendiente Fase 6+: navegación con teclado en cards, skip-link, audit Axe.

## Cómo probar

```bash
# 1) Backend con mock (sin coste de API):
cp .env.example .env
docker compose up backend db

# 2) Frontend:
cd frontend
npm install
npm run dev
# → http://localhost:3000/es/analyze
```

Pega cualquier texto (el mock devuelve algo determinista basado en su hash) y
verás la disección. Cambia `LLM_PROVIDER=gemini|claude` en `.env` para salida
real.
