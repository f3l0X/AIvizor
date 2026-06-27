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

## Estructura

```
backend/   FastAPI + capa LLM + servicios analyzer/trainer
frontend/  Next.js 14 con [locale]/ (es, en)
docker-compose.yml
PLANNING.md
```

## Estado actual

- [x] **Fase 0 — Scaffold.** Monorepo, docker-compose, FastAPI `/health`, Next.js base con i18n ES/EN, `.env.example`.
- [ ] Fase 1 — Capa LLM (interfaz + provider mock).
- [ ] Fase 2 — Analizador (backend).
- [ ] Fase 3 — Seguridad: anti prompt-injection.
- [ ] Fase 4 — Analizador (frontend).
- [ ] Fase 5 — Entrenador (backend + frontend).
- [ ] Fase 6 — Pulido + demo + deploy.

## Seguridad

El analizador ingiere contenido no confiable: la resistencia a *prompt injection* es un
requisito de primera clase (delimitadores, salidas estructuradas validadas, tests
dedicados). Detalle en §4 de [PLANNING.md](./PLANNING.md).
