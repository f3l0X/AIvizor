# Módulo B — Trainer

> Estado: implementado en Fase 5.
> Endpoints: `POST /api/train/next` y `POST /api/train/answer`.
> Frontend: `/<locale>/train`.

## Flujo end-to-end

```
   ┌───────────┐    POST /api/train/next         ┌──────────────────────┐
   │ TrainPage │ ───────────────────────────────▶│ trainer.generate_   │
   │ (client)  │  {difficulty, input_type,       │  sample()           │
   │           │   language}                     └──────────┬──────────┘
   │           │                                            │
   │           │     ┌────────── LLMProvider ────────────────┘
   │           │     ▼                                 ┌─ persistencia ─┐
   │           │  ┌────────────────┐                  │ training_       │
   │           │  │ TrainingSample │────────────────▶ │ attempts (id,   │
   │           │  │ (FULL: con     │  save_sample()   │ sample JSONB,   │
   │           │  │  true_verdict, │                  │ answer=NULL)    │
   │           │  │  true_indic.)  │                  └─────────────────┘
   │           │  └────────┬───────┘
   │           │           │ TrainingSamplePublic
   │           │           │  (SIN la verdad)
   │           │ ◀─────────┘
   │           │
   │  alumno   │
   │  contesta │
   │           │    POST /api/train/answer       ┌──────────────────────┐
   │           │ ───────────────────────────────▶│ trainer.evaluate_   │
   │           │  {sample_id, user_verdict,      │  answer()           │
   │           │   marked_indicator_types}       └──────────┬──────────┘
   │           │                                            │
   │           │              get_sample(id) ◀──────────────┘
   │           │              compara + score + next_difficulty
   │           │              save_answer (UPDATE row)
   │           │
   │           │ ◀─── TrainingFeedback
   └───────────┘    {correct, score, missed_indicators,
                     explanation, next_difficulty}
```

## Decisión clave: la "verdad" no sale del servidor

`TrainingSample` (interno) tiene `true_verdict` y `true_indicators`. Si el
cliente recibiera ese objeto, vería la respuesta correcta antes de contestar.

Solución: dos esquemas distintos.

- `TrainingSample` — completo, persiste en BD, vive server-side.
- `TrainingSamplePublic` — recorte con `{id, input_type, language, difficulty,
  content}`. Es lo que devuelve `/api/train/next`.

El servidor guarda el sample indexado por `id` en `training_attempts`, y el
cliente solo manda `sample_id` + su respuesta. La "verdad" se compara dentro
de `evaluate_answer` sin volver a salir al cliente — solo los `missed_indicators`
viajan de vuelta, y solo después de responder.

## Scoring

```
verdict incorrecto                          → score=0,   missed=todos
verdict correcto, todos indicadores marcados → score=100, missed=[]
verdict correcto, indicadores parciales     → score = 100 * aciertos / total
verdict correcto, sample sin indicadores    → score=100, missed=[]
```

## Dificultad adaptativa

Regla simple v1 (en `_next_difficulty`):

```
correct  → next = min(5, current + 1)
incorrect → next = max(1, current - 1)
```

Sin streaks, sin sesiones, stateless en backend. El cliente recibe la
sugerencia en `feedback.next_difficulty` y la usa para la siguiente llamada.
Si quiere desviarse de la sugerencia, puede — el selector del frontend permite
ajustar manualmente.

Por qué stateless: en v1 no hay autenticación. Cualquier sistema de "racha" en
servidor obligaría a tracking por sesión o por cookie, y el cliente puede
gestionar perfectamente su propio nivel. Si en Fase 6+ se añade login, mover
la lógica al servidor es trivial (el repo ya guarda histórico).

## MockProvider variable por dificultad

`backend/app/llm/mock.py` ahora infiere la dificultad del propio user prompt
(que contiene "dificultad N" / "difficulty N") y devuelve samples distintos
por nivel:

- **L1**: phishing burdo (typos, dominio `.ru`, urgencia exagerada).
- **L2**: igual que L1 con label distinto (placeholder hasta tener un sample
  propio).
- **L3**: phishing más sutil (correos-postal.com con micropago).
- **L4**: igual que L3 con label distinto.
- **L5**: ejemplo **legítimo** — entrena al alumno a no marcar todo como
  phishing, que es un fallo común tras unos cuantos niveles seguidos.

En Fase 6 (o cuando se cambie a Gemini/Claude reales) se sustituyen los L2/L4
por samples nativos del nivel.

## Persistencia

Tabla `training_attempts` (PLANNING.md §5):

| columna       | tipo            | nota                                  |
|---------------|-----------------|---------------------------------------|
| id            | UUID PK         | = TrainingSample.id                   |
| difficulty    | INTEGER         | 1..5                                  |
| sample        | JSONB           | TrainingSample completo (con verdad)  |
| user_answer   | JSONB NULL      | TrainingAnswer (null hasta responder) |
| correct       | BOOLEAN NULL    | null hasta responder                  |
| score         | INTEGER NULL    | null hasta responder                  |
| created_at    | TIMESTAMPTZ     | inserción del sample                  |
| answered_at   | TIMESTAMPTZ NULL| set en `evaluate_answer`              |

Migración: `backend/alembic/versions/0002_training_attempts.py`.

Aplicar:

```bash
docker compose exec backend alembic upgrade head
```

## Frontend

`<TrainerCard>` (`frontend/components/TrainerCard.tsx`):

- Muestra `content` en monospace dentro de un `<pre>`.
- Selector de `verdict` con tres botones (verde/ámbar/rojo según selección).
- Lista de **checkboxes** para los indicadores, en grid 2 columnas.
- Una vez enviada la respuesta, los inputs se bloquean y los checkboxes que
  correspondían a `missed_indicators` se resaltan en ámbar (feedback visual
  inmediato).
- Sección de feedback con badge "✓ Correcto / ✗ Incorrecto", explicación,
  lista de indicadores fallados (con evidencia y explicación), y botón
  "Siguiente (nivel N)" que dispara `/api/train/next` con la dificultad
  sugerida.

`TrainPage` (`frontend/app/[locale]/train/page.tsx`):

- Discriminated union de Status: `idle | loading | sample | submitting |
  feedback | error`.
- Selectores de tipo + dificultad inicial encima de la carta.
- Tras feedback, "Siguiente" mantiene la sesión en la misma página y
  actualiza el `difficulty` local.

## Tests

- `test_trainer_service.py` — generate persiste, evaluate falla con sample
  desconocido, scoring full/wrong/partial, caps de dificultad, ejemplo
  legítimo (8 tests).
- `test_train_api.py` — endpoints E2E: `/next` no filtra la verdad, loop
  completo correcto, 404 en sample desconocido, 422 en dificultad inválida,
  defaults, L5 → legit (6 tests).

86/86 verde al cierre de Fase 5.

## Verificación manual

Con backend en mock + migración aplicada:

```bash
# Pide un sample L1
curl -sX POST http://localhost:8000/api/train/next \
  -H 'Content-Type: application/json' \
  -d '{"difficulty":1,"input_type":"email","language":"es"}'

# Responde con verdict + indicadores marcados
curl -sX POST http://localhost:8000/api/train/answer \
  -H 'Content-Type: application/json' \
  -d '{
    "sample_id": "<id-del-paso-anterior>",
    "user_verdict": "phishing",
    "marked_indicator_types": ["lookalike_domain","urgency_language","brand_or_grammar_error"]
  }'
```

En el navegador: `http://localhost:3000/es/train`.
