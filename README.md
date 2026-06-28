# AIvizor

[![Backend tests](https://github.com/f3l0X/AIvizor/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/f3l0X/AIvizor/actions/workflows/backend-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

> **Tu ojo avizor contra el phishing. / See the phish before it bites.**

Anti-phishing **educativo, bajo demanda y bilingüe ES/EN** que demuestra cómo
diseñar un producto sobre LLMs sin atarse a un proveedor y sin convertir el
endpoint en una vía de prompt injection.

Dos módulos sobre un mismo motor de IA:

- **Analizador** — pegas un correo, URL o SMS sospechoso y la IA devuelve un
  *score* de riesgo, veredicto e indicadores explicados en lenguaje llano.
- **Entrenador** — la IA genera ejemplos con dificultad adaptativa para que
  practiques detección; te dice qué acertaste, qué se te escapó y qué marcaste
  de más.

> Por qué un proyecto más sobre phishing: la mayoría de plataformas son suites
> de compliance corporativo (Vigil, KnowBe4...). AIvizor es lo contrario:
> herramienta educativa de uso puntual. La demo pública funciona **sin login**;
> la Fase 7 añadió, de forma opcional, cuentas multi-usuario, **BYOK** (tu propia
> clave de IA) y un panel admin. Pieza de portfolio con vocación de producto.

---

## Demo

![Demo de AIvizor — analizador y entrenador](./docs/demo.gif)

> Salida real de IA (Gemini). Cómo se grabó / cómo regenerarla: [docs/DEMO.md](./docs/DEMO.md).

---

## En 30 segundos

```
analyze:                              train:
┌────────────────────────────┐        ┌────────────────────────────┐
│ Pega un email sospechoso   │        │ Nivel 3 · Correo           │
│ [textarea]                 │        │ "Tu paquete está pendiente │
│                            │        │  de entrega. Abone 1,99€   │
│ ▶ Analizar                 │        │  en correos-postal.com..." │
└──────────┬─────────────────┘        │                            │
           ▼                          │ ¿Veredicto?                │
   ┌─────────────────────┐            │  [Legítimo] [Sospechoso]   │
   │ ▓▓▓▓▓▓▓▓▓░ 78/100   │            │  [Phishing]                │
   │ phishing            │            │                            │
   │                     │            │ ¿Indicadores? (marca)      │
   │ ⚠️ Dominio look-    │            │  ☐ Dominio look-alike      │
   │ alike: bbva.ru      │            │  ☐ Petición de pago        │
   │ ⏰ Urgencia: "ya"   │            │  ▶ Comprobar               │
   │ 🔑 Pide credenc...  │            └────────┬───────────────────┘
   └─────────────────────┘                     ▼
                                       ✓ Correcto · 100/100
                                       ✓ Domain look-alike
                                       ⚠ Te escapó: payment_request
                                       ▶ Siguiente (nivel 4)
```

Bilingüe ES/EN, modo oscuro, accesibilidad básica.

---

## Decisiones arquitectónicas (lo que vende esto)

### 1. Capa de abstracción LLM — el motor es detalle de infraestructura

Los servicios (`analyzer`, `trainer`) **nunca** importan SDKs de un proveedor.
Hablan con una interfaz `LLMProvider`:

```python
class LLMProvider(Protocol):
    async def complete_structured(
        self, *, system: str, user: str,
        response_model: type[T], language: Language,
    ) -> T: ...
```

Cambiar de Gemini a Claude — o al mock determinista para CI — es cambiar una
variable de entorno. Cero acoplamiento, cero refactor.

Implementaciones:
- **`MockProvider`** — sin red, determinista, **30 plantillas** del Trainer
  cubriendo email/URL/SMS × 5 dificultades. Doble función como contrato vivo:
  si añades un campo y olvidas el mock, los tests rompen.
- **`GeminiProvider`** — `google-genai` con `response_schema` (acepta clases
  Pydantic 2 directamente).
- **`ClaudeProvider`** — `anthropic` con **tool use forzado** (`return_result`)
  para garantizar JSON estructurado.

Toda salida se valida contra Pydantic antes de tocar BD o cliente. Si el LLM
se desvía, el provider lanza `LLMError` → 502 honesto al cliente, **nunca**
datos corruptos. Ver [docs/architecture/llm-layer.md](./docs/architecture/llm-layer.md).

### 2. Defensa por capas anti prompt-injection

El analyzer mete **contenido del atacante** dentro de un LLM. Es el caso de
uso de manual para inyección. La estrategia no es "una bala de plata" sino
**5 capas independientes** — cada una puede fallar; combinarlas las hace muy
costosas de evadir todas a la vez:

| # | Capa | Mecanismo |
|---|------|-----------|
| **L1** | Wrapper | Contenido envuelto en delimitadores `<<<USER_CONTENT_START/END>>>` que se neutralizan si aparecen en el input (no se puede cerrar el bloque a mitad). |
| **L2** | Detector | `security/injection_signals.py` etiqueta 7 familias de payloads (instruction override, role spoofing, prompt disclosure, encoding smuggling, invisible chars, system tags…) para observabilidad. No bloquea, registra. |
| **L3** | System prompt endurecido | 6 reglas críticas: la manipulación es indicador (no instrucción), no salir del JSON, no revelar el prompt, no acceder a recursos externos, no confiar en cabeceras del propio contenido. |
| **L4** | Schema validado | `response_schema` (Gemini) / `tool_use` forzado (Claude) + validación Pydantic. Si el LLM capitula y devuelve texto libre, falla la validación. |
| **L5** | Coerción servidor | Campos sensibles (idioma) los reescribe el servidor, no el LLM. |

**45 tests parametrizados** con payloads reales contra cada capa.
Ver [docs/architecture/security.md](./docs/architecture/security.md).

### 3. La "verdad" del Trainer nunca sale del servidor

Trampa fácil de meter en un entrenador: enviar la respuesta correcta al
cliente para que pueda evaluarla. Si lo haces, queda como deuda imposible
de quitar. Diseño correcto desde el día 1:

- `TrainingSample` (interno) tiene `true_verdict` y `true_indicators` →
  persiste en BD, vive server-side.
- `TrainingSamplePublic` (lo que devuelve `/api/train/next`) es solo
  `{id, content, input_type, language, difficulty}` — sin la verdad.
- El cliente solo envía `sample_id + su respuesta`; el servidor compara
  internamente y devuelve feedback con score, indicadores fallados y
  falsos positivos.

Ver [docs/architecture/trainer.md](./docs/architecture/trainer.md).

### 4. Repository pattern para tests sin contenedores

Cada servicio depende de un `Protocol` (`AnalysisRepository`,
`TrainingAttemptRepository`, `UserRepository`, `ApiKeyRepository`), no de
SQLAlchemy. En producción FastAPI inyecta la implementación SQL; en tests, una
`InMemory*` captura llamadas. Resultado: **136 tests sin Postgres, sin Docker,
sin red** — registro, login y BYOK se prueban contra repos en memoria.

### 5. Multi-usuario opcional con BYOK — sin romper la demo anónima (Fase 7)

La demo pública es anónima. Sobre ella, la Fase 7 añadió cuentas como **capa
opt-in**, no como requisito:

- **Sesión por JWT en cookie httpOnly** (`SameSite=lax`, `Secure` configurable):
  el frontend nunca toca el token, solo manda `credentials:'include'`. bcrypt para
  el hash; tres representaciones separadas del usuario para que el hash jamás cruce
  la frontera HTTP. → [auth.md](./docs/architecture/auth.md)
- **BYOK (Bring Your Own Key).** Cada usuario aporta su propia clave de Gemini o
  Claude y consume *su* cuota. Se cifra en reposo con **Fernet**; la clave en claro
  solo entra, las lecturas devuelven una máscara (`••••wxyz`). Analyzer/Trainer
  resuelven el provider por petición: usuario con clave → la suya; si no → el
  provider del servidor. La demo no se rompe. → [byok.md](./docs/architecture/byok.md)
- **Panel admin** con auto-protección (un admin no puede desactivarse/borrarse a sí
  mismo). → [admin.md](./docs/architecture/admin.md)

---

## Stack

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI 0.115 · Pydantic 2 · SQLAlchemy 2.0 async · psycopg 3 · Alembic |
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind · next-intl |
| Persistencia | PostgreSQL 16 |
| Motor IA | Gemini · Claude · MockProvider (configurable por env) |
| Auth / BYOK | JWT en cookie httpOnly · bcrypt · Fernet (cifrado de claves en reposo) |
| Orquestación | Docker Compose |

---

## Quick start

```bash
git clone https://github.com/f3l0X/AIvizor.git
cd AIvizor
cp .env.example .env
# Por defecto LLM_PROVIDER=mock — arranca sin API keys ni coste.

docker compose up --build
docker compose exec backend alembic upgrade head
```

- Frontend → http://localhost:3000/es (o /en)
- Backend  → http://localhost:8000/health
- OpenAPI  → http://localhost:8000/docs

> ¿Cómo se usa? Guía paso a paso de los dos módulos, cuentas, BYOK y panel admin
> en el **[Manual de uso](./docs/MANUAL.md)**.

Prueba directamente la API:

```bash
curl -sX POST http://localhost:8000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"content":"Verifique su cuenta YA o se bloqueará","input_type":"email","language":"es"}'
```

### Cambiar a Gemini o Claude

```bash
# .env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
# o:
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=...
```

Reinicia el backend (`docker compose restart backend`). Ni una línea del
código de negocio cambia.

### Activar cuentas + BYOK (opcional)

La demo funciona anónima. Para habilitar la capa multi-usuario (Fase 7), define
en `.env`:

```bash
JWT_SECRET=...                 # mín. 32 bytes; cámbialo en producción
BYOK_ENCRYPTION_KEY=...        # Fernet (urlsafe base64, 32 bytes)
#  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ADMIN_EMAIL=admin@example.com  # opcional: siembra un admin al arrancar
ADMIN_PASSWORD=...
```

El registro público crea cuentas con rol `user`; un admin promueve a otros desde
`/[locale]/admin`. Ver [auth.md](./docs/architecture/auth.md) y
[byok.md](./docs/architecture/byok.md).

---

## Estructura

```
backend/
  app/
    api/           # endpoints FastAPI (analyze, train, auth, keys, admin)
    services/      # lógica de dominio (analyzer, trainer, auth, byok, admin)
    llm/           # LLMProvider Protocol + mock/gemini/claude/factory
    prompts/       # system prompts ES/EN con anti-injection
    schemas/       # contrato Pydantic (catálogo cerrado de IndicatorType)
    db/            # SQLAlchemy + repositories (Protocol + SQL + InMemory)
    security/      # injection signals + passwords (bcrypt) + tokens (JWT) + crypto (Fernet)
  alembic/         # migraciones 0001–0004 (users, user_api_keys)
  tests/           # 136 tests, sin BD

frontend/
  app/[locale]/    # rutas por idioma (es, en): analyze, train, login, register, settings, admin
  components/      # RiskMeter, IndicatorCard, AnalyzeForm, TrainerCard, AuthProvider, AdminUserTable...
  messages/        # i18n (ES, EN) con plurales ICU
  lib/             # cliente HTTP + tipos espejo del backend

docs/architecture/ # documentos de diseño: llm-layer, analyzer, security, trainer,
                   # frontend-analyzer, auth, byok, frontend-auth, admin
```

---

## Tests

```bash
cd backend
python -m venv .venv && ./.venv/Scripts/python.exe -m pip install -e ".[dev]"
./.venv/Scripts/python.exe -m pytest
```

Cobertura por área:

| Módulo | Tests |
|--------|-------|
| Schemas (catálogo cerrado, rangos) | 4 |
| LLM mock + factory | 9 |
| Analyzer (service + endpoint) | 10 |
| Prompts del analyzer | 3 |
| **Injection (5 capas + 7 familias de payloads)** | **45** |
| Trainer (service + endpoint) | 16 |
| Auth (registro, login, sesión, roles) | 18 |
| BYOK (CRUD, cifrado, resolución de provider) | 18 |
| Admin (CRUD usuarios, auto-protección) | 12 |
| Health | 1 |
| **Total** | **136** |

---

## Estado actual

- [x] **Fase 0 — Scaffold.** Monorepo, docker-compose, FastAPI `/health`, Next.js base con i18n ES/EN.
- [x] **Fase 1 — Capa LLM.** Interfaz `LLMProvider`, MockProvider, GeminiProvider, ClaudeProvider, factory. → [doc](./docs/architecture/llm-layer.md)
- [x] **Fase 2 — Analyzer backend.** `POST /api/analyze`, repository pattern, persistencia + Alembic. → [doc](./docs/architecture/analyzer.md)
- [x] **Fase 3 — Seguridad anti prompt-injection.** 5 capas + 45 tests con payloads. → [doc](./docs/architecture/security.md)
- [x] **Fase 4 — Analyzer frontend.** `/analyze` con RiskMeter, IndicatorCard, dark mode. → [doc](./docs/architecture/frontend-analyzer.md)
- [x] **Fase 5 — Trainer end-to-end.** Backend + frontend con la "verdad" siempre server-side, scoring + dificultad adaptativa, 30 plantillas mock por (nivel × idioma × tipo). → [doc](./docs/architecture/trainer.md)
- [x] **Fase 6 — Pulido + demo.** README narrativo, CI, GIF de demo.
- [x] **Fase 7 — Multi-usuario + BYOK + admin** *(giro consciente respecto al anti-scope original).*
  - [x] **7.2 — Auth.** Registro, login y sesión por JWT en cookie httpOnly; roles. → [doc](./docs/architecture/auth.md)
  - [x] **7.3 — BYOK.** Clave de LLM por usuario, cifrada en reposo (Fernet); resolución de provider por petición. → [doc](./docs/architecture/byok.md)
  - [x] **7.4 — Frontend de auth.** Login, registro y ajustes BYOK; estado de sesión en la cabecera. → [doc](./docs/architecture/frontend-auth.md)
  - [x] **7.5 — Panel admin.** Gestión de usuarios (activar/desactivar, rol, borrar) con auto-protección. → [doc](./docs/architecture/admin.md)

---

## Decisiones que NO entran en v1 (por qué)

- **Sin entrenamiento de modelos propios.** No es lo que vende un junior con un
  portfolio: prefiero demostrar criterio de arquitectura sobre LLMs ajenos que
  un Random Forest sobre PhishTank que no aporta nada nuevo.
- **Sin extensión de navegador.** Terreno saturado y mala demo en GIF.
- **Sin compliance / panel de campañas.** No competimos con Vigil/KnowBe4;
  ocupamos el hueco "herramienta puntual y didáctica" que ellos no cubren.

> **Nota:** el anti-scope original incluía *"sin login ni multi-tenant"*. La
> Fase 7 lo revirtió de forma **consciente**: cuentas + BYOK + admin como capa
> **opt-in** sobre la demo anónima (que sigue funcionando sin login). El motivo
> es de portfolio — demuestra auth con JWT, cifrado de secretos en reposo y un
> modelo multi-tenant a nivel de coste de IA, sin convertir el proyecto en una
> suite de compliance.

---

## Licencia

[MIT](./LICENSE).
