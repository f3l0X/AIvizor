# AIvizor

> **Tu ojo avizor contra el phishing. / See the phish before it bites.**

Anti-phishing **educativo, bajo demanda y bilingüe ES/EN**, con dos módulos sobre un mismo
motor de IA:

- **Analizador** — pegas un correo, URL o SMS sospechoso y la IA devuelve un *score* de
  riesgo, veredicto e indicadores explicados.
- **Entrenador** — la IA genera ejemplos con dificultad adaptativa para que practiques
  detección.

Pieza de portfolio con vocación de producto. Decisiones arquitectónicas y alcance en
[PLANNING.md](./PLANNING.md).

---

## Stack

FastAPI · Next.js 14 (App Router) · Tailwind · next-intl · PostgreSQL 16 · Docker Compose
· capa de abstracción LLM (Gemini / Claude / mock).

## Quick start

```bash
cp .env.example .env
# Edita .env para poner tus claves si quieres usar Gemini o Claude.
# Por defecto LLM_PROVIDER=mock para arrancar sin coste.

docker compose up --build
```

- Frontend → http://localhost:3000
- Backend  → http://localhost:8000/health
- Postgres → localhost:5432

Aplica la migración de la base de datos la primera vez:

```bash
docker compose exec backend alembic upgrade head
```

Prueba el Analyzer (Fase 2):

```bash
curl -sX POST http://localhost:8000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"content":"Verifique su cuenta ya","input_type":"email","language":"es"}'
```

## Estructura

```
backend/   FastAPI + capa LLM + servicios analyzer/trainer
frontend/  Next.js 14 con [locale]/ (es, en)
docker-compose.yml
PLANNING.md
```

## Estado actual

- [x] **Fase 0 — Scaffold.** Monorepo, docker-compose, FastAPI `/health`, Next.js base con i18n ES/EN, `.env.example`.
- [x] **Fase 1 — Capa LLM.** Interfaz `LLMProvider`, esquemas Pydantic, `MockProvider` (sin coste), `GeminiProvider`, `ClaudeProvider`, factory por env, tests. Documento de diseño en [docs/architecture/llm-layer.md](./docs/architecture/llm-layer.md).
- [x] **Fase 2 — Analizador (backend).** `POST /api/analyze` con prompts ES/EN delimitados, repositorio inyectable (SQL + InMemory), persistencia en `analyses`, migración Alembic. Documento en [docs/architecture/analyzer.md](./docs/architecture/analyzer.md).
- [x] **Fase 3 — Seguridad: anti prompt-injection.** Defensa por capas (wrapper + detector + prompt endurecido + schema validado + coerción servidor) + suite de payloads. Documento en [docs/architecture/security.md](./docs/architecture/security.md).
- [x] **Fase 4 — Analizador (frontend).** Pantalla `/analyze` con formulario, RiskMeter, IndicatorCard y resultado completo. Bilingüe ES/EN, modo oscuro, accesibilidad básica. Documento en [docs/architecture/frontend-analyzer.md](./docs/architecture/frontend-analyzer.md).
- [ ] Fase 5 — Entrenador (backend + frontend).
- [ ] Fase 6 — Pulido + demo + deploy.

## Seguridad

El analizador ingiere contenido no confiable. La resistencia a *prompt injection* es
un requisito de primera clase, no un parche: ver [docs/architecture/security.md](./docs/architecture/security.md)
para la **defensa por capas** (wrapper que neutraliza delimitadores, detector
de patrones conocidos para observabilidad, system prompt endurecido, validación
estricta de salida vía esquema Pydantic, coerción de campos sensibles en servidor)
y el catálogo de payloads cubiertos por la suite de tests.
